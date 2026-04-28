"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Manage and retrieve cultural events."""
    import json
    try:
        data = json.loads(payload)
        action = data.get('action')
        if not action:
            return 'error: action is required'
        if action == 'add':
            name = data.get('name')
            category = data.get('category')
            date = data.get('date')
            venue = data.get('venue')
            if not all([name, category, date, venue]):
                return 'error: name, category, date, and venue are required for add action'
            # Simulate adding to a persistent store (in-memory list)
            if not hasattr(run, 'events'):
                run.events = []
            event = {'name': name, 'category': category, 'date': date, 'venue': venue}
            run.events.append(event)
            return json.dumps({'status': 'added', 'event': event}, ensure_ascii=False)
        elif action == 'list':
            if not hasattr(run, 'events'):
                run.events = []
            events = run.events
            # Apply filters
            category_filter = data.get('category')
            if category_filter:
                events = [e for e in events if e['category'] == category_filter]
            venue_filter = data.get('venue')
            if venue_filter:
                events = [e for e in events if venue_filter.lower() in e['venue'].lower()]
            start_date = data.get('start_date')
            end_date = data.get('end_date')
            if start_date:
                events = [e for e in events if e['date'] >= start_date]
            if end_date:
                events = [e for e in events if e['date'] <= end_date]
            # Also support single date filter
            date_filter = data.get('date')
            if date_filter:
                events = [e for e in events if e['date'] == date_filter]
            return json.dumps({'events': events}, ensure_ascii=False)
        else:
            return 'error: invalid action, must be add or list'
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "cultural_event_manager",
    "description": "Manage and retrieve cultural events (exhibitions, performances, festivals) from a local database, enabling users to add new events or query existing ones by date, category, or venue.",
    "category": "system",
    "domain": "culture",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "description": "Operation to perform: 'add' to create a new event, 'list' to retrieve events based on filters.",
            "enum": [
                "add",
                "list"
            ]
        },
        "name": {
            "type": "string",
            "description": "Name of the cultural event (required for 'add' action)."
        },
        "category": {
            "type": "string",
            "description": "Event category (e.g., art, music, theater, festival, literary, historical). Required for 'add' action.",
            "enum": [
                "art",
                "music",
                "theater",
                "festival",
                "literary",
                "historical"
            ]
        },
        "date": {
            "type": "string",
            "description": "Date of the event in YYYY-MM-DD format. Required for 'add' action. Optional for 'list' action: if provided, filter events on or after this date."
        },
        "venue": {
            "type": "string",
            "description": "Venue name or location (e.g., 'National Gallery', 'Concert Hall'). Required for 'add' action. Optional for 'list' action: if provided, filter by venue."
        },
        "start_date": {
            "type": "string",
            "description": "Optional: Start date for date range filter when listing events (YYYY-MM-DD format). Used only for 'list' action."
        },
        "end_date": {
            "type": "string",
            "description": "Optional: End date for date range filter when listing events (YYYY-MM-DD format). Used only for 'list' action."
        }
    },
    "required": [
        "action"
    ]
},
}
