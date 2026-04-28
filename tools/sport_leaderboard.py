"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        event_name = data.get('event_name')
        participants = data.get('participants', [])
        sort_order = data.get('sort_order', 'descending')
        if not event_name or not participants:
            return json.dumps({'error': 'Missing required fields: event_name and participants'}, ensure_ascii=False)
        # Assign ranks based on sort order
        reverse = sort_order == 'descending'
        sorted_parts = sorted(participants, key=lambda x: x['metric_value'], reverse=reverse)
        rank = 1
        leaderboard = []
        for i, p in enumerate(sorted_parts):
            if i > 0 and p['metric_value'] != sorted_parts[i-1]['metric_value']:
                rank = i + 1
            entry = {
                'rank': rank,
                'name': p['name'],
                'metric_value': p['metric_value'],
                'metric_unit': p.get('metric_unit', '')
            }
            leaderboard.append(entry)
        result = {
            'event': event_name,
            'leaderboard': leaderboard,
            'total_participants': len(participants)
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "sport_leaderboard",
    "description": "Generate a leaderboard visualization for sports events, ranking participants by performance metrics such as points, time, or score, and returning a structured list sorted by rank.",
    "category": "visualization",
    "domain": "sports",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "event_name": {
            "type": "string",
            "description": "Name of the sports event (e.g., 'Marathon', 'Swimming Championship')."
        },
        "participants": {
            "type": "array",
            "description": "List of participants with their performance metrics. Each participant is an object with fields: name (string), metric_value (number), and optionally metric_unit (string).",
            "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Participant name."
                    },
                    "metric_value": {
                        "type": "number",
                        "description": "Performance value (e.g., points, seconds, meters)."
                    },
                    "metric_unit": {
                        "type": "string",
                        "description": "Optional: Unit of the metric (e.g., 'points', 'seconds', 'meters')."
                    }
                },
                "required": [
                    "name",
                    "metric_value"
                ]
            }
        },
        "sort_order": {
            "type": "string",
            "description": "Optional: Sorting direction for ranking. 'descending' (higher metric_value is better, e.g., points) or 'ascending' (lower metric_value is better, e.g., race time). Default is 'descending'.",
            "enum": [
                "descending",
                "ascending"
            ],
            "default": "descending"
        }
    },
    "required": [
        "event_name",
        "participants"
    ]
},
}
