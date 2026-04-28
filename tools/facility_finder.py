"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Search healthcare facilities by location, specialty, and insurance network."""
    import json
    import math
    from typing import Optional

    # Simulated database of healthcare facilities
    FACILITIES_DB = [
        {
            "id": 1,
            "name": "City General Hospital",
            "type": "hospital",
            "lat": 40.7128, "lon": -74.0060,
            "address": "123 Main St, New York, NY 10001",
            "phone": "+1-212-555-0100",
            "hours": "24/7",
            "rating": 4.2,
            "specialties": ["cardiology", "emergency_medicine", "orthopedics", "pediatrics"],
            "accepted_insurance": ["BlueCross", "Aetna", "UnitedHealth", "Cigna"]
        },
        {
            "id": 2,
            "name": "Greenhill Medical Clinic",
            "type": "clinic",
            "lat": 40.7580, "lon": -73.9855,
            "address": "456 Park Ave, New York, NY 10022",
            "phone": "+1-212-555-0101",
            "hours": "Mon-Fri 8am-8pm, Sat 9am-5pm",
            "rating": 4.5,
            "specialties": ["primary_care", "pediatrics", "dermatology"],
            "accepted_insurance": ["BlueCross", "Aetna", "UnitedHealth"]
        },
        {
            "id": 3,
            "name": "QuickCare Urgent Care - Manhattan",
            "type": "urgent_care",
            "lat": 40.7300, "lon": -73.9950,
            "address": "789 Broadway, New York, NY 10003",
            "phone": "+1-212-555-0102",
            "hours": "7am-10pm daily",
            "rating": 3.8,
            "specialties": ["emergency_medicine", "urgent_care"],
            "accepted_insurance": ["BlueCross", "Aetna", "Cigna"]
        },
        {
            "id": 4,
            "name": "Presidio Orthopedic Center",
            "type": "clinic",
            "lat": 40.7440, "lon": -73.9900,
            "address": "321 Madison Ave, New York, NY 10016",
            "phone": "+1-212-555-0103",
            "hours": "Mon-Fri 9am-6pm",
            "rating": 4.7,
            "specialties": ["orthopedics"],
            "accepted_insurance": ["Aetna", "UnitedHealth", "Cigna"]
        },
        {
            "id": 5,
            "name": "Children's Health Hospital",
            "type": "hospital",
            "lat": 40.7520, "lon": -73.9800,
            "address": "555 E 34th St, New York, NY 10016",
            "phone": "+1-212-555-0104",
            "hours": "24/7",
            "rating": 4.9,
            "specialties": ["pediatrics", "cardiology"],
            "accepted_insurance": ["BlueCross", "Aetna", "UnitedHealth"]
        }
    ]

    def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance in miles between two coordinates."""
        R = 3958.8  # Earth radius in miles
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c

    def match_insurance(accepted: list, provider: Optional[str]) -> bool:
        if not provider:
            return True
        return provider.lower() in [i.lower() for i in accepted]

    def match_specialty(specialties: list, specialty: Optional[str]) -> bool:
        if not specialty:
            return True
        return specialty.lower() in [s.lower() for s in specialties]

    try:
        data = json.loads(payload)
        
        # Validate required fields
        required = ["latitude", "longitude", "radius_miles"]
        for field in required:
            if field not in data:
                return json.dumps({"error": f"Missing required field: {field}"}, ensure_ascii=False)
        
        lat = float(data["latitude"])
        lon = float(data["longitude"])
        radius = float(data["radius_miles"])
        
        if radius < 1 or radius > 100:
            return json.dumps({"error": "radius_miles must be between 1 and 100"}, ensure_ascii=False)
        
        specialty = data.get("specialty")
        insurance = data.get("insurance_provider")
        facility_type = data.get("facility_type", "all")
        min_rating = data.get("min_rating")
        max_results = data.get("max_results", 20)
        
        if min_rating is not None:
            min_rating = float(min_rating)
            if min_rating < 1 or min_rating > 5:
                return json.dumps({"error": "min_rating must be between 1 and 5"}, ensure_ascii=False)
        
        if not isinstance(max_results, int) or max_results < 1 or max_results > 50:
            return json.dumps({"error": "max_results must be an integer between 1 and 50"}, ensure_ascii=False)
        
        if facility_type not in ["hospital", "clinic", "urgent_care", "all"]:
            return json.dumps({"error": "facility_type must be one of: hospital, clinic, urgent_care, all"}, ensure_ascii=False)
        
        # Filter and score facilities
        results = []
        for facility in FACILITIES_DB:
            dist = haversine(lat, lon, facility["lat"], facility["lon"])
            if dist > radius:
                continue
            if facility_type != "all" and facility["type"] != facility_type:
                continue
            if not match_specialty(facility["specialties"], specialty):
                continue
            if not match_insurance(facility["accepted_insurance"], insurance):
                continue
            if min_rating is not None and facility["rating"] < min_rating:
                continue
            
            results.append({
                "id": facility["id"],
                "name": facility["name"],
                "type": facility["type"],
                "address": facility["address"],
                "phone": facility["phone"],
                "hours": facility["hours"],
                "rating": facility["rating"],
                "distance_miles": round(dist, 2),
                "specialties": facility["specialties"],
                "accepted_insurance": facility["accepted_insurance"]
            })
        
        # Sort by distance (ascending) then by rating (descending)
        results.sort(key=lambda x: (x["distance_miles"], -x["rating"]))
        
        # Limit results
        limited_results = results[:max_results]
        
        return json.dumps({
            "facilities": limited_results,
            "count": len(limited_results),
            "query_center": {"latitude": lat, "longitude": lon},
            "radius_miles": radius
        }, ensure_ascii=False)
        
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON payload"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Internal error: {str(e)}"}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "facility_finder",
    "description": "Search for healthcare facilities by specialty, location radius, and insurance network. Returns a list of matching hospitals, clinics, and urgent care centers with contact info, distance, hours, and ratings.",
    "category": "search",
    "domain": "healthcare",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "latitude": {
            "type": "number",
            "description": "Latitude of the search center point in decimal degrees (e.g., 40.7128 for New York City).",
            "examples": [
                40.7128,
                34.0522
            ]
        },
        "longitude": {
            "type": "number",
            "description": "Longitude of the search center point in decimal degrees (e.g., -74.0060 for New York City).",
            "examples": [
                -74.006,
                -118.2437
            ]
        },
        "radius_miles": {
            "type": "number",
            "description": "Search radius from the center point in miles. Must be between 1 and 100.",
            "minimum": 1,
            "maximum": 100,
            "examples": [
                10,
                25
            ]
        },
        "specialty": {
            "type": "string",
            "description": "Medical specialty to filter facilities by (e.g., 'cardiology', 'orthopedics', 'pediatrics'). Optional: if omitted, no specialty filter is applied.",
            "examples": [
                "cardiology",
                "orthopedics"
            ]
        },
        "insurance_provider": {
            "type": "string",
            "description": "Insurance provider name to check network participation (e.g., 'BlueCross', 'Aetna', 'UnitedHealth'). Optional: if omitted, no insurance filter is applied.",
            "examples": [
                "BlueCross",
                "Aetna"
            ]
        },
        "facility_type": {
            "type": "string",
            "enum": [
                "hospital",
                "clinic",
                "urgent_care",
                "all"
            ],
            "description": "Type of healthcare facility to search for. Default is 'all' if not specified.",
            "examples": [
                "hospital",
                "urgent_care"
            ]
        },
        "min_rating": {
            "type": "number",
            "description": "Optional: Minimum star rating (1-5) to filter facilities. Only facilities with rating >= this value are returned.",
            "minimum": 1,
            "maximum": 5,
            "examples": [
                3.5,
                4
            ]
        },
        "max_results": {
            "type": "integer",
            "description": "Optional: Maximum number of results to return (1-50). Default is 20 if not specified.",
            "minimum": 1,
            "maximum": 50,
            "examples": [
                10,
                20
            ]
        }
    },
    "required": [
        "latitude",
        "longitude",
        "radius_miles"
    ]
},
}
