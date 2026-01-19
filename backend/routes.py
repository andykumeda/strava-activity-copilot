import os
import re
import asyncio
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from .database import get_db
from .models import User, Token
from .deps import get_current_user
from .context_optimizer import ContextOptimizer
from .llm_provider import get_llm_provider

router = APIRouter()

# LLM Configuration - defaults to OpenRouter
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openrouter")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek/deepseek-chat")  # Try "deepseek/deepseek-chat" or "deepseek/deepseek-reasoner"

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8001")

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    
    @validator('question')
    def validate_question(cls, v):
        if not v.strip():
            raise ValueError('Question cannot be empty')
        return v.strip()

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

def determine_query_type(question: str, optimized_context: dict) -> str:
    """Determine query type for smart model selection."""
    question_lower = question.lower()
    
    if any(word in question_lower for word in ['total', 'sum', 'average', 'how many', 'how much', 'count']):
        return "aggregate"
    elif any(word in question_lower for word in ['compare', 'vs', 'versus', 'difference', 'better', 'worse']):
        return "comparison"
    elif any(word in question_lower for word in ['analyze', 'trend', 'pattern', 'why', 'reason']):
        return "analysis"
    else:
        return "general"

@router.post("/query", response_model=QueryResponse)
async def query_strava_data(
    request: QueryRequest, 
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    # 1. Get Valid Token
    access_token = await get_valid_token(user, db)

    # 2. Fetch Context Data from MCP Server
    # For a generic query, we might fetch "recent activities" and "stats".
    # A more advanced implementation would let Gemini decide what to fetch via tool calls,
    # but per requirements, we'll fetch structured data and pass to Gemini.
    
    async with httpx.AsyncClient() as client:
        headers = {"X-Strava-Token": access_token}
        
        # Parallel fetch for better performance
        try:
            stats_resp, activities_resp = await asyncio.gather(
                client.get(f"{MCP_SERVER_URL}/athlete/stats", headers=headers),
                client.get(f"{MCP_SERVER_URL}/activities/summary", headers=headers, timeout=180.0)
            )
        except httpx.RequestError as e:
             raise HTTPException(status_code=500, detail=f"Failed to connect to MCP server: {str(e)}")

    stats_data = stats_resp.json() if stats_resp.status_code == 200 else {"error": "Failed to fetch stats"}
    activity_summary_data = activities_resp.json() if activities_resp.status_code == 200 else {"error": "Failed to fetch activities"}
    
    context_data = {
        "stats": stats_data,
        "activity_summary": activity_summary_data
    }
    
    # 3. Optimize Context - Smart filtering to prevent context limits and minimize costs
    optimizer = ContextOptimizer(
        question=request.question,
        activity_summary=activity_summary_data,
        stats=stats_data
    )
    optimized_context = optimizer.optimize_context()
    
    # System instructions (reduces token cost, can be cached)
    system_instruction = """You are a helpful assistant analyzing Strava fitness data.

IMPORTANT INSTRUCTIONS:
- Data is already in imperial units (miles and feet)
- Always show distances in MILES only
- Always show elevation in FEET only
- For pace, show as minutes per mile (e.g., "8:30/mile")
- When asked about a specific date, show ALL activities from that date
- Format output using Markdown:
  * Use bullet points (-) for lists
  * Use **bold** for activity names or key stats
- When comparing years, only compare matching time periods
- Be precise with calculations
- If data is incomplete, acknowledge this
- Use summary_by_year for aggregate queries when detailed activities aren't provided
- Provide concise and encouraging responses"""

    # User prompt (minimal, dynamic content)
    user_prompt = f"""=== USER QUESTION ===
{request.question}
=== END USER QUESTION ===

=== DATA ===
{optimized_context}
=== END DATA ===

Answer the user's question based on this data. If the answer cannot be determined from the data, say so."""
    
    # 4. Generate Answer using LLM provider (OpenRouter, DeepSeek, or Gemini)
    try:
        llm = get_llm_provider()
        
        # Determine query type for smart model selection (OpenRouter only)
        query_type = determine_query_type(request.question, optimized_context)
        
        answer_text = await llm.generate(
            prompt=user_prompt,
            system_instruction=system_instruction,
            temperature=0.3,
            max_tokens=2000,
            query_type=query_type  # For smart model selection with OpenRouter
        )
    except ValueError as e:
        # Configuration error
        raise HTTPException(
            status_code=500, 
            detail=f"LLM configuration error: {str(e)}. Please check your API keys in .env"
        )
    except Exception as e:
        # Handle context limit errors gracefully
        error_msg = str(e).lower()
        error_str = str(e)
        
        # Log the full error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"LLM generation error: {error_str}")
        
        if "context" in error_msg or "token" in error_msg or "length" in error_msg:
            answer_text = f"I apologize, but the query requires too much data to process at once. Please try a more specific question or a shorter time range."
        elif "404" in error_str or "not found" in error_msg:
            # Check if it's an OpenRouter model availability issue
            raise HTTPException(
                status_code=500,
                detail=f"Model not available: {error_str}. The model '{LLM_MODEL}' may not be accessible with your API key. Try a different model in .env (e.g., google/gemini-3-flash-preview)."
            )
        elif "api" in error_msg or "key" in error_msg or "auth" in error_msg:
            raise HTTPException(
                status_code=500,
                detail=f"LLM API error: {error_str}. Please check your API key configuration."
            )
        else:
            answer_text = f"Error generating answer: {error_str}"
    
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
