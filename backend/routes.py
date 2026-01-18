import os
import httpx
import google.generativeai as genai
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from .database import get_db
from .models import User, Token
from .deps import get_current_user

router = APIRouter()

# Configure Gemini
GENAI_API_KEY = os.getenv("GEMINI_API_KEY")
if GENAI_API_KEY:
    genai.configure(api_key=GENAI_API_KEY)
else:
    print("WARNING: GEMINI_API_KEY not set")

MCP_SERVER_URL = "http://localhost:8000"

class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    answer: str
    data_used: dict

async def get_valid_token(user: User, db: Session) -> str:
    """Get a valid access token, refreshing if necessary."""
    token_entry = db.query(Token).filter(Token.user_id == user.id).first()
    if not token_entry:
        raise HTTPException(status_code=401, detail="No Strava tokens found for user")

    # Check expiration (simple timestamp check, add buffer)
    # expires_at is unix timestamp
    if datetime.utcnow().timestamp() > (token_entry.expires_at - 300):
        # Refresh token
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://www.strava.com/oauth/token",
                data={
                    "client_id": os.getenv("STRAVA_CLIENT_ID"),
                    "client_secret": os.getenv("STRAVA_CLIENT_SECRET"),
                    "refresh_token": token_entry.refresh_token,
                    "grant_type": "refresh_token",
                },
            )
        
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Failed to refresh Strava token")

        data = response.json()
        token_entry.access_token = data["access_token"]
        token_entry.refresh_token = data["refresh_token"]
        token_entry.expires_at = data["expires_at"]
        db.commit()
    
    return token_entry.access_token

@router.post("/query", response_model=QueryResponse)
async def query_strava_data(
    request: QueryRequest, 
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not GENAI_API_KEY:
        raise HTTPException(status_code=500, detail="Gemini API not configured")

    # 1. Get Valid Token
    access_token = await get_valid_token(user, db)

    # 2. Fetch Context Data from MCP Server
    # For a generic query, we might fetch "recent activities" and "stats".
    # A more advanced implementation would let Gemini decide what to fetch via tool calls,
    # but per requirements, we'll fetch structured data and pass to Gemini.
    
    async with httpx.AsyncClient() as client:
        headers = {"X-Strava-Token": access_token}
        
        # Parallel fetch could be better, but sequential for simplicity
        try:
            stats_resp = await client.get(f"{MCP_SERVER_URL}/athlete/stats", headers=headers)
            activities_resp = await client.get(f"{MCP_SERVER_URL}/activities/recent?limit=30", headers=headers) # Get last 30
        except httpx.RequestError as e:
             raise HTTPException(status_code=500, detail=f"Failed to connect to MCP server: {str(e)}")

    context_data = {
        "stats": stats_resp.json() if stats_resp.status_code == 200 else {"error": "Failed to fetch stats"},
        "recent_activities": activities_resp.json() if activities_resp.status_code == 200 else {"error": "Failed to fetch activities"}
    }
    
    # 3. Construct Prompt
    # We provide the JSON data and the user question.
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    You are a helpful assistant analyzing Strava fitness data.
    
    User Question: {request.question}
    
    Here is the user's data (stats and recent activities):
    {context_data}
    
    Please answer the user's question based on this data. 
    If the answer cannot be determined from the data, say so.
    Provide a concise and encouraging response.
    """
    
    # 4. Generate Answer
    try:
        response = model.generate_content(prompt)
        answer_text = response.text
    except Exception as e:
        answer_text = f"Error generating answer: {str(e)}"
    
    return QueryResponse(answer=answer_text, data_used=context_data)

@router.get("/test-data")
async def get_test_data(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Utility to see what data the backend fetches for debugging."""
    access_token = await get_valid_token(user, db)
    async with httpx.AsyncClient() as client:
        headers = {"X-Strava-Token": access_token}
        stats_resp = await client.get(f"{MCP_SERVER_URL}/athlete/stats", headers=headers)
        activities_resp = await client.get(f"{MCP_SERVER_URL}/activities/recent?limit=10", headers=headers)
        
    return {
        "stats": stats_resp.json(),
        "recent_activities": activities_resp.json()
    }
