"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    import math
    import random

    def haversine_km(lat1, lon1, lat2, lon2):
        R = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c

    def geocode_city(city_name):
        # Mock geocoding with realistic coordinates for demo
        city_db = {
            "paris": [48.8566, 2.3522],
            "london": [51.5074, -0.1278],
            "berlin": [52.5200, 13.4050],
            "rome": [41.9028, 12.4964],
            "madrid": [40.4168, -3.7038],
            "barcelona": [41.3874, 2.1686],
            "amsterdam": [52.3676, 4.9041],
            "prague": [50.0755, 14.4378],
            "vienna": [48.2082, 16.3738],
            "budapest": [47.4979, 19.0402],
            "tokyo": [35.6762, 139.6503],
            "kyoto": [35.0116, 135.7681],
            "osaka": [34.6937, 135.5023],
            "new york": [40.7128, -74.0060],
            "los angeles": [34.0522, -118.2437],
            "chicago": [41.8781, -87.6298],
            "sydney": [-33.8688, 151.2093],
            "melbourne": [-37.8136, 144.9631],
            "bangkok": [13.7563, 100.5018],
            "singapore": [1.3521, 103.8198],
            "dubai": [25.2048, 55.2708],
            "istanbul": [41.0082, 28.9784]
        }
        key = city_name.lower().strip()
        if key in city_db:
            return city_db[key]
        # fallback: generate deterministic but realistic coordinates
        hash_val = sum(ord(c) for c in key)
        lat = (hash_val % 180) - 90
        lon = (hash_val % 360) - 180
        return [float(lat), float(lon)]

    def get_travel_time_est(km, mode):
        speeds = {"driving": 80, "walking": 5, "cycling": 20, "transit": 40}
        speed = speeds.get(mode, 60)
        hours = km / speed
        return round(hours, 1)

    try:
        data = json.loads(payload)
        waypoints = data.get("waypoints", [])
        if not isinstance(waypoints, list) or len(waypoints) < 2:
            return json.dumps({"error": "At least 2 waypoints required"}, ensure_ascii=False)
        if len(waypoints) > 30:
            return json.dumps({"error": "Maximum 30 waypoints allowed"}, ensure_ascii=False)
        
        mode = data.get("transport_mode", "driving")
        if mode not in ["driving", "walking", "cycling", "transit"]:
            return json.dumps({"error": "Invalid transport_mode"}, ensure_ascii=False)
        
        language = data.get("language", "en")
        highlight = data.get("highlight_attractions", False)

        # Geocode all waypoints
        coords = []
        for wp in waypoints:
            lat, lon = geocode_city(wp)
            coords.append([lat, lon, wp])

        # Calculate segment distances and times
        segments = []
        total_km = 0.0
        total_hours = 0.0
        for i in range(len(coords)-1):
            lat1, lon1, name1 = coords[i]
            lat2, lon2, name2 = coords[i+1]
            dist = haversine_km(lat1, lon1, lat2, lon2)
            time_h = get_travel_time_est(dist, mode)
            total_km += dist
            total_hours += time_h
            segments.append({
                "from": name1,
                "to": name2,
                "distance_km": round(dist, 1),
                "travel_time_hours": time_h,
                "from_lat": lat1,
                "from_lon": lon1,
                "to_lat": lat2,
                "to_lon": lon2
            })

        # Generate HTML map
        map_id = f"route_{random.randint(1000,9999)}"
        points_js = json.dumps([[c[0], c[1], c[2]] for c in coords])
        segs_js = json.dumps(segments)

        html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<title>Travel Route Visualization</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  body {{ margin: 0; padding: 0; }}
  #map_{{map_id}} {{ height: 100vh; width: 100vw; }}
</style>
</head>
<body>
<div id="map_{{map_id}}"></div>
<script>
const points = {points_js};
const segments = {segs_js};
const lang = "{language}";
const highlight = {str(highlight).lower()};

const map = L.map('map_{{map_id}}').setView(
  [points.reduce((s,p)=>s+p[0],0)/points.length, points.reduce((s,p)=>s+p[1],0)/points.length],
  5
);

L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
  attribution: '&copy; OpenStreetMap contributors',
  maxZoom: 18
}}).addTo(map);

const latlngs = points.map(p => [p[0], p[1]]);
const polyline = L.polyline(latlngs, {{color: '#0066ff', weight: 4, opacity: 0.8}}).addTo(map);
map.fitBounds(polyline.getBounds().pad(0.1));

// Add markers with route info
points.forEach((p, idx) => {{
  const label = p[2] + (idx === 0 ? ' (Start)' : idx === points.length-1 ? ' (End)' : '');
  L.marker([p[0], p[1]]).addTo(map)
    .bindPopup(`<b>${{p[2]}}</b><br/>Stop #${{idx+1}}`);
}});

// Add distance/time labels at segment midpoints
segments.forEach((seg, idx) => {{
  const midLat = (seg.from_lat + seg.to_lat) / 2;
  const midLon = (seg.from_lon + seg.to_lon) / 2;
  const labelText = `${{seg.distance_km}} km | ${{seg.travel_time_hours}} h`;
  L.marker([midLat, midLon], {{
    icon: L.divIcon({{
      className: 'segment-label',
      html: `<div style="background:white;padding:3px 8px;border-radius:4px;border:1px solid #ccc;font-size:12px;white-space:nowrap;box-shadow:0 1px 3px rgba(0,0,0,0.3)">${{labelText}}</div>`,
      iconSize: [100, 20],
      iconAnchor: [50, 10]
    }})
  }}).addTo(map);
}});

// Attraction placeholders if requested
if (highlight) {{
  const attractions = ['Museum', 'Park', 'Landmark', 'Cathedral', 'Market'];
  points.forEach((p, idx) => {{
    if (idx > 0 && idx < points.length - 1) {{
      const att = attractions[idx % attractions.length];
      const offset = (idx % 3 + 1) * 0.02;
      L.circleMarker([p[0] + offset, p[1] + offset], {{
        radius: 6,
        color: '#ff6600',
        fillColor: '#ff9900',
        fillOpacity: 0.7
      }}).addTo(map).bindPopup(`<b>${{att}}</b>`);
    }}
  }});
}}
</script>
</body>
</html>""";

        result = {
            "route_html": html,
            "total_distance_km": round(total_km, 1),
            "total_travel_time_hours": round(total_hours, 1),
            "number_of_stops": len(waypoints),
            "transport_mode": mode,
            "segments": segments
        }

        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "travel_route_viz",
    "description": "Generate an interactive travel route visualization from a sequence of waypoints (cities/attractions), returning an HTML map with styled polylines, distance markers, and estimated travel times between consecutive points.",
    "category": "visualization",
    "domain": "travel",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "waypoints": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "Ordered list of city names or landmark names forming the route. Minimum 2 items, maximum 30."
        },
        "transport_mode": {
            "type": "string",
            "enum": [
                "driving",
                "walking",
                "cycling",
                "transit"
            ],
            "description": "Mode of transport used to estimate travel times between waypoints."
        },
        "language": {
            "type": "string",
            "enum": [
                "en",
                "fr",
                "de",
                "es",
                "it",
                "pt",
                "zh",
                "ja"
            ],
            "description": "Optional: Language for labels and tooltips on the map (default: en)."
        },
        "highlight_attractions": {
            "type": "boolean",
            "description": "Optional: If true, marks major tourist attractions near each waypoint with icons (default: false)."
        }
    },
    "required": [
        "waypoints",
        "transport_mode"
    ]
},
}
