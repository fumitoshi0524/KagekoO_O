"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    from datetime import datetime, timedelta
    import uuid
    try:
        data = json.loads(payload)
        required = ['event_name', 'event_type', 'institution', 'date_time']
        for key in required:
            if key not in data:
                return json.dumps({'error': f'Missing required field: {key}'})
        event_name = data['event_name']
        event_type = data['event_type']
        institution = data['institution']
        date_time_str = data['date_time']
        reminder_days = data.get('reminder_days_before', 1)
        if not isinstance(reminder_days, int) or reminder_days < 0 or reminder_days > 30:
            return json.dumps({'error': 'reminder_days_before must be integer between 0 and 30'})
        recurring = data.get('recurring', False)
        try:
            event_datetime = datetime.fromisoformat(date_time_str)
        except ValueError:
            return json.dumps({'error': 'Invalid date_time format. Use ISO 8601 YYYY-MM-DDTHH:MM:SS'})
        valid_types = ['exhibition', 'festival', 'lecture', 'workshop', 'performance']
        if event_type not in valid_types:
            return json.dumps({'error': f'Invalid event_type. Must be one of {valid_types}'})
        reminder_datetime = event_datetime - timedelta(days=reminder_days)
        if reminder_datetime < datetime.now():
            return json.dumps({'error': 'Reminder time is in the past. Choose a future event or fewer reminder days.'})
        reminder_id = str(uuid.uuid4())
        result = {
            'status': 'success',
            'reminder_id': reminder_id,
            'event_name': event_name,
            'event_type': event_type,
            'institution': institution,
            'event_datetime': date_time_str,
            'reminder_datetime': reminder_datetime.isoformat(),
            'reminder_days_before': reminder_days,
            'recurring': recurring,
            'message': f'Reminder scheduled for {event_name} at {institution}. Your reminder will be sent on {reminder_datetime.strftime("%Y-%m-%d %H:%M:%S")}.'
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)})


TOOL_SPEC = {
    "name": "cultural_heritage_event_reminder",
    "description": "Schedule and manage reminders for cultural heritage events (exhibitions, festivals, lectures) associated with artists, historians, or cultural institutions, returning a confirmation with event details and a unique reminder ID.",
    "category": "system",
    "domain": "culture",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "event_name": {
            "type": "string",
            "description": "Name of the cultural heritage event (e.g., 'Klimt Exhibition', 'History of Calligraphy Lecture')"
        },
        "event_type": {
            "type": "string",
            "description": "Type of event",
            "enum": [
                "exhibition",
                "festival",
                "lecture",
                "workshop",
                "performance"
            ]
        },
        "institution": {
            "type": "string",
            "description": "Name of the organizing cultural institution (e.g., 'Louvre Museum', 'Smithsonian')"
        },
        "date_time": {
            "type": "string",
            "description": "Date and time of the event in ISO 8601 format (YYYY-MM-DDTHH:MM:SS)"
        },
        "reminder_days_before": {
            "type": "integer",
            "description": "Optional: Number of days before the event to trigger reminder (default 1). Must be between 0 and 30.",
            "minimum": 0,
            "maximum": 30
        },
        "recurring": {
            "type": "boolean",
            "description": "Optional: Whether the event repeats weekly (default false)"
        }
    },
    "required": [
        "event_name",
        "event_type",
        "institution",
        "date_time"
    ]
},
}
