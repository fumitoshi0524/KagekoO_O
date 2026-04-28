"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    from datetime import datetime, timedelta
    try:
        data = json.loads(payload)
        events = data.get('events')
        if not events:
            return json.dumps({'error': 'No events provided'})
        
        # Validate each event
        for evt in events:
            if 'date' not in evt or 'event_type' not in evt or 'description' not in evt:
                return json.dumps({'error': 'Each event must have date, event_type, description'})
            if evt['event_type'] not in ['diagnosis','procedure','lab_result','medication','appointment']:
                return json.dumps({'error': f"Invalid event_type: {evt['event_type']}"})
            # Validate date format
            try:
                datetime.strptime(evt['date'], '%Y-%m-%d')
            except ValueError:
                return json.dumps({'error': f"Invalid date format: {evt['date']}. Use YYYY-MM-DD."})
        
        # Sort events by date
        sorted_events = sorted(events, key=lambda x: x['date'])
        
        # Apply time range filter if specified
        time_range = data.get('time_range', 'all')
        if time_range != 'all':
            if time_range == 'last_6_months':
                cutoff = datetime.now() - timedelta(days=180)
                sorted_events = [e for e in sorted_events if datetime.strptime(e['date'], '%Y-%m-%d') >= cutoff]
            # could add other ranges, default all
        
        # Group events by month for timeline sections
        timeline_nodes = []
        for evt in sorted_events:
            node = {
                'date': evt['date'],
                'event_type': evt['event_type'],
                'description': evt['description'],
                'severity': evt.get('severity', 'low')
            }
            timeline_nodes.append(node)
        
        result = {
            'patient_id': data.get('patient_id', 'unknown'),
            'total_events': len(timeline_nodes),
            'timeline': timeline_nodes,
            'visualization_type': 'chronological_timeline'
        }
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({'error': str(e)})


TOOL_SPEC = {
    "name": "clinical_timeline_visualizer",
    "description": "Generate a chronological timeline visualization of a patient's medical events (diagnoses, procedures, lab results, medications, and appointments) from structured health records. Returns a JSON object with event nodes arranged by date, suitable for rendering as an interactive Gantt-like timeline.",
    "category": "visualization",
    "domain": "healthcare",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "events": {
            "type": "array",
            "description": "Array of medical events with date, type, and description.",
            "items": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "format": "date",
                        "description": "Date of the event in YYYY-MM-DD format."
                    },
                    "event_type": {
                        "type": "string",
                        "enum": [
                            "diagnosis",
                            "procedure",
                            "lab_result",
                            "medication",
                            "appointment"
                        ],
                        "description": "Category of the medical event."
                    },
                    "description": {
                        "type": "string",
                        "description": "Short textual description of the event (e.g., 'Type 2 diabetes diagnosed', 'HbA1c 7.2%')."
                    },
                    "severity": {
                        "type": "string",
                        "enum": [
                            "low",
                            "medium",
                            "high",
                            "critical"
                        ],
                        "description": "Optional: severity level for diagnoses or lab results."
                    }
                },
                "required": [
                    "date",
                    "event_type",
                    "description"
                ]
            }
        },
        "patient_id": {
            "type": "string",
            "description": "Optional: anonymized patient identifier to include in the visualization metadata."
        },
        "time_range": {
            "type": "string",
            "description": "Optional: filter events to a specific range, e.g., 'last_6_months' or 'all'. Defaults to 'all'."
        }
    },
    "required": [
        "events"
    ]
},
}
