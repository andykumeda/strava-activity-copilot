import os
import re
import httpx
from google import genai
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
if not GENAI_API_KEY:
    print("WARNING: GEMINI_API_KEY not set")

MCP_SERVER_URL = "http://localhost:8001"

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
            activities_resp = await client.get(f"{MCP_SERVER_URL}/activities/summary", headers=headers, timeout=180.0)  # Summarized data for efficient queries
        except httpx.RequestError as e:
             raise HTTPException(status_code=500, detail=f"Failed to connect to MCP server: {str(e)}")

    context_data = {
        "stats": stats_resp.json() if stats_resp.status_code == 200 else {"error": "Failed to fetch stats"},
        "activity_summary": activities_resp.json() if activities_resp.status_code == 200 else {"error": "Failed to fetch activities"}
    }
    
    # 3. Construct Prompt
    # We provide the JSON data and the user question.
    if not client:
        return QueryResponse(answer="Gemini API not configured", data_used=context_data)
        
    # --- Context Optimization ---
    # Filter specific activities based on the question to avoid hitting token limits
    # 1. Always include the high-level summary (by_year)
    # 2. Extract years from the question
    # 3. If years found, include activities from those years. Else, include recent (last 90 days).
    
    full_summary = context_data.get("activity_summary", {})
    activities_by_date = full_summary.get("activities_by_date", {})
    
    years_found = re.findall(r'\b(20\d{2})\b', request.question)
    relevant_activities = []
    filter_reason = "Default: Recent activities (last 90 active days)"
    
    if years_found:
        selected_years = set(years_found)
        filter_reason = f"Filtered by years found in question: {', '.join(selected_years)}"
        for date_str, activities in activities_by_date.items():
            year = date_str.split('-')[0]
            if year in selected_years:
                for activity in activities:
                    activity['date'] = date_str
                    relevant_activities.append(activity)
    else:
        # Default: Last 90 days of recorded activities
        sorted_dates = sorted(activities_by_date.keys(), reverse=True)
        recent_dates = sorted_dates[:90]
        for date_str in recent_dates:
            activities = activities_by_date[date_str]
            for activity in activities:
                activity['date'] = date_str
                relevant_activities.append(activity)
                
    optimized_context = {
        "stats": context_data.get("stats"),
        "summary_by_year": full_summary.get("by_year"),
        "relevant_activities": relevant_activities,
        "filter_note": filter_reason
    }

    prompt = f"""
    You are a helpful assistant analyzing Strava fitness data.
    
    IMPORTANT INSTRUCTIONS:
    - The raw data uses meters - you MUST convert to imperial units before responding
    - Always show distances in MILES only (1 meter = 0.000621371 miles)
    - Always show elevation in FEET only (1 meter = 3.28084 feet)
    - Do NOT show metric values or conversion math - just give the final imperial values
    - For pace, show as minutes per mile (e.g., "8:30/mile")
    - When asked about a specific date, show ALL activities from that date, not just one
    - Format output using Markdown:
      * Use bullet points (-) for lists of activities
      * Use **bold** for activity names or key stats
      * Place each activity on a new line
    - When comparing years, only compare data from matching time periods
    - Be precise with calculations
    - If data is incomplete, acknowledge this
    
    User Question: {request.question}
    
    Here is the RELEVANT Strava data (filtered to fit context limits):
    {optimized_context}
    
    Please answer the user's question based on this data.
    Use miles for distance and feet for elevation - do not show meters.
    When asked about a date, list ALL activities from that date.
    If the answer cannot be determined from the data, say so.
    Provide a concise and encouraging response.
    """
    
    # 4. Generate Answer
    try:
        # Create client inside function to ensure correct context
        gemini_client = genai.Client(api_key=GENAI_API_KEY)
        response = await gemini_client.aio.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=prompt
        )
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
