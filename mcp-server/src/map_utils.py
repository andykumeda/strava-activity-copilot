import polyline
from typing import List, Tuple, Dict, Any
from math import floor
import json
import logging
from templates import MAP_TEMPLATE

logger = logging.getLogger(__name__)

def decode_polyline(encoded_polyline: str) -> List[Tuple[float, float]]:
    """Decode a polyline string into a list of coordinates."""
    try:
        return polyline.decode(encoded_polyline)
    except Exception as e:
        logger.error(f"Failed to decode polyline: {str(e)}")
        raise ValueError(f"Invalid polyline data: {str(e)}")

def format_duration(seconds: int) -> str:
    """Format duration in seconds to HH:MM:SS format."""
    try:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"
    except Exception as e:
        logger.error(f"Failed to format duration: {str(e)}")
        return "00:00"

def create_html_map(activity: Dict[str, Any]) -> str:
    """
    Create an HTML map visualization of the activity.
    Args:
        activity: Strava activity data
    Returns:
        HTML string with interactive map and activity info
    """
    try:
        if not activity.get('map') or not activity['map'].get('polyline'):
            logger.warning("No map data available in activity")
            return "<p>No map data available</p>"

        # Decode polyline
        coordinates = decode_polyline(activity['map']['polyline'])
        logger.debug(f"Decoded {len(coordinates)} coordinates from polyline")
        
        # Format duration
        duration = format_duration(activity.get('moving_time', 0))
        
        # Prepare data for template
        template_data = {
            'activity_name': activity.get('name', 'Activity'),
            'distance': activity.get('distance', 0) / 1000,  # Convert to km
            'duration': duration,
            'avg_speed': activity.get('average_speed', 0) * 3.6,  # Convert to km/h
            'elevation_gain': activity.get('total_elevation_gain', 0),
            'coordinates': json.dumps(coordinates)  # Convert coordinates to JSON for JavaScript
        }
        
        # Return formatted HTML
        return MAP_TEMPLATE.format(**template_data)
    except Exception as e:
        logger.error(f"Failed to create HTML map: {str(e)}", exc_info=True)
        raise ValueError(f"Failed to create map visualization: {str(e)}")

def format_activity_with_map(activity: Dict[str, Any], format: str = 'html') -> str:
    """
    Format an activity with map visualization.
    Args:
        activity: Strava activity data
        format: Output format ('html' or 'ascii')
    Returns:
        Formatted string with activity info and map
    """
    try:
        if format == 'html':
            return create_html_map(activity)
        else:
            # Keep existing ASCII implementation for backward compatibility
            coordinates = decode_polyline(activity['map']['polyline'])
            ascii_map = create_ascii_map(coordinates)
            
            activity_info = f"""# {activity['name']}

## Route Map
{ascii_map}

## Activity Details
- Type: {activity.get('type', 'N/A')}
- Distance: {activity.get('distance', 0) / 1000:.2f} km
- Duration: {format_duration(activity.get('moving_time', 0))}
- Date: {activity.get('start_date_local', 'N/A')}
- Location: {activity.get('location_city', '')} {activity.get('location_state', '')}

## Performance
- Average Speed: {activity.get('average_speed', 0) * 3.6:.1f} km/h
- Max Speed: {activity.get('max_speed', 0) * 3.6:.1f} km/h
- Elevation Gain: {activity.get('total_elevation_gain', 0):.0f}m
"""
            return activity_info
    except Exception as e:
        logger.error(f"Failed to format activity: {str(e)}", exc_info=True)
        raise ValueError(f"Failed to format activity data: {str(e)}")

# Keep the create_ascii_map function for backward compatibility
def create_ascii_map(coordinates: List[Tuple[float, float]], width: int = 60, height: int = 20) -> str:
    """Create an ASCII map representation of the route."""
    try:
        if not coordinates:
            return "No coordinates available"

        # Find bounds
        lats = [lat for lat, _ in coordinates]
        lngs = [lng for _, lng in coordinates]
        min_lat, max_lat = min(lats), max(lats)
        min_lng, max_lng = min(lngs), max(lngs)

        # Create empty map
        map_array = [[' ' for _ in range(width)] for _ in range(height)]

        # Plot points
        for lat, lng in coordinates:
            # Convert to map coordinates
            x = floor((lng - min_lng) / (max_lng - min_lng) * (width - 1))
            y = floor((max_lat - lat) / (max_lat - min_lat) * (height - 1))
            
            # Ensure within bounds
            x = min(max(x, 0), width - 1)
            y = min(max(y, 0), height - 1)
            
            map_array[y][x] = '•'

        # Mark start and end
        start_x = floor((coordinates[0][1] - min_lng) / (max_lng - min_lng) * (width - 1))
        start_y = floor((max_lat - coordinates[0][0]) / (max_lat - min_lat) * (height - 1))
        end_x = floor((coordinates[-1][1] - min_lng) / (max_lng - min_lng) * (width - 1))
        end_y = floor((max_lat - coordinates[-1][0]) / (max_lat - min_lat) * (height - 1))
        
        map_array[start_y][start_x] = 'S'
        map_array[end_y][end_x] = 'E'

        # Convert to string
        map_str = '```\n'  # Start code block
        map_str += '┌' + '─' * width + '┐\n'
        for row in map_array:
            map_str += '│' + ''.join(row) + '│\n'
        map_str += '└' + '─' * width + '┘\n'
        map_str += '```\n'  # End code block
        
        # Add legend
        map_str += 'Legend:\n'
        map_str += 'S: Start point\n'
        map_str += 'E: End point\n'
        map_str += '•: Route point\n'
        
        return map_str
    except Exception as e:
        logger.error(f"Failed to create ASCII map: {str(e)}", exc_info=True)
        raise ValueError(f"Failed to create ASCII map: {str(e)}") 