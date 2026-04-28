"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a Gantt-style timeline visualization for a multi-day trip itinerary."""
    import json
    try:
        data = json.loads(payload)
        trip_name = data.get("trip_name", "Untitled Trip")
        timezone = data.get("timezone", "UTC")
        activities = data.get("activities", [])
        if not activities:
            return json.dumps({"error": "At least one activity is required."}, ensure_ascii=False)
        dates = data.get("dates", [])
        max_day = max(a["day"] for a in activities)
        # Basic validation
        for a in activities:
            if not (0 <= int(a["start_time"][:2]) < 24 and 0 <= int(a["start_time"][3:]) < 60):
                return json.dumps({"error": f"Invalid start_time: {a['start_time']}"}, ensure_ascii=False)
            if not (0 <= int(a["end_time"][:2]) < 24 and 0 <= int(a["end_time"][3:]) < 60):
                return json.dumps({"error": f"Invalid end_time: {a['end_time']}"}, ensure_ascii=False)
            if a["start_time"] >= a["end_time"]:
                return json.dumps({"error": f"start_time {a['start_time']} must be before end_time {a['end_time']}"}, ensure_ascii=False)
        # Build timeline structure
        timeline = []
        for day_num in range(1, max_day + 1):
            day_activities = [a for a in activities if a["day"] == day_num]
            day_activities.sort(key=lambda x: x["start_time"])
            day_label = dates[day_num - 1] if day_num <= len(dates) else f"Day {day_num}"
            entries = []
            for a in day_activities:
                entry = {
                    "activity": a["activity"],
                    "start_time": a["start_time"],
                    "end_time": a["end_time"],
                    "location": a.get("location", "")
                }
                entries.append(entry)
            timeline.append({"day": day_num, "day_label": day_label, "activities": entries})
        result = {
            "trip_name": trip_name,
            "timezone": timezone,
            "total_days": max_day,
            "total_activities": len(activities),
            "timeline": timeline
        }
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "itinerary_gantt",
    "description": "Generate a Gantt-style timeline visualization for a multi-day trip itinerary, showing activities, durations, and locations per day.",
    "category": "visualization",
    "domain": "travel",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "trip_name": {
            "type": "string",
            "description": "Name of the trip (e.g., 'Tokyo Autumn 2025')."
        },
        "timezone": {
            "type": "string",
            "description": "IANA timezone identifier for the trip (e.g., 'Asia/Tokyo').",
            "default": "UTC"
        },
        "activities": {
            "type": "array",
            "description": "List of activities in chronological order.",
            "items": {
                "type": "object",
                "properties": {
                    "day": {
                        "type": "integer",
                        "description": "Day number of the trip (1-based)."
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Start time in HH:MM 24-hour format."
                    },
                    "end_time": {
                        "type": "string",
                        "description": "End time in HH:MM 24-hour format."
                    },
                    "activity": {
                        "type": "string",
                        "description": "Short activity label (e.g., 'Senso-ji Temple visit')."
                    },
                    "location": {
                        "type": "string",
                        "description": "Optional: Location or venue name."
                    }
                },
                "required": [
                    "day",
                    "start_time",
                    "end_time",
                    "activity"
                ]
            }
        },
        "dates": {
            "type": "array",
            "description": "Optional: Array of date strings (YYYY-MM-DD) for each day, length must match max day number.",
            "items": {
                "type": "string"
            }
        }
    },
    "required": [
        "trip_name",
        "activities"
    ]
},
}
