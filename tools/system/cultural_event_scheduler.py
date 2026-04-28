"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    import hashlib
    from datetime import datetime

    try:
        data = json.loads(payload)
        # validate required fields
        required = ["title", "category", "date", "time", "venue", "organizer"]
        for field in required:
            if field not in data or not isinstance(data[field], str) or not data[field].strip():
                return json.dumps({"error": f"Missing or empty required field: {field}"}, ensure_ascii=False)

        title = data["title"].strip()
        if len(title) > 200:
            return json.dumps({"error": "Title exceeds 200 characters"}, ensure_ascii=False)

        category = data["category"]
        valid_categories = ["exhibition", "performance", "workshop", "festival", "lecture", "film_screening", "other"]
        if category not in valid_categories:
            return json.dumps({"error": f"Invalid category. Must be one of {valid_categories}"}, ensure_ascii=False)

        date_str = data["date"]
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return json.dumps({"error": "Date must be in YYYY-MM-DD format"}, ensure_ascii=False)

        time_str = data["time"]
        try:
            datetime.strptime(time_str, "%H:%M")
        except ValueError:
            return json.dumps({"error": "Time must be in HH:MM (24-hour) format"}, ensure_ascii=False)

        venue = data["venue"].strip()
        if len(venue) > 300:
            return json.dumps({"error": "Venue exceeds 300 characters"}, ensure_ascii=False)

        organizer = data["organizer"].strip()
        if len(organizer) > 150:
            return json.dumps({"error": "Organizer exceeds 150 characters"}, ensure_ascii=False)

        description = data.get("description", "")
        if len(description) > 1000:
            return json.dumps({"error": "Description exceeds 1000 characters"}, ensure_ascii=False)

        target_audience = data.get("target_audience", "all_ages")
        valid_audiences = ["all_ages", "children", "youth", "adults", "seniors", "professionals", "families"]
        if target_audience not in valid_audiences:
            return json.dumps({"error": f"Invalid target_audience. Must be one of {valid_audiences}"}, ensure_ascii=False)

        # generate a unique event ID based on input fields
        unique_string = title + date_str + time_str + venue
        event_id = hashlib.md5(unique_string.encode()).hexdigest()[:8]

        result = {
            "event_id": event_id,
            "status": "scheduled",
            "title": title,
            "category": category,
            "date": date_str,
            "time": time_str,
            "venue": venue,
            "organizer": organizer,
            "description": description,
            "target_audience": target_audience
        }
        return json.dumps(result, ensure_ascii=False)

    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON payload"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "cultural_event_scheduler",
    "description": "Schedule a cultural event (exhibition, performance, workshop, festival) by registering its title, category, date, time, venue, organizer, and optional target audience; returns the event ID and confirmation details.",
    "category": "system",
    "domain": "culture",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "title": {
            "type": "string",
            "description": "Official name of the cultural event (max 200 characters)."
        },
        "category": {
            "type": "string",
            "enum": [
                "exhibition",
                "performance",
                "workshop",
                "festival",
                "lecture",
                "film_screening",
                "other"
            ],
            "description": "Type of cultural event."
        },
        "date": {
            "type": "string",
            "description": "Event date in YYYY-MM-DD format."
        },
        "time": {
            "type": "string",
            "description": "Event start time in HH:MM (24-hour) format."
        },
        "venue": {
            "type": "string",
            "description": "Name or address of the venue where the event takes place (max 300 characters)."
        },
        "organizer": {
            "type": "string",
            "description": "Name of the organizing person or institution (max 150 characters)."
        },
        "description": {
            "type": "string",
            "description": "Optional: short description or program notes for the event (max 1000 characters)."
        },
        "target_audience": {
            "type": "string",
            "enum": [
                "all_ages",
                "children",
                "youth",
                "adults",
                "seniors",
                "professionals",
                "families"
            ],
            "description": "Optional: intended audience demographic for the event."
        }
    },
    "required": [
        "title",
        "category",
        "date",
        "time",
        "venue",
        "organizer"
    ]
},
}
