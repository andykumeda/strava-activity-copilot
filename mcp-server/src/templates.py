"""HTML templates for the Strava activity visualization."""

MAP_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>{activity_name}</title>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
    <style>
        body {{ margin: 0; padding: 0; }}
        #map {{ height: 400px; width: 100%; }}
        .activity-info {{
            padding: 20px;
            max-width: 800px;
            margin: 0 auto;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        .stat-card {{
            background: #f5f5f5;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .stat-value {{
            font-size: 24px;
            font-weight: bold;
            color: #2d3748;
        }}
        .stat-label {{
            color: #718096;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div id="map"></div>
    <div class="activity-info">
        <h1>{activity_name}</h1>
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{distance:.1f} km</div>
                <div class="stat-label">Distance</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{duration}</div>
                <div class="stat-label">Duration</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{avg_speed:.1f} km/h</div>
                <div class="stat-label">Average Speed</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{elevation_gain:.0f}m</div>
                <div class="stat-label">Elevation Gain</div>
            </div>
        </div>
    </div>
    <script>
        const map = L.map('map');
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '© OpenStreetMap contributors'
        }}).addTo(map);
        
        const coordinates = {coordinates};
        const polyline = L.polyline(coordinates, {{color: 'red', weight: 3}}).addTo(map);
        
        // Add start and end markers
        L.marker(coordinates[0]).addTo(map).bindPopup('Start');
        L.marker(coordinates[coordinates.length - 1]).addTo(map).bindPopup('End');
        
        // Fit the map to show the entire route
        map.fitBounds(polyline.getBounds());
    </script>
</body>
</html>
""" 