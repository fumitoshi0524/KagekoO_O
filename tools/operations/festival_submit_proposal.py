"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Submit a cultural festival proposal and return a confirmation with tracking ID."""
    import json
    import uuid
    from datetime import datetime

    try:
        data = json.loads(payload)
        # Required field validation
        required = ["event_title", "organizer_name", "organizer_email", "start_date", "end_date", "venue", "estimated_attendance", "budget_amount"]
        for field in required:
            if field not in data:
                return json.dumps({"error": f"Missing required field: {field}"}, ensure_ascii=False)

        event_title = data["event_title"]
        if len(event_title) > 120:
            return json.dumps({"error": "event_title must not exceed 120 characters"}, ensure_ascii=False)

        estimated_attendance = data["estimated_attendance"]
        if not isinstance(estimated_attendance, int) or estimated_attendance <= 0:
            return json.dumps({"error": "estimated_attendance must be a positive integer"}, ensure_ascii=False)

        budget = data["budget_amount"]
        if not isinstance(budget, (int, float)) or budget <= 0:
            return json.dumps({"error": "budget_amount must be a positive number"}, ensure_ascii=False)

        start = data["start_date"]
        end = data["end_date"]
        try:
            start_date = datetime.strptime(start, "%Y-%m-%d")
            end_date = datetime.strptime(end, "%Y-%m-%d")
            if end_date < start_date:
                return json.dumps({"error": "end_date must be on or after start_date"}, ensure_ascii=False)
        except ValueError:
            return json.dumps({"error": "Invalid date format. Use YYYY-MM-DD"}, ensure_ascii=False)

        # Generate tracking ID
        tracking_id = "FEST-" + uuid.uuid4().hex[:8].upper()
        submission_time = datetime.utcnow().isoformat()

        result = {
            "tracking_id": tracking_id,
            "status": "submitted",
            "submission_time": submission_time,
            "event_title": event_title,
            "organizer_name": data["organizer_name"],
            "organizer_email": data["organizer_email"],
            "start_date": start,
            "end_date": end,
            "venue": data["venue"],
            "estimated_attendance": estimated_attendance,
            "budget_amount": budget,
            "description": data.get("description", "")
        }
        return json.dumps(result, ensure_ascii=False)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON payload: {str(e)}"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Unexpected error: {str(e)}"}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "festival_submit_proposal",
    "description": "Submit a cultural festival proposal including event title, organizer details, date range, venue, estimated attendance, and budget; returns a proposal confirmation with a unique tracking ID and current status for workflow management.",
    "category": "operations",
    "domain": "culture",
    "risk_level": "write",
    "schema": {
    "type": "object",
    "properties": {
        "event_title": {
            "type": "string",
            "description": "Title of the cultural festival or event (max 120 characters)"
        },
        "organizer_name": {
            "type": "string",
            "description": "Full name of the primary organizer or contact person"
        },
        "organizer_email": {
            "type": "string",
            "description": "Email address of the organizer for correspondence"
        },
        "start_date": {
            "type": "string",
            "description": "Proposed start date of the festival in YYYY-MM-DD format"
        },
        "end_date": {
            "type": "string",
            "description": "Proposed end date of the festival in YYYY-MM-DD format"
        },
        "venue": {
            "type": "string",
            "description": "Name and location of the proposed venue for the event"
        },
        "estimated_attendance": {
            "type": "integer",
            "description": "Estimated number of attendees (must be a positive integer)"
        },
        "budget_amount": {
            "type": "number",
            "description": "Proposed total budget in local currency (e.g., USD) — must be greater than 0"
        },
        "description": {
            "type": "string",
            "description": "Optional: Brief description of the festival theme, activities, or cultural significance"
        }
    },
    "required": [
        "event_title",
        "organizer_name",
        "organizer_email",
        "start_date",
        "end_date",
        "venue",
        "estimated_attendance",
        "budget_amount"
    ]
},
}
