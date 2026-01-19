"""
Smart context optimization for Gemini API.
Handles context limits, token counting, and intelligent data filtering.
"""
import json
import re
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime, timedelta
import dateparser


class ContextOptimizer:
    """
    Optimizes context sent to Gemini to:
    1. Prevent context limit errors
    2. Minimize token usage (cost)
    3. Ensure all historical data is accessible
    """
    
    # Token estimates (rough approximations)
    # Gemini 2.0 Flash has ~1M token context, but we want to stay well under
    MAX_CONTEXT_TOKENS = 500000  # Conservative limit
    TOKEN_OVERHEAD = 500  # Prompt overhead
    
    # Token estimates per item
    TOKENS_PER_ACTIVITY = 50  # Condensed activity format
    TOKENS_PER_SUMMARY_ENTRY = 20
    TOKENS_PER_STATS_ENTRY = 30
    
    def __init__(self, question: str, activity_summary: Dict[str, Any], stats: Dict[str, Any]):
        self.question = question.lower()
        self.activity_summary = activity_summary
        self.stats = stats
        self.by_year = activity_summary.get("by_year", {})
        self.activities_by_date = activity_summary.get("activities_by_date", {})
        
    def estimate_tokens(self, data: Any) -> int:
        """Rough token estimation by JSON string length."""
        json_str = json.dumps(data, separators=(',', ':'))
        # Rough estimate: ~4 characters per token
        return len(json_str) // 4
    
    def parse_date_range(self) -> Optional[Tuple[datetime, datetime]]:
        """
        Parse natural language dates from question.
        Returns (start_date, end_date) or None if can't determine.
        """
        question_lower = self.question.lower()
        
        # Check for explicit years
        years = re.findall(r'\b(20\d{2})\b', self.question)
        if years:
            years_int = [int(y) for y in years]
            start_year = min(years_int)
            end_year = max(years_int)
            return (
                datetime(start_year, 1, 1),
                datetime(end_year, 12, 31, 23, 59, 59)
            )
        
        # Check for "all time", "everything", "all activities"
        if any(phrase in question_lower for phrase in ['all time', 'everything', 'all activities', 'entire', 'complete']):
            # Return None to indicate all data
            return None
        
        # Check for "last year", "this year", etc.
        if 'last year' in question_lower:
            now = datetime.now()
            return (datetime(now.year - 1, 1, 1), datetime(now.year - 1, 12, 31, 23, 59, 59))
        
        if 'this year' in question_lower or 'current year' in question_lower:
            now = datetime.now()
            return (datetime(now.year, 1, 1), datetime(now.year, 12, 31, 23, 59, 59))
        
        # Check for "last N months/weeks/days"
        months_match = re.search(r'last (\d+) months?', question_lower)
        if months_match:
            months = int(months_match.group(1))
            end = datetime.now()
            start = end - timedelta(days=months * 30)
            return (start, end)
        
        weeks_match = re.search(r'last (\d+) weeks?', question_lower)
        if weeks_match:
            weeks = int(weeks_match.group(1))
            end = datetime.now()
            start = end - timedelta(weeks=weeks)
            return (start, end)
        
        days_match = re.search(r'last (\d+) days?', question_lower)
        if days_match:
            days = int(days_match.group(1))
            end = datetime.now()
            start = end - timedelta(days=days)
            return (start, end)
        
        # Try dateparser for specific dates
        try:
            parsed = dateparser.parse(self.question, settings={'PREFER_DATES_FROM': 'past'})
            if parsed:
                # If a single date, return that day
                return (parsed.replace(hour=0, minute=0, second=0), 
                       parsed.replace(hour=23, minute=59, second=59))
        except:
            pass
        
        # Default: return None (will use summary-only approach)
        return None
    
    def filter_activities_by_date_range(self, start_date: Optional[datetime], 
                                       end_date: Optional[datetime]) -> List[Dict[str, Any]]:
        """Filter activities by date range."""
        if start_date is None and end_date is None:
            # All activities requested
            all_activities = []
            for date_str, activities in self.activities_by_date.items():
                for activity in activities:
                    activity['date'] = date_str
                    all_activities.append(activity)
            return all_activities
        
        filtered = []
        for date_str, activities in self.activities_by_date.items():
            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                if start_date and date_obj < start_date:
                    continue
                if end_date and date_obj > end_date:
                    continue
                
                for activity in activities:
                    activity['date'] = date_str
                    filtered.append(activity)
            except ValueError:
                continue
        
        return filtered
    
    def optimize_context(self) -> Dict[str, Any]:
        """
        Main optimization function.
        Returns optimized context that:
        1. Stays within token limits
        2. Includes all necessary data
        3. Uses summaries when appropriate
        """
        # Always include summary data (small, essential)
        optimized = {
            "summary_by_year": self.by_year,
            "stats": self.stats,
        }
        
        # Determine what level of detail is needed
        date_range = self.parse_date_range()
        
        # Check if question needs detailed activities
        needs_details = any(phrase in self.question for phrase in [
            'activity', 'activities', 'run', 'ride', 'workout', 'training',
            'on', 'date', 'day', 'specific', 'list', 'show', 'what did'
        ])
        
        # Check if question is about aggregates (can use summaries)
        is_aggregate = any(phrase in self.question for phrase in [
            'total', 'sum', 'average', 'compare', 'statistics', 'stats',
            'how many', 'how much', 'total distance', 'total time'
        ])
        
        # Strategy: Use summaries for aggregates, details for specific queries
        if is_aggregate and not needs_details:
            # Aggregates can be answered from summaries alone
            optimized["strategy"] = "summary_only"
            optimized["note"] = "Using summary data for aggregate query"
            return optimized
        
        # Get filtered activities
        if date_range:
            start_date, end_date = date_range
            relevant_activities = self.filter_activities_by_date_range(start_date, end_date)
        else:
            # All activities requested
            relevant_activities = self.filter_activities_by_date_range(None, None)
        
        # Estimate token usage
        base_tokens = self.estimate_tokens(optimized)
        activity_tokens = len(relevant_activities) * self.TOKENS_PER_ACTIVITY
        total_estimated = base_tokens + activity_tokens + self.TOKEN_OVERHEAD
        
        # If within limits, include all relevant activities
        if total_estimated < self.MAX_CONTEXT_TOKENS:
            optimized["relevant_activities"] = relevant_activities
            optimized["strategy"] = "full_details"
            optimized["activity_count"] = len(relevant_activities)
            optimized["estimated_tokens"] = total_estimated
            return optimized
        
        # Too large - need to be smarter
        # Strategy 1: If asking about specific date, include that date only
        if 'on' in self.question or 'date' in self.question:
            # Try to extract specific date
            try:
                parsed_date = dateparser.parse(self.question)
                if parsed_date:
                    date_key = parsed_date.strftime("%Y-%m-%d")
                    if date_key in self.activities_by_date:
                        optimized["relevant_activities"] = [
                            {**act, 'date': date_key} 
                            for act in self.activities_by_date[date_key]
                        ]
                        optimized["strategy"] = "specific_date"
                        optimized["note"] = f"Showing activities for {date_key} only"
                        return optimized
            except:
                pass
        
        # Strategy 2: Limit to most recent N activities within date range
        if date_range:
            start_date, end_date = date_range
            filtered = self.filter_activities_by_date_range(start_date, end_date)
            # Sort by date (most recent first) and limit
            filtered.sort(key=lambda x: x.get('start_time', ''), reverse=True)
            max_activities = (self.MAX_CONTEXT_TOKENS - base_tokens - self.TOKEN_OVERHEAD) // self.TOKENS_PER_ACTIVITY
            optimized["relevant_activities"] = filtered[:max_activities]
            optimized["strategy"] = "limited_recent"
            optimized["note"] = f"Showing {len(optimized['relevant_activities'])} most recent activities from date range"
            optimized["total_available"] = len(filtered)
            return optimized
        
        # Strategy 3: Use year summaries + recent activities
        # Include summaries for all years, but only recent detailed activities
        sorted_dates = sorted(self.activities_by_date.keys(), reverse=True)
        max_recent_days = 30  # Last 30 days of details
        recent_activities = []
        for date_str in sorted_dates[:max_recent_days]:
            for activity in self.activities_by_date[date_str]:
                activity['date'] = date_str
                recent_activities.append(activity)
        
        optimized["relevant_activities"] = recent_activities
        optimized["strategy"] = "summary_plus_recent"
        optimized["note"] = "Using year summaries + recent 30 days of activities. For older data, summaries are available."
        optimized["recent_activity_count"] = len(recent_activities)
        
        return optimized

