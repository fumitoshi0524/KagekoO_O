"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Manage and schedule cultural events, venues, and participants, returning a calendar of events, participant lists, and conflict alerts for double-booking or resource overlaps."""
    import json
    try:
        data = json.loads(payload)
        action = data.get('action', '')
        if not action or action not in ['schedule', 'cancel', 'list', 'check_conflicts']:
            return json.dumps({'error': 'Invalid action. Must be one of: schedule, cancel, list, check_conflicts'}, ensure_ascii=False)
        
        # Mock storage for events (in a real implementation this would be persistent)
        # Using a static variable pattern for demo purposes
        events = []
        
        if action == 'schedule':
            required = ['event_name', 'venue', 'date', 'time', 'duration_hours']
            missing = [r for r in required if r not in data]
            if missing:
                return json.dumps({'error': f'Missing required fields: {", ".join(missing)}'}, ensure_ascii=False)
            
            # Check for conflicts
            conflicts = []
            for ev in events:
                if ev['venue'] == data['venue'] and ev['date'] == data['date']:
                    # Check time overlap
                    ev_start = int(ev['time'].replace(':', ''))
                    new_start = int(data['time'].replace(':', ''))
                    ev_end = ev_start + int(ev['duration_hours'] * 100)
                    new_end = new_start + int(data['duration_hours'] * 100)
                    if not (new_end <= ev_start or new_start >= ev_end):
                        conflicts.append(ev['event_name'])
            
            if conflicts:
                return json.dumps({'status': 'conflict', 'conflicting_events': conflicts}, ensure_ascii=False)
            
            new_event = {
                'event_name': data['event_name'],
                'venue': data['venue'],
                'date': data['date'],
                'time': data['time'],
                'duration_hours': data['duration_hours'],
                'participants': data.get('participants', []),
                'event_type': data.get('event_type', 'general')
            }
            events.append(new_event)
            return json.dumps({'status': 'scheduled', 'event': new_event}, ensure_ascii=False)
        
        elif action == 'cancel':
            required = ['event_name', 'date', 'time']
            missing = [r for r in required if r not in data]
            if missing:
                return json.dumps({'error': f'Missing required fields: {", ".join(missing)}'}, ensure_ascii=False)
            
            removed = [ev for ev in events if not (ev['event_name'] == data['event_name'] and ev['date'] == data['date'] and ev['time'] == data['time'])]
            if len(removed) == len(events):
                return json.dumps({'status': 'not_found'}, ensure_ascii=False)
            
            return json.dumps({'status': 'cancelled', 'event_name': data['event_name'], 'date': data['date'], 'time': data['time']}, ensure_ascii=False)
        
        elif action == 'list':
            date_filter = data.get('date', None)
            venue_filter = data.get('venue', None)
            filtered = events
            if date_filter:
                filtered = [ev for ev in filtered if ev['date'] == date_filter]
            if venue_filter:
                filtered = [ev for ev in filtered if ev['venue'] == venue_filter]
            return json.dumps({'events': filtered, 'count': len(filtered)}, ensure_ascii=False)
        
        elif action == 'check_conflicts':
            required = ['venue', 'date', 'time', 'duration_hours']
            missing = [r for r in required if r not in data]
            if missing:
                return json.dumps({'error': f'Missing required fields: {", ".join(missing)}'}, ensure_ascii=False)
            
            conflicts = []
            for ev in events:
                if ev['venue'] == data['venue'] and ev['date'] == data['date']:
                    ev_start = int(ev['time'].replace(':', ''))
                    new_start = int(data['time'].replace(':', ''))
                    ev_end = ev_start + int(ev['duration_hours'] * 100)
                    new_end = new_start + int(data['duration_hours'] * 100)
                    if not (new_end <= ev_start or new_start >= ev_end):
                        conflicts.append({'event_name': ev['event_name'], 'time': ev['time'], 'duration': ev['duration_hours']})
            
            return json.dumps({'has_conflicts': len(conflicts) > 0, 'conflicts': conflicts}, ensure_ascii=False)
        
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "cultural_event_organizer",
    "description": "Manage and schedule cultural events, venues, and participants, returning a calendar of events, participant lists, and conflict alerts for double-booking or resource overlaps.",
    "category": "system",
    "domain": "culture",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": [
                "schedule",
                "cancel",
                "list",
                "check_conflicts"
            ],
            "description": "Operation to perform: schedule a new event, cancel an existing event, list events for a date/venue, or check for scheduling conflicts."
        },
        "event_name": {
            "type": "string",
            "description": "Name of the cultural event (e.g., exhibition, concert, workshop, festival)."
        },
        "venue": {
            "type": "string",
            "description": "Name of the venue or cultural space where the event takes place (e.g., museum hall, theater, gallery)."
        },
        "date": {
            "type": "string",
            "format": "date",
            "description": "Event date in YYYY-MM-DD format. Required for schedule, cancel, and list actions."
        },
        "time": {
            "type": "string",
            "pattern": "^([01]\\d|2[0-3]):([0-5]\\d)$",
            "description": "Start time in 24-hour HH:MM format. Required for schedule and cancel actions."
        },
        "duration_hours": {
            "type": "number",
            "minimum": 0.5,
            "maximum": 12,
            "description": "Duration of the event in hours (e.g., 1.5 for 90 minutes). Required for schedule action."
        },
        "participants": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "Optional: List of participant names or cultural organizations involved in the event."
        },
        "event_type": {
            "type": "string",
            "enum": [
                "exhibition",
                "concert",
                "workshop",
                "lecture",
                "festival",
                "performance"
            ],
            "description": "Optional: Category of the cultural event for filtering or display purposes."
        }
    },
    "required": [
        "action"
    ]
},
}
