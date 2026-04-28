"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Search for sports venues by location, sport type, and required amenities, returning a list of matching venues with capacity, available activities, and user ratings."""
    import json
    import math
    import random

    try:
        data = json.loads(payload)
        
        # Validate required fields
        required = ["latitude", "longitude", "radius_km"]
        for field in required:
            if field not in data:
                return json.dumps({"error": f"Missing required field: {field}"}, ensure_ascii=False)
        
        lat = data["latitude"]
        lon = data["longitude"]
        radius = data["radius_km"]
        
        if not isinstance(lat, (int, float)) or lat < -90 or lat > 90:
            return json.dumps({"error": "Latitude must be a number between -90 and 90"}, ensure_ascii=False)
        if not isinstance(lon, (int, float)) or lon < -180 or lon > 180:
            return json.dumps({"error": "Longitude must be a number between -180 and 180"}, ensure_ascii=False)
        if not isinstance(radius, (int, float)) or radius < 0.5 or radius > 100:
            return json.dumps({"error": "Radius must be between 0.5 and 100 km"}, ensure_ascii=False)
        
        sport_filter = data.get("sport_type", "")
        min_capacity = data.get("min_capacity", 1)
        indoor_outdoor = data.get("indoor_outdoor", "any")
        max_results = data.get("max_results", 20)
        
        # Simulate a database of sports venues around the world
        # In production, this would query a real venue database or API
        
        # Generate realistic venues based on location density (more venues near cities)
        # Use latitude to bias venue density (more venues in populated regions)
        base_density = max(1, int(50 * (1 - abs(lat) / 90)))
        num_venues = random.randint(base_density, base_density * 3)
        
        sport_types = ["basketball", "tennis", "swimming", "soccer", "golf", "baseball", "volleyball", "badminton", "squash", "hockey", "boxing", "yoga", "gym"]
        venue_names = ["SportsPlex", "Athletic Center", "Arena", "Stadium", "Field House", "Sports Club", "Recreation Center", "Gymnasium", "Sports Park", "Training Facility", "Multi-Sport Center", "Olympic Complex", "Community Sports Hub", "Elite Performance Center", "Sports Village"]
        
        venues = []
        for i in range(num_venues):
            # Random position within radius (using polar coordinates)
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(0.1, radius)  # km from center
            
            # Convert distance to lat/lon offset (rough approximation)
            lat_offset = dist / 111.32 * math.cos(angle)
            lon_offset = dist / (111.32 * math.cos(math.radians(lat))) * math.sin(angle)
            
            venue_lat = round(lat + lat_offset, 4)
            venue_lon = round(lon + lon_offset, 4)
            
            venue_sports = random.sample(sport_types, random.randint(1, 4))
            
            # Apply sport filter
            if sport_filter and sport_filter not in venue_sports:
                continue
            
            is_indoor = random.choice([True, False])
            if indoor_outdoor == "indoor" and not is_indoor:
                continue
            if indoor_outdoor == "outdoor" and is_indoor:
                continue
            
            capacity = random.randint(50, 50000)
            if capacity < min_capacity:
                continue
            
            venue = {
                "name": f"{random.choice(venue_names)} #{i+1}",
                "address": f"{random.randint(100, 9999)} Sports Boulevard",
                "city": "Nearby City",
                "latitude": venue_lat,
                "longitude": venue_lon,
                "distance_km": round(dist, 2),
                "is_indoor": is_indoor,
                "capacity": capacity,
                "available_sports": venue_sports,
                "rating": round(random.uniform(1.0, 5.0), 1),
                "amenities": random.sample(["parking", "locker_rooms", "cafe", "pro_shop", "lighting", "heating", "air_conditioning", "seating", "scoreboard", "first_aid"], random.randint(2, 6)),
                "price_per_hour": round(random.uniform(10, 200), 2),
                "opening_hours": "06:00-22:00"
            }
            venues.append(venue)
        
        # Sort by distance
        venues.sort(key=lambda v: v["distance_km"])
        
        # Limit results
        venues = venues[:max_results]
        
        result = {
            "query": {
                "latitude": lat,
                "longitude": lon,
                "radius_km": radius,
                "sport_filter": sport_filter if sport_filter else "all",
                "min_capacity": min_capacity
            },
            "total_results": len(venues),
            "venues": venues
        }
        
        return json.dumps(result, ensure_ascii=False)
        
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON payload"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "sport_venue_finder",
    "description": "Search for sports venues by location, sport type, and required amenities, returning a list of matching venues with capacity, available activities, and user ratings.",
    "category": "search",
    "domain": "sports",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "latitude": {
            "type": "number",
            "description": "Center point latitude for the search radius, in decimal degrees (-90 to 90)."
        },
        "longitude": {
            "type": "number",
            "description": "Center point longitude for the search radius, in decimal degrees (-180 to 180)."
        },
        "radius_km": {
            "type": "number",
            "description": "Search radius from the center point in kilometers, must be between 0.5 and 100.",
            "minimum": 0.5,
            "maximum": 100
        },
        "sport_type": {
            "type": "string",
            "description": "Optional: Filter venues by the specific sport they support (e.g., 'basketball', 'tennis', 'swimming', 'soccer', 'golf'). Leave empty for all types.",
            "enum": [
                "basketball",
                "tennis",
                "swimming",
                "soccer",
                "golf",
                "baseball",
                "volleyball",
                "badminton",
                "squash",
                "hockey",
                "boxing",
                "yoga",
                "gym",
                ""
            ]
        },
        "min_capacity": {
            "type": "integer",
            "description": "Optional: Minimum venue capacity in number of people (e.g., 100 for small events, 1000+ for large stadiums).",
            "minimum": 1
        },
        "indoor_outdoor": {
            "type": "string",
            "description": "Optional: Filter by venue type (indoor, outdoor, or both).",
            "enum": [
                "indoor",
                "outdoor",
                "any"
            ]
        },
        "max_results": {
            "type": "integer",
            "description": "Optional: Maximum number of venues to return, between 1 and 50. Defaults to 20 if not specified.",
            "minimum": 1,
            "maximum": 50,
            "default": 20
        }
    },
    "required": [
        "latitude",
        "longitude",
        "radius_km"
    ]
},
}
