"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    import uuid
    from datetime import datetime

    try:
        data = json.loads(payload)
        title = data.get("title")
        description = data.get("description")
        category = data.get("category")
        date_str = data.get("date")
        location = data.get("location")
        organizer_name = data.get("organizer_name")
        ticket_price = data.get("ticket_price", 0.0)

        if not all([title, description, category, date_str, location, organizer_name]):
            return json.dumps({"error": "Missing required fields"}, ensure_ascii=False)

        # Validate date
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return json.dumps({"error": "Invalid date format. Must be YYYY-MM-DD."}, ensure_ascii=False)

        if len(title) > 200:
            return json.dumps({"error": "Title too long (max 200 chars)"}, ensure_ascii=False)
        if len(description) > 1000:
            return json.dumps({"error": "Description too long (max 1000 chars)"}, ensure_ascii=False)

        if ticket_price is not None and ticket_price < 0:
            return json.dumps({"error": "Ticket price cannot be negative"}, ensure_ascii=False)

        # Simulate creating event (in production, save to database)
        event_id = str(uuid.uuid4())

        result = {
            "event_id": event_id,
            "title": title,
            "description": description,
            "category": category,
            "date": date_str,
            "location": location,
            "organizer_name": organizer_name,
            "ticket_price": ticket_price if ticket_price else 0.0,
            "status": "created",
            "created_at": datetime.utcnow().isoformat()
        }
        return json.dumps(result, ensure_ascii=False)

    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON payload"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Internal error: {str(e)}"}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "cultural_event_creator",
    "description": "Create a cultural event entry (festival, exhibition, workshop, or performance) with title, description, category, date, and location, returning the unique event ID and a confirmation summary for use in scheduling and promotional workflows.",
    "category": "operations",
    "domain": "culture",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "title": {
            "type": "string",
            "description": "Official name of the cultural event, up to 200 characters."
        },
        "description": {
            "type": "string",
            "description": "Brief description of the event content, theme, and target audience, up to 1000 characters."
        },
        "category": {
            "type": "string",
            "description": "Type of cultural event.",
            "enum": [
                "festival",
                "exhibition",
                "workshop",
                "performance",
                "lecture",
                "other"
            ]
        },
        "date": {
            "type": "string",
            "description": "Event date in ISO 8601 format (YYYY-MM-DD) for the primary occurrence."
        },
        "location": {
            "type": "string",
            "description": "Physical venue or online platform name, e.g., 'Museum of Modern Art' or 'Zoom'."
        },
        "organizer_name": {
            "type": "string",
            "description": "Name of the organizing entity or person, up to 150 characters."
        },
        "ticket_price": {
            "type": "number",
            "description": "Optional: Admission fee in USD (0 for free events). Minimum 0.0.",
            "minimum": 0.0
        }
    },
    "required": [
        "title",
        "description",
        "category",
        "date",
        "location",
        "organizer_name"
    ]
},
}
