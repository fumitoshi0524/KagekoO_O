"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    from datetime import datetime, date

    try:
        data = json.loads(payload)
        action = data.get("action")
        if action not in ["add_event", "remove_event", "list_events", "clear_all"]:
            return json.dumps({"error": "Invalid action. Must be one of: add_event, remove_event, list_events, clear_all"}, ensure_ascii=False)

        # In-memory store for demonstration (in production, this would be a database)
        if not hasattr(run, "events_storage"):
            run.events_storage = []

        if action == "add_event":
            event_name = data.get("event_name")
            event_date_str = data.get("event_date")
            category = data.get("category")
            venue = data.get("venue")
            if not event_name or not event_date_str:
                return json.dumps({"error": "event_name and event_date are required for add_event"}, ensure_ascii=False)
            try:
                event_date = datetime.strptime(event_date_str, "%Y-%m-%d").date()
            except ValueError:
                return json.dumps({"error": "event_date must be in YYYY-MM-DD format"}, ensure_ascii=False)
            if event_date < date.today():
                return json.dumps({"error": "event_date must be today or in the future"}, ensure_ascii=False)
            # Avoid duplicate event names on same date (simple validation)
            for ev in run.events_storage:
                if ev["event_name"] == event_name and ev["event_date"] == event_date_str:
                    return json.dumps({"error": f"Event '{event_name}' already exists on {event_date_str}"}, ensure_ascii=False)
            new_event = {"event_name": event_name, "event_date": event_date_str}
            if category:
                new_event["category"] = category
            if venue:
                new_event["venue"] = venue
            run.events_storage.append(new_event)
            return json.dumps({"status": "success", "message": f"Added event '{event_name}' on {event_date_str}", "events_count": len(run.events_storage)}, ensure_ascii=False)

        elif action == "remove_event":
            event_name = data.get("event_name")
            if not event_name:
                return json.dumps({"error": "event_name is required for remove_event"}, ensure_ascii=False)
            initial_count = len(run.events_storage)
            run.events_storage = [ev for ev in run.events_storage if ev["event_name"] != event_name]
            removed_count = initial_count - len(run.events_storage)
            if removed_count == 0:
                return json.dumps({"status": "not_found", "message": f"No event named '{event_name}' found"}, ensure_ascii=False)
            return json.dumps({"status": "success", "message": f"Removed {removed_count} event(s) named '{event_name}'", "events_count": len(run.events_storage)}, ensure_ascii=False)

        elif action == "list_events":
            # Apply filters
            filtered = run.events_storage.copy()
            # Date range filter
            start_date_str = data.get("event_date")
            end_date_str = data.get("end_date")
            if start_date_str:
                try:
                    start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                except ValueError:
                    return json.dumps({"error": "event_date must be in YYYY-MM-DD format"}, ensure_ascii=False)
                if end_date_str:
                    try:
                        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                    except ValueError:
                        return json.dumps({"error": "end_date must be in YYYY-MM-DD format"}, ensure_ascii=False)
                    filtered = [ev for ev in filtered if start_date <= datetime.strptime(ev["event_date"], "%Y-%m-%d").date() <= end_date]
                else:
                    filtered = [ev for ev in filtered if datetime.strptime(ev["event_date"], "%Y-%m-%d").date() >= start_date]
            # Category filter
            category_filter = data.get("category")
            if category_filter:
                filtered = [ev for ev in filtered if ev.get("category") == category_filter]
            # Venue filter
            venue_filter = data.get("venue")
            if venue_filter:
                filtered = [ev for ev in filtered if ev.get("venue") == venue_filter]
            # Sort by date ascending
            filtered.sort(key=lambda x: x["event_date"])
            return json.dumps({"status": "success", "events": filtered, "count": len(filtered)}, ensure_ascii=False)

        elif action == "clear_all":
            count = len(run.events_storage)
            run.events_storage = []
            return json.dumps({"status": "success", "message": f"Cleared {count} events", "events_count": 0}, ensure_ascii=False)

        else:
            return json.dumps({"error": "Unhandled action"}, ensure_ascii=False)

    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "cultural_event_calendar_manager",
    "description": "Manage and query a calendar of cultural events (exhibitions, festivals, performances) across multiple venues, returning a list of events filtered by date range, category, or venue, useful for scheduling and resource allocation.",
    "category": "system",
    "domain": "culture",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "description": "Operation to perform: add_event, remove_event, list_events, or clear_all",
            "enum": [
                "add_event",
                "remove_event",
                "list_events",
                "clear_all"
            ]
        },
        "event_name": {
            "type": "string",
            "description": "Name of the cultural event (required for add_event and remove_event, ignored otherwise)"
        },
        "event_date": {
            "type": "string",
            "description": "Date of the event in YYYY-MM-DD format (required for add_event, optional for list_events as filter start)"
        },
        "category": {
            "type": "string",
            "description": "Optional: Type of cultural event: exhibition, festival, performance, talk, workshop (can be used for list_events filter)",
            "enum": [
                "exhibition",
                "festival",
                "performance",
                "talk",
                "workshop"
            ]
        },
        "venue": {
            "type": "string",
            "description": "Optional: Venue name (can be used for list_events filter or add_event context)"
        },
        "end_date": {
            "type": "string",
            "description": "Optional: End date for date range filter when listing events, format YYYY-MM-DD"
        }
    },
    "required": [
        "action"
    ]
},
}
