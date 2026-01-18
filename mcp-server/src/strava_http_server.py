#!/usr/bin/env python3
"""
HTTP server for Strava API integration.
This server exposes HTTP endpoints to query the Strava API for activities, athletes, and other data.
"""

import os
import sys
import time
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

# In-memory cache for activities
# Cache structure: {athlete_id: {"activities": [...], "fetched_at": timestamp}}
ACTIVITY_CACHE: Dict[str, Dict[str, Any]] = {}

# Cache structure: {token: athlete_id}
TOKEN_TO_ID_CACHE: Dict[str, str] = {}

CACHE_TTL_SECONDS = 300  # 5 minutes

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
        
        # Retry logic for 429s (Rate Limit Exceeded)
        max_retries = 3
        retry_count = 0
        
        while True:
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params
                )
                
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.HTTPError as e:
                # Handle Rate Limits (429)
                if e.response.status_code == 429 and retry_count < max_retries:
                    retry_count += 1
                    # Get wait time from header or default to exponential backoff
                    retry_after = int(e.response.headers.get("Retry-After", 15))
                    # Cap potential wait time (don't wait too long)
                    wait_time = min(retry_after, 60)
                    
                    logger.warning(f"Rate limited (429). Waiting {wait_time}s then retrying ({retry_count}/{max_retries})...")
                    time.sleep(wait_time)
                    continue
                
                # Propagate 401s directly
                if e.response.status_code == 401:
                     raise HTTPException(status_code=401, detail="Invalid or expired Strava token")
                
                # Propagate other errors
                logger.error(f"Strava API request failed: {str(e)}")
                raise HTTPException(status_code=e.response.status_code, detail=str(e))
                
    except HTTPException:
        raise
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
def get_recent_activities(limit: int = 200, page: int = 1, x_strava_token: str = Header(..., alias="X-Strava-Token")) -> List[Dict[str, Any]]:
    """Get recent activities from Strava. Max 200 per page."""
    # Strava API max is 200 per page
    per_page = min(limit, 200)
    return make_strava_request(
        f"{STRAVA_API_BASE_URL}/athlete/activities",
        params={"per_page": per_page, "page": page},
        access_token=x_strava_token
    )

@app.get("/activities/all")
def get_all_activities(x_strava_token: str = Header(..., alias="X-Strava-Token"), refresh: bool = False) -> List[Dict[str, Any]]:
    """Get ALL activities from Strava by paginating through all pages. Results are cached for 5 minutes."""
    global ACTIVITY_CACHE, TOKEN_TO_ID_CACHE
    
    # Get athlete ID (check token cache first)
    athlete_id = TOKEN_TO_ID_CACHE.get(x_strava_token)
    
    if not athlete_id:
        try:
            athlete = make_strava_request(f"{STRAVA_API_BASE_URL}/athlete", access_token=x_strava_token)
            athlete_id = str(athlete["id"])
            TOKEN_TO_ID_CACHE[x_strava_token] = athlete_id
        except HTTPException as e:
            if e.status_code == 429:
                # If we're 429'd on the athlete lookup, we can't get the ID.
                # If we had it cached we could have returned data.
                logger.error("Rate limited getting athlete ID. Cannot check cache.")
                raise e
            raise
    
    # Check cache (unless refresh is requested)
    if not refresh and athlete_id in ACTIVITY_CACHE:
        cache_entry = ACTIVITY_CACHE[athlete_id]
        if time.time() - cache_entry["fetched_at"] < CACHE_TTL_SECONDS:
            logger.info(f"Returning {len(cache_entry['activities'])} cached activities for athlete {athlete_id}")
            return cache_entry["activities"]
    
    # Fetch all activities with pagination
    all_activities = []
    page = 1
    per_page = 200  # Max allowed by Strava
    
    try:
        while True:
            activities = make_strava_request(
            f"{STRAVA_API_BASE_URL}/athlete/activities",
            params={"per_page": per_page, "page": page},
            access_token=x_strava_token
        )
        
            if not activities:
                break
                
            all_activities.extend(activities)
            
            # If we got fewer than per_page, we've reached the end
            if len(activities) < per_page:
                break
                
            page += 1
            
            # Safety limit to prevent infinite loops (max 50 pages = 10,000 activities)
            if page > 50:
                logger.warning("Reached max page limit (50) while fetching activities")
                break

    except HTTPException as e:
        if e.status_code == 429:
            logger.warning("Rate limit hit during pagination. Returning partial results.")
            pass
        else:
            raise
    
    # Save to cache if we got results (or if we got a lot before error)
    if all_activities:
        ACTIVITY_CACHE[athlete_id] = {
            "activities": all_activities,
            "fetched_at": time.time()
        }
        logger.info(f"Fetched and cached {len(all_activities)} total activities for athlete {athlete_id}")
    
    return all_activities

@app.get("/activities/summary")
def get_activities_summary(x_strava_token: str = Header(..., alias="X-Strava-Token")) -> Dict[str, Any]:
    """Get a summarized view of all activities for efficient AI queries. Returns aggregated data by year/month."""
    # Get all activities (will use cache if available)
    all_activities = get_all_activities(x_strava_token)
    
    # Group activities by year and month
    by_year: Dict[str, Dict[str, Any]] = {}
    activities_by_date: Dict[str, List[Dict[str, Any]]] = {}
    
    for activity in all_activities:
        # Parse date
        start_date = activity.get("start_date_local", activity.get("start_date", ""))
        if not start_date:
            continue
            
        date_obj = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        year = str(date_obj.year)
        month = f"{year}-{date_obj.month:02d}"
        date_key = date_obj.strftime("%Y-%m-%d")
        
        # Initialize year if needed
        if year not in by_year:
            by_year[year] = {
                "total_activities": 0,
                "total_distance_miles": 0,
                "total_elevation_feet": 0,
                "total_moving_time_seconds": 0,
                "by_type": {},
                "by_month": {}
            }
        
        # Initialize month if needed
        if month not in by_year[year]["by_month"]:
            by_year[year]["by_month"][month] = {
                "activities": 0,
                "distance_miles": 0,
                "elevation_feet": 0,
                "moving_time_seconds": 0
            }
        
        # Track activities by date (condensed format)
        if date_key not in activities_by_date:
            activities_by_date[date_key] = []
        
        activity_type = activity.get("sport_type", activity.get("type", "Unknown"))
        distance_miles = activity.get("distance", 0) * 0.000621371
        elevation_feet = activity.get("total_elevation_gain", 0) * 3.28084
        moving_time = activity.get("moving_time", 0)
        
        activities_by_date[date_key].append({
            "name": activity.get("name", ""),
            "type": activity_type,
            "distance_miles": round(distance_miles, 2),
            "elevation_feet": round(elevation_feet, 0),
            "moving_time_seconds": moving_time,
            "start_time": start_date
        })
        
        # Update year totals
        by_year[year]["total_activities"] += 1
        by_year[year]["total_distance_miles"] += distance_miles
        by_year[year]["total_elevation_feet"] += elevation_feet
        by_year[year]["total_moving_time_seconds"] += moving_time
        
        # Update type counts
        if activity_type not in by_year[year]["by_type"]:
            by_year[year]["by_type"][activity_type] = {"count": 0, "distance_miles": 0}
        by_year[year]["by_type"][activity_type]["count"] += 1
        by_year[year]["by_type"][activity_type]["distance_miles"] += distance_miles
        
        # Update month totals
        by_year[year]["by_month"][month]["activities"] += 1
        by_year[year]["by_month"][month]["distance_miles"] += distance_miles
        by_year[year]["by_month"][month]["elevation_feet"] += elevation_feet
        by_year[year]["by_month"][month]["moving_time_seconds"] += moving_time
    
    # Round the totals
    for year_data in by_year.values():
        year_data["total_distance_miles"] = round(year_data["total_distance_miles"], 2)
        year_data["total_elevation_feet"] = round(year_data["total_elevation_feet"], 0)
        for type_data in year_data["by_type"].values():
            type_data["distance_miles"] = round(type_data["distance_miles"], 2)
        for month_data in year_data["by_month"].values():
            month_data["distance_miles"] = round(month_data["distance_miles"], 2)
            month_data["elevation_feet"] = round(month_data["elevation_feet"], 0)
    
    return {
        "total_activities": len(all_activities),
        "by_year": by_year,
        "activities_by_date": activities_by_date,  # Full list for date queries
        "cache_info": f"Data cached at {datetime.now().isoformat()}"
    }

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
        uvicorn.run(app, host="0.0.0.0", port=8001)
    except Exception as e:
        logger.error(f"Server error: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    main() 