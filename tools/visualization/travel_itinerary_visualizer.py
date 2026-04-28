"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    from datetime import datetime, timedelta
    try:
        data = json.loads(payload)
        items = data.get('itinerary_items', [])
        if not items:
            return json.dumps({'error': 'No itinerary items provided.'}, ensure_ascii=False)
        timezone_str = data.get('timezone', 'UTC')
        group_by_date = data.get('group_by_date', True)
        # Build visual timeline data
        color_map = {
            'activity': '#4CAF50',
            'transport': '#2196F3',
            'accommodation': '#FF9800',
            'meal': '#9C27B0',
            'other': '#607D8B'
        }
        parsed_items = []
        for item in items:
            start = datetime.fromisoformat(item['start_time'])
            end = datetime.fromisoformat(item['end_time'])
            duration_minutes = (end - start).total_seconds() / 60
            parsed_items.append({
                'name': item['name'],
                'start': item['start_time'],
                'end': item['end_time'],
                'category': item['category'],
                'location': item.get('location', ''),
                'duration_minutes': duration_minutes,
                'color': color_map.get(item['category'], '#607D8B')
            })
        # Sort by start time
        parsed_items.sort(key=lambda x: x['start'])
        # Group by date if requested
        if group_by_date:
            groups = {}
            for item in parsed_items:
                date_key = item['start'][:10]
                if date_key not in groups:
                    groups[date_key] = []
                groups[date_key].append(item)
            result = {
                'timezone': timezone_str,
                'total_items': len(parsed_items),
                'total_duration_minutes': sum(it['duration_minutes'] for it in parsed_items),
                'groups': [{'date': d, 'items': groups[d]} for d in sorted(groups.keys())]
            }
        else:
            result = {
                'timezone': timezone_str,
                'total_items': len(parsed_items),
                'total_duration_minutes': sum(it['duration_minutes'] for it in parsed_items),
                'items': parsed_items
            }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "travel_itinerary_visualizer",
    "description": "Generate a visual timeline chart from a list of travel itinerary items (activities, transport, accommodations) with durations, locations, and color-coded categories, returning JSON that can be rendered by a charting library.",
    "category": "visualization",
    "domain": "travel",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "itinerary_items": {
            "type": "array",
            "description": "List of itinerary entries, each with name, start_time, end_time, category, and optional location.",
            "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the activity, transport leg, or accommodation."
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Start datetime in ISO 8601 format (e.g., 2025-06-10T09:00:00)."
                    },
                    "end_time": {
                        "type": "string",
                        "description": "End datetime in ISO 8601 format."
                    },
                    "category": {
                        "type": "string",
                        "enum": [
                            "activity",
                            "transport",
                            "accommodation",
                            "meal",
                            "other"
                        ],
                        "description": "Category of the itinerary item."
                    },
                    "location": {
                        "type": "string",
                        "description": "Optional: Location name or address."
                    }
                },
                "required": [
                    "name",
                    "start_time",
                    "end_time",
                    "category"
                ]
            }
        },
        "timezone": {
            "type": "string",
            "description": "Optional: IANA timezone string (e.g., 'America/New_York') for rendering. Defaults to UTC."
        },
        "group_by_date": {
            "type": "boolean",
            "description": "Optional: Whether to group items by date in the output. Default True."
        }
    },
    "required": [
        "itinerary_items"
    ]
},
}
