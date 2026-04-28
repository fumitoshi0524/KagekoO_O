"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Search for direct flight connections between two airports or cities."""
    import json
    try:
        data = json.loads(payload)
        origin = data.get("origin")
        dest = data.get("destination")
        date = data.get("departure_date")
        if not origin or not dest or not date:
            return json.dumps({"error": "Missing required fields: origin, destination, departure_date"})
        max_results = min(data.get("max_results", 10), 50)
        carrier = data.get("preferred_carrier", None)

        # Mock internal database of direct routes (in real system this would query an API or DB)
        routes = [
            {"airline": "AA", "flight": "AA100", "origin": "JFK", "dest": "LHR", "dept": "08:00", "arr": "20:00", "duration": "7h"},
            {"airline": "BA", "flight": "BA178", "origin": "LHR", "dest": "JFK", "dept": "10:30", "arr": "13:45", "duration": "8h15m"},
            {"airline": "DL", "flight": "DL404", "origin": "JFK", "dest": "CDG", "dept": "17:00", "arr": "06:30+1", "duration": "7h30m"},
            {"airline": "AF", "flight": "AF1234", "origin": "CDG", "dest": "JFK", "dept": "14:00", "arr": "16:30", "duration": "8h30m"},
            {"airline": "UA", "flight": "UA888", "origin": "SFO", "dest": "NRT", "dept": "11:00", "arr": "14:00+1", "duration": "11h"},
            {"airline": "BA", "flight": "BA289", "origin": "LHR", "dest": "LAX", "dept": "09:30", "arr": "13:00", "duration": "10h30m"},
            {"airline": "AA", "flight": "AA300", "origin": "LAX", "dest": "LHR", "dept": "21:00", "arr": "15:00+1", "duration": "10h"},
        ]

        results = []
        for r in routes:
            # Match origin (case-insensitive) either by code or city name
            # simplified: just check if origin part of r['origin'] (or match city names)
            if origin.upper() != r['origin'] and origin.upper() != r['dest']:  # basic matching
                pass
            # Actually match origin and destination
            if r['origin'] == origin.upper() and r['dest'] == dest.upper():
                if carrier is None or r['airline'] == carrier.upper():
                    results.append(r)
                    if len(results) >= max_results:
                        break

        return json.dumps({
            "origin": origin,
            "destination": dest,
            "date": date,
            "flights": results,
            "count": len(results)
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


TOOL_SPEC = {
    "name": "find_direct_flights",
    "description": "Search for direct flight connections between two airports or cities given departure and arrival locations, returning a list of available airlines, flight numbers, departure times, arrival times, and durations.",
    "category": "search",
    "domain": "travel",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "origin": {
            "type": "string",
            "description": "IATA airport code or city name for the departure point (e.g., LHR, JFK, London)."
        },
        "destination": {
            "type": "string",
            "description": "IATA airport code or city name for the arrival point (e.g., CDG, LAX, Paris)."
        },
        "departure_date": {
            "type": "string",
            "description": "Date of travel in YYYY-MM-DD format."
        },
        "max_results": {
            "type": "integer",
            "description": "Optional: maximum number of flight results to return (default 10, max 50).",
            "minimum": 1,
            "maximum": 50
        },
        "preferred_carrier": {
            "type": "string",
            "description": "Optional: IATA airline code (e.g., AA for American Airlines, BA for British Airways) to filter results by a specific carrier."
        }
    },
    "required": [
        "origin",
        "destination",
        "departure_date"
    ]
},
}
