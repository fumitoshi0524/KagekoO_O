"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    import math
    import random
    from datetime import datetime, timedelta

    try:
        data = json.loads(payload)
        lat = data.get("latitude")
        lng = data.get("longitude")
        radius = data.get("radius_km")
        category = data.get("category")
        min_rating = data.get("min_rating", 0.0)
        open_now = data.get("open_now", False)
        max_results = min(data.get("max_results", 10), 50)

        if not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
            return json.dumps({"error": "latitude and longitude must be numbers"}, ensure_ascii=False)
        if not isinstance(radius, (int, float)) or radius < 0.1 or radius > 50:
            return json.dumps({"error": "radius_km must be between 0.1 and 50"}, ensure_ascii=False)
        if category not in ["restaurant", "cafe", "gym", "salon", "grocery", "laundromat"]:
            return json.dumps({"error": "Invalid category"}, ensure_ascii=False)

        # Simulate realistic venue database with deterministic but varied results
        venue_templates = {
            "restaurant": ["Bella Italia", "Sakura Sushi", "Golden Dragon", "Paris Bistro", "El Patio", "Tandoori Flame", "Pizza Paradise", "Burger Barn"],
            "cafe": ["Morning Brew", "Bean There", "Cuppa Joy", "Perk Up", "Brew & Bloom", "Steaming Mug"],
            "gym": ["FitZone", "Iron Haven", "Flex Gym", "Cardio Core", "Pump House"],
            "salon": ["Glamour Cuts", "Style Studio", "Shear Artistry", "Locks & Co."],
            "grocery": ["Fresh Mart", "Green Basket", "Daily Needs", "Corner Grocer"],
            "laundromat": ["Spin Cycle", "Clean & Dry", "Wash World", "Bubble Laundry"]
        }
        
        names = venue_templates[category]
        results = []
        for i, name in enumerate(names):
            # Generate semi-realistic coordinates within radius (approximate 1 degree lat = 111km)
            angle = random.uniform(0, 2 * math.pi)
            dist_km = random.uniform(0.1, radius)
            delta_lat = (dist_km / 111.0) * math.cos(angle)
            delta_lng = (dist_km / (111.0 * math.cos(math.radians(lat)))) * math.sin(angle)
            venue_lat = round(lat + delta_lat, 6)
            venue_lng = round(lng + delta_lng, 6)
            distance = round(math.sqrt((delta_lat*111)**2 + (delta_lng*111*math.cos(math.radians(lat)))**2), 2)
            rating = round(random.uniform(1.0, 5.0), 1)
            total_ratings = random.randint(10, 500)
            address = f"{random.randint(1,999)} {random.choice(['Main St', 'Oak Ave', 'Pine Rd', 'Elm Blvd', 'Park Lane'])}"
            
            # Simulate opening hours (simple 9am-10pm for demo)
            now = datetime.now()
            open_time = now.replace(hour=9, minute=0, second=0, microsecond=0)
            close_time = now.replace(hour=22, minute=0, second=0, microsecond=0)
            is_open = open_time <= now <= close_time

            if rating < min_rating:
                continue
            if open_now and not is_open:
                continue

            venue = {
                "name": name,
                "category": category,
                "address": address,
                "latitude": venue_lat,
                "longitude": venue_lng,
                "distance_km": distance,
                "rating": rating,
                "total_ratings": total_ratings,
                "open_now": is_open
            }
            results.append(venue)

        # Sort by distance
        results.sort(key=lambda x: x["distance_km"])
        results = results[:max_results]

        response = {
            "query": {
                "latitude": lat,
                "longitude": lng,
                "radius_km": radius,
                "category": category
            },
            "results": results,
            "total_found": len(results)
        }
        return json.dumps(response, ensure_ascii=False)

    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON payload"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "nearby_venue_finder",
    "description": "Search for nearby venues (restaurants, cafes, gyms, salons, grocery stores, laundromats) within a specified radius and return results sorted by distance with ratings, address, and category tags.",
    "category": "search",
    "domain": "lifestyle",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "latitude": {
            "type": "number",
            "description": "Latitude of the search center point in decimal degrees (range: -90 to 90)."
        },
        "longitude": {
            "type": "number",
            "description": "Longitude of the search center point in decimal degrees (range: -180 to 180)."
        },
        "radius_km": {
            "type": "number",
            "description": "Search radius in kilometers (minimum: 0.1, maximum: 50)."
        },
        "category": {
            "type": "string",
            "description": "Type of venue to search for.",
            "enum": [
                "restaurant",
                "cafe",
                "gym",
                "salon",
                "grocery",
                "laundromat"
            ]
        },
        "min_rating": {
            "type": "number",
            "description": "Optional: Minimum average rating filter (0.0 to 5.0). Only venues with rating >= this value are returned."
        },
        "open_now": {
            "type": "boolean",
            "description": "Optional: If True, only return venues currently open."
        },
        "max_results": {
            "type": "integer",
            "description": "Optional: Maximum number of results to return (1 to 50, default 10)."
        }
    },
    "required": [
        "latitude",
        "longitude",
        "radius_km",
        "category"
    ]
},
}
