"""Auto-generated tool module."""

from __future__ import annotations

import json
import math


def run(payload: str) -> str:
    """Calculate distance between two geographic coordinates using the Haversine formula."""
    try:
        data = json.loads(payload)
        lat1 = float(data.get("lat1", 0))
        lon1 = float(data.get("lon1", 0))
        lat2 = float(data.get("lat2", 0))
        lon2 = float(data.get("lon2", 0))
        unit = str(data.get("unit", "km")).lower().strip()
    except (json.JSONDecodeError, TypeError, ValueError):
        return "error: invalid payload — provide JSON with lat1, lon1, lat2, lon2"

    R = 6371  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance_km = R * c

    if unit == "mi":
        distance = round(distance_km * 0.621371, 2)
    elif unit == "m":
        distance = round(distance_km * 1000, 1)
    else:
        distance = round(distance_km, 2)

    bearing = math.degrees(math.atan2(
        math.sin(dlon) * math.cos(math.radians(lat2)),
        math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) -
        math.sin(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.cos(dlon)
    ))
    bearing = (bearing + 360) % 360

    return json.dumps({
        "from": {"lat": lat1, "lon": lon1},
        "to": {"lat": lat2, "lon": lon2},
        "distance": distance,
        "unit": unit,
        "bearing_degrees": round(bearing, 1),
        "bearing_direction": _bearing_to_direction(bearing),
    }, indent=2, ensure_ascii=False)


def _bearing_to_direction(degrees: float) -> str:
    directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                  "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    idx = round(degrees / 22.5) % 16
    return directions[idx]


TOOL_SPEC = {
    "name": "geo_distance",
    "description": "Calculate the great-circle distance and bearing between two geographic coordinates using the Haversine formula. Supports km, miles, and meters.",
    "category": "analysis",
    "domain": "travel",
    "risk_level": "read",
    "schema": {
        "type": "object",
        "properties": {
            "lat1": {"type": "number", "description": "Latitude of first point (decimal degrees)."},
            "lon1": {"type": "number", "description": "Longitude of first point (decimal degrees)."},
            "lat2": {"type": "number", "description": "Latitude of second point (decimal degrees)."},
            "lon2": {"type": "number", "description": "Longitude of second point (decimal degrees)."},
            "unit": {
                "type": "string",
                "description": "Distance unit: km (default), mi (miles), or m (meters).",
                "enum": ["km", "mi", "m"],
                "default": "km"
            }
        },
        "required": ["lat1", "lon1", "lat2", "lon2"]
    }
}
