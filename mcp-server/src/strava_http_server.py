#!/usr/bin/env python3
"""
HTTP server for Strava API integration.
This server exposes HTTP endpoints to query the Strava API for activities, athletes, and other data.
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Response, Request, Header
from fastapi.responses import HTMLResponse
import uvicorn
import requests
from map_utils import format_activity_with_map

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# Strava API configuration
STRAVA_API_BASE_URL = "https://www.strava.com/api/v3"

# Create FastAPI app
app = FastAPI(
    title="Strava API Server",
    description="HTTP server for Strava API integration",
)

def make_strava_request(url: str, method: str = "GET", params: Dict[str, Any] = None, access_token: str = None) -> Dict[str, Any]:
    """Make a request to the Strava API."""
    if not access_token:
        raise HTTPException(status_code=401, detail="Missing X-Strava-Token header")
    
    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            params=params
        )
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
             raise HTTPException(status_code=401, detail="Invalid or expired Strava token")
        logger.error(f"Strava API request failed: {str(e)}")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"Strava API request failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/auth/status")
def check_auth_status(x_strava_token: Optional[str] = Header(None, alias="X-Strava-Token")) -> Dict[str, Any]:
    """Check if we're authenticated with Strava."""
    if not x_strava_token:
        return {
            "authenticated": False,
            "message": "Not authenticated with Strava"
        }
    
    try:
        profile = make_strava_request(f"{STRAVA_API_BASE_URL}/athlete", access_token=x_strava_token)
        return {
            "authenticated": True,
            "message": "Successfully authenticated with Strava",
            "profile": profile
        }
    except Exception as e:
        return {
            "authenticated": False,
            "message": f"Authentication error: {str(e)}"
        }

@app.get("/activities/recent")
def get_recent_activities(limit: int = 10, x_strava_token: str = Header(..., alias="X-Strava-Token")) -> List[Dict[str, Any]]:
    """Get recent activities from Strava."""
    return make_strava_request(
        f"{STRAVA_API_BASE_URL}/athlete/activities",
        params={"per_page": limit},
        access_token=x_strava_token
    )

@app.get("/activities/{activity_id}")
def get_activity(activity_id: int, x_strava_token: str = Header(..., alias="X-Strava-Token")) -> Dict[str, Any]:
    """Get detailed activity data from Strava."""
    return make_strava_request(f"{STRAVA_API_BASE_URL}/activities/{activity_id}", access_token=x_strava_token)

@app.get("/athlete/stats")
def get_athlete_stats(x_strava_token: str = Header(..., alias="X-Strava-Token")) -> Dict[str, Any]:
    """Get athlete statistics from Strava."""
    # First get athlete ID
    athlete = make_strava_request(f"{STRAVA_API_BASE_URL}/athlete", access_token=x_strava_token)
    athlete_id = athlete["id"]
    
    # Then get stats
    return make_strava_request(f"{STRAVA_API_BASE_URL}/athletes/{athlete_id}/stats", access_token=x_strava_token)

@app.get("/activities/{activity_id}/map")
def get_activity_with_map(activity_id: int, format: str = 'html', x_strava_token: str = Header(..., alias="X-Strava-Token")) -> Response:
    """Get detailed activity data from Strava with map visualization."""
    try:
        activity_data = make_strava_request(f"{STRAVA_API_BASE_URL}/activities/{activity_id}", access_token=x_strava_token)
        logger.debug(f"Retrieved activity data for ID {activity_id}")
        
        formatted_activity = format_activity_with_map(activity_data, format)
        logger.debug(f"Formatted activity data with {format} format")
        
        if format == 'html':
            return HTMLResponse(content=formatted_activity, media_type="text/html")
        else:
            return {
                "formatted_activity": formatted_activity,
                "activity": activity_data
            }
    except Exception as e:
        logger.error(f"Error processing activity {activity_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

def main() -> None:
    """Main entry point for the server."""
    try:
        logger.info("Starting Strava HTTP Server...")
        uvicorn.run(app, host="0.0.0.0", port=8000)
    except Exception as e:
        logger.error(f"Server error: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    main() 