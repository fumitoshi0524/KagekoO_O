"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    import math

    try:
        data = json.loads(payload)
        location = data.get('location')
        radius_km = data.get('radius_km')
        category_filter = data.get('category_filter', 'all')
        max_results = data.get('max_results', 20)
        sort_by = data.get('sort_by', 'distance')

        if not location or not radius_km:
            return json.dumps({"error": "Missing required fields: location and radius_km are required."})
        if not isinstance(radius_km, (int, float)) or radius_km < 1 or radius_km > 100:
            return json.dumps({"error": "radius_km must be between 1 and 100."})

        # Parse location: try latitude,longitude first
        lat, lon = None, None
        if ',' in location:
            parts = location.split(',')
            if len(parts) == 2:
                try:
                    lat = float(parts[0].strip())
                    lon = float(parts[1].strip())
                except ValueError:
                    pass
        # If not latitude/longitude, treat as address (simulate geocoding with dummy coordinates)
        if lat is None:
            # In production, use a geocoding API; here we return a placeholder
            return json.dumps({"error": "Could not parse location. Provide as 'latitude,longitude' or a valid address."})

        # Simulate a database of attractions near Paris (for demonstration)
        attractions_db = [
            {"name": "Eiffel Tower", "category": "monument", "lat": 48.8584, "lon": 2.2945, "rating": 4.7},
            {"name": "Louvre Museum", "category": "museum", "lat": 48.8606, "lon": 2.3376, "rating": 4.8},
            {"name": "Notre-Dame Cathedral", "category": "monument", "lat": 48.8530, "lon": 2.3499, "rating": 4.6},
            {"name": "Luxembourg Gardens", "category": "park", "lat": 48.8462, "lon": 2.3372, "rating": 4.5},
            {"name": "Sacré-Cœur Basilica", "category": "monument", "lat": 48.8867, "lon": 2.3431, "rating": 4.6},
            {"name": "Musée d'Orsay", "category": "museum", "lat": 48.8600, "lon": 2.3266, "rating": 4.7},
            {"name": "Arc de Triomphe", "category": "monument", "lat": 48.8738, "lon": 2.2950, "rating": 4.5},
            {"name": "Tuileries Garden", "category": "park", "lat": 48.8640, "lon": 2.3230, "rating": 4.4},
            {"name": "Centre Pompidou", "category": "museum", "lat": 48.8606, "lon": 2.3524, "rating": 4.3},
            {"name": "Montmartre", "category": "landmark", "lat": 48.8867, "lon": 2.3410, "rating": 4.5},
        ]

        def haversine(lat1, lon1, lat2, lon2):
            R = 6371
            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lat2 - lon1)
            a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
            return R * c

        results = []
        for attr in attractions_db:
            distance = haversine(lat, lon, attr['lat'], attr['lon'])
            if distance <= radius_km:
                if category_filter != 'all' and attr['category'] != category_filter:
                    continue
                results.append({
                    "name": attr['name'],
                    "category": attr['category'],
                    "distance_km": round(distance, 2),
                    "rating": attr['rating'],
                    "latitude": attr['lat'],
                    "longitude": attr['lon']
                })

        if sort_by == 'rating':
            results.sort(key=lambda x: x['rating'], reverse=True)
        else:
            results.sort(key=lambda x: x['distance_km'])

        results = results[:max_results]

        return json.dumps({
            "location": {"latitude": lat, "longitude": lon},
            "radius_km": radius_km,
            "count": len(results),
            "attractions": results
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": str(e)})


TOOL_SPEC = {
    "name": "find_nearby_attractions",
    "description": "Search for tourist attractions, landmarks, and points of interest near a given geographic location (latitude/longitude) or address, returning a list of nearby places with names, categories, distances, and ratings.",
    "category": "search",
    "domain": "travel",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "location": {
            "type": "string",
            "description": "Geographic location as 'latitude,longitude' (e.g., '48.8566,2.3522') or a free-text address (e.g., 'Eiffel Tower, Paris') to search around."
        },
        "radius_km": {
            "type": "number",
            "description": "Search radius in kilometers (1 to 100).",
            "minimum": 1,
            "maximum": 100
        },
        "category_filter": {
            "type": "string",
            "description": "Optional: Filter results by attraction type. Allowed values: 'museum', 'park', 'monument', 'restaurant', 'hotel', 'shopping', 'all'.",
            "enum": [
                "museum",
                "park",
                "monument",
                "restaurant",
                "hotel",
                "shopping",
                "all"
            ]
        },
        "max_results": {
            "type": "integer",
            "description": "Optional: Maximum number of results to return (1 to 50, default 20).",
            "minimum": 1,
            "maximum": 50
        },
        "sort_by": {
            "type": "string",
            "description": "Optional: Sort order for results. 'distance' sorts by proximity (ascending), 'rating' sorts by user rating (descending). Default: 'distance'.",
            "enum": [
                "distance",
                "rating"
            ]
        }
    },
    "required": [
        "location",
        "radius_km"
    ]
},
}
