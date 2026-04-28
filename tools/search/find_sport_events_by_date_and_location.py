"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    import random
    from datetime import datetime, timedelta
    try:
        data = json.loads(payload)
        date_str = data.get("date")
        location = data.get("location", None)
        sport_type = data.get("sport_type", "")
        radius_km = data.get("radius_km", 50)
        max_results = data.get("max_results", 20)
        if max_results < 1 or max_results > 100:
            max_results = 20
        # Validate date format
        try:
            event_date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return json.dumps({"error": "Invalid date format. Use YYYY-MM-DD."})
        if event_date < datetime.now() - timedelta(days=1):
            return json.dumps({"error": "Date cannot be in the past."})
        # Simulate a search against a sports event database
        # In production, this would query an API or database
        # Generate plausible mock events for demonstration
        mock_events = []
        sports = [
            {"name": "Soccer", "teams": ["Lions FC", "Eagles United", "Tornados SC", "Thunderbolts"]},
            {"name": "Basketball", "teams": ["Slam Dunkers", "Hoops Masters", "Net Rippers", "Airballers"]},
            {"name": "Tennis", "teams": ["Ace Rackets", "Volley Kings"]},
            {"name": "Running", "teams": ["Marathon Runners", "Sprint Stars"]},
            {"name": "Swimming", "teams": ["Aqua Jets", "Wave Riders"]},
            {"name": "Cycling", "teams": ["Pedal Pushers", "Wheel Speeders"]}
        ]
        if sport_type:
            filtered = [s for s in sports if s["name"].lower() == sport_type.lower()]
            if not filtered:
                # try partial match
                filtered = [s for s in sports if sport_type.lower() in s["name"].lower()]
            if filtered:
                sports = filtered
        # Generate events
        for i in range(min(max_results, len(sports) * 2)):
            sport = random.choice(sports)
            team1 = random.choice(sport["teams"])
            team2 = random.choice([t for t in sport["teams"] if t != team1]) if len(sport["teams"]) > 1 else team1
            venue = f"{random.choice(['Stadium', 'Arena', 'Field', 'Track', 'Pool', 'Velodrome'])} {random.randint(1, 10)}"
            start_hour = random.randint(8, 22)
            start_minute = random.randint(0, 59)
            start_time = f"{start_hour:02d}:{start_minute:02d}"
            event = {
                "event_name": f"{sport['name']} Match: {team1} vs {team2}",
                "sport_type": sport["name"],
                "teams_or_athletes": [team1, team2],
                "venue": venue,
                "start_time": f"{date_str} {start_time}",
                "location": location if location else "Global",
                "distance_km": round(random.uniform(1, radius_km), 1) if location else None
            }
            mock_events.append(event)
        # Remove duplicates (by event name)
        seen = set()
        unique_events = []
        for e in mock_events:
            key = e["event_name"]
            if key not in seen:
                seen.add(key)
                unique_events.append(e)
        result = {
            "search_params": {
                "date": date_str,
                "location": location,
                "sport_type": sport_type if sport_type else "all",
                "radius_km": radius_km,
                "max_results": max_results
            },
            "events": unique_events[:max_results],
            "total_found": len(unique_events)
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Failed to search events: {str(e)}"})


TOOL_SPEC = {
    "name": "find_sport_events_by_date_and_location",
    "description": "Search for sports events (matches, tournaments, races, etc.) on a given date or date range near a specified location, returning event names, start times, venues, and participating teams or athletes. Useful for planning attendance or viewing schedules.",
    "category": "search",
    "domain": "sports",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "date": {
            "type": "string",
            "description": "Date of interest in YYYY-MM-DD format"
        },
        "location": {
            "type": "string",
            "description": "City name, address, or geographic coordinates (latitude,longitude) to search near. Optional: if omitted, search returns events globally."
        },
        "sport_type": {
            "type": "string",
            "description": "Optional: filter by sport type (e.g., soccer, basketball, tennis, running). Leave empty for all sports."
        },
        "radius_km": {
            "type": "number",
            "description": "Optional: search radius in kilometers around the given location (default 50). Only used if location is provided."
        },
        "max_results": {
            "type": "integer",
            "description": "Optional: maximum number of events to return (default 20, max 100)."
        }
    },
    "required": [
        "date"
    ]
},
}
