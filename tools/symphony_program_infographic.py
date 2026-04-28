"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    from collections import Counter, OrderedDict

    try:
        data = json.loads(payload)
    except json.JSONDecodeError as e:
        return f'error: invalid JSON - {e}'

    if 'program_items' not in data:
        return 'error: required field "program_items" missing'

    items = data['program_items']
    if not isinstance(items, list) or len(items) == 0:
        return 'error: program_items must be a non-empty list'

    # Validate each item
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            return f'error: item at index {idx} must be an object'
        for field in ['composer', 'title', 'duration_minutes']:
            if field not in item:
                return f'error: item at index {idx} missing required field "{field}"'
        if not isinstance(item.get('duration_minutes'), (int, float)):
            return f'error: item at index {idx} duration_minutes must be a number'

    total_minutes = sum(item['duration_minutes'] for item in items)
    composer_counts = Counter(item['composer'].strip() for item in items)
    unique_composers = list(composer_counts.keys())
    composer_diversity_score = round(len(unique_composers) / len(items), 2) if items else 0

    # Build timeline segments for visualization
    timeline = []
    current_start = 0
    for item in items:
        timeline.append(OrderedDict([
            ('composer', item['composer']),
            ('title', item['title']),
            ('start_min', current_start),
            ('end_min', round(current_start + item['duration_minutes'], 2)),
            ('duration_min', item['duration_minutes']),
            ('instrumentation', item.get('instrumentation', 'not specified'))
        ]))
        current_start += item['duration_minutes']

    result = OrderedDict([
        ('concert_title', data.get('concert_title', 'Untitled Concert')),
        ('venue', data.get('venue', 'Unknown Venue')),
        ('date', data.get('date', 'Unknown Date')),
        ('total_duration_min', round(total_minutes, 2)),
        ('total_duration_readable', f"{int(total_minutes // 60)}h {int(total_minutes % 60)}m"),
        ('number_of_pieces', len(items)),
        ('unique_composers', unique_composers),
        ('composer_diversity_score', composer_diversity_score),
        ('most_performed_composer', max(composer_counts, key=composer_counts.get)),
        ('timeline_segments', timeline),
        ('visual_type', 'horizontal_timeline_bar')
    ])

    return json.dumps(result, ensure_ascii=False, indent=2)


TOOL_SPEC = {
    "name": "symphony_program_infographic",
    "description": "Generate a structured infographic summary from a symphony or concert program, including movement names, durations, composers, and instrumentation, returning a JSON structure ready for display or chart rendering.",
    "category": "visualization",
    "domain": "culture",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "program_items": {
            "type": "array",
            "description": "List of pieces or movements performed in the concert.",
            "items": {
                "type": "object",
                "properties": {
                    "composer": {
                        "type": "string",
                        "description": "Full name of the composer."
                    },
                    "title": {
                        "type": "string",
                        "description": "Title of the piece or movement."
                    },
                    "duration_minutes": {
                        "type": "number",
                        "description": "Duration of the piece in minutes."
                    },
                    "instrumentation": {
                        "type": "string",
                        "description": "Optional: Instruments or ensemble used (e.g. violin solo, full orchestra, string quartet)."
                    }
                },
                "required": [
                    "composer",
                    "title",
                    "duration_minutes"
                ]
            }
        },
        "concert_title": {
            "type": "string",
            "description": "Optional: Name of the concert or series event."
        },
        "venue": {
            "type": "string",
            "description": "Optional: Name of the performance venue."
        },
        "date": {
            "type": "string",
            "description": "Optional: Date of the performance in YYYY-MM-DD format."
        }
    },
    "required": [
        "program_items"
    ]
},
}
