"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Locate UNESCO World Heritage sites near a geographic location."""
    import json
    import math
    
    try:
        data = json.loads(payload)
        
        # Validate required inputs
        required = ["latitude", "longitude", "radius_km"]
        for field in required:
            if field not in data:
                return f"error: missing required field '{field}'"
        
        lat = float(data["latitude"])
        lon = float(data["longitude"])
        radius = float(data["radius_km"])
        
        # Validate ranges
        if lat < -90 or lat > 90:
            return "error: latitude must be between -90 and 90"
        if lon < -180 or lon > 180:
            return "error: longitude must be between -180 and 180"
        if radius < 1 or radius > 500:
            return "error: radius_km must be between 1 and 500"
        
        category_filter = data.get("category_filter")
        max_results = min(int(data.get("max_results", 10)), 50)
        
        # Simulated UNESCO World Heritage sites database (simplified)
        # In a real implementation, this would connect to UNESCO API or geospatial database
        heritage_sites = [
            {"name": "Eiffel Tower", "lat": 48.8584, "lon": 2.2945, "category": "cultural", "period": "19th century", "significance": "Iconic wrought-iron tower symbolizing French engineering and culture"},
            {"name": "Colosseum", "lat": 41.8902, "lon": 12.4922, "category": "cultural", "period": "Ancient Rome (72-80 AD)", "significance": "Largest ancient amphitheater, representing Roman architectural and engineering achievement"},
            {"name": "Great Wall of China", "lat": 40.4319, "lon": 116.5704, "category": "cultural", "period": "7th century BC - 16th century", "significance": "Extensive fortification system representing Chinese defensive architecture"},
            {"name": "Machu Picchu", "lat": -13.1631, "lon": -72.5450, "category": "mixed", "period": "15th century", "significance": "Incan citadel built in the Andes mountains, showcasing Incan engineering and astronomy"},
            {"name": "Taj Mahal", "lat": 27.1751, "lon": 78.0421, "category": "cultural", "period": "1632-1653", "significance": "White marble mausoleum exemplifying Mughal architecture and love"},
            {"name": "Amazon Rainforest", "lat": -3.4653, "lon": -62.2159, "category": "natural", "period": "Formed over 55 million years", "significance": "Largest tropical rainforest with immense biodiversity and indigenous cultures"},
            {"name": "Pyramids of Giza", "lat": 29.9792, "lon": 31.1342, "category": "cultural", "period": "2580-2560 BC", "significance": "Ancient Egyptian pyramid complex representing pharaonic civilization"},
            {"name": "Great Barrier Reef", "lat": -18.2871, "lon": 147.6992, "category": "natural", "period": "Formed over millions of years", "significance": "World's largest coral reef system with exceptional marine biodiversity"},
            {"name": "Acropolis of Athens", "lat": 37.9715, "lon": 23.7267, "category": "cultural", "period": "5th century BC", "significance": "Ancient citadel symbolizing classical Greek civilization and democracy"},
            {"name": "Stonehenge", "lat": 51.1789, "lon": -1.8262, "category": "cultural", "period": "3000-2000 BC", "significance": "Prehistoric monument with astronomical alignment, representing Neolithic engineering"}
        ]
        
        def haversine(lat1, lon1, lat2, lon2):
            """Calculate distance between two points on Earth using Haversine formula."""
            R = 6371  # Earth radius in km
            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lon2 - lon1)
            a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
            return R * c
        
        # Filter sites by distance and category
        nearby_sites = []
        for site in heritage_sites:
            distance = haversine(lat, lon, site["lat"], site["lon"])
            if distance <= radius:
                if category_filter and site["category"] != category_filter:
                    continue
                site_copy = site.copy()
                site_copy["distance_km"] = round(distance, 1)
                nearby_sites.append(site_copy)
        
        # Sort by distance and limit results
        nearby_sites.sort(key=lambda x: x["distance_km"])
        nearby_sites = nearby_sites[:max_results]
        
        if not nearby_sites:
            result = {
                "found": False,
                "message": f"No UNESCO World Heritage sites found within {radius} km of the given location.",
                "sites": []
            }
        else:
            result = {
                "found": True,
                "count": len(nearby_sites),
                "center": {"latitude": lat, "longitude": lon},
                "search_radius_km": radius,
                "sites": nearby_sites
            }
        
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        return f"error: {str(e)}"


TOOL_SPEC = {
    "name": "cultural_heritage_locator",
    "description": "Locate and provide detailed information about UNESCO World Heritage sites near a given geographic location, returning site names, categories, historical periods, and significance descriptions for cultural exploration and trip planning.",
    "category": "system",
    "domain": "culture",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "latitude": {
            "type": "number",
            "description": "Latitude coordinate in decimal degrees (range: -90 to 90)"
        },
        "longitude": {
            "type": "number",
            "description": "Longitude coordinate in decimal degrees (range: -180 to 180)"
        },
        "radius_km": {
            "type": "number",
            "description": "Search radius in kilometers from the given coordinates (range: 1 to 500)"
        },
        "category_filter": {
            "type": "string",
            "description": "Optional: Filter sites by UNESCO category. Options: cultural, natural, mixed",
            "enum": [
                "cultural",
                "natural",
                "mixed"
            ]
        },
        "max_results": {
            "type": "integer",
            "description": "Optional: Maximum number of sites to return (range: 1 to 50, default: 10)"
        }
    },
    "required": [
        "latitude",
        "longitude",
        "radius_km"
    ]
},
}
