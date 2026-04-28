"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        festival = data.get('festival_name')
        lineup = data.get('lineup')
        if not festival or not lineup:
            return 'error: festival_name and lineup are required'
        # Sort lineup by start_time then stage
        sorted_lineup = sorted(lineup, key=lambda x: (x['start_time'], x['stage']))
        # Validate time format and sequence
        for slot in sorted_lineup:
            if ':' not in slot['start_time'] or ':' not in slot['end_time']:
                return 'error: Invalid time format, use HH:MM'
            start_h, start_m = map(int, slot['start_time'].split(':'))
            end_h, end_m = map(int, slot['end_time'].split(':'))
            if (end_h * 60 + end_m) <= (start_h * 60 + start_m):
                return f"error: End time {slot['end_time']} must be after start time {slot['start_time']} for {slot['artist']}"
        # Generate timeline grid (stages as columns, time slots as rows)
        time_slots = []
        for slot in sorted_lineup:
            time_slots.append({
                'artist': slot['artist'],
                'stage': slot['stage'],
                'start': slot['start_time'],
                'end': slot['end_time'],
                'genre': slot.get('genre', 'unknown'),
                'duration_minutes': (int(slot['end_time'].split(':')[0])*60 + int(slot['end_time'].split(':')[1])) - (int(slot['start_time'].split(':')[0])*60 + int(slot['start_time'].split(':')[1]))
            })
        # Group by stage for per-stage scheduling
        stages = {}
        for slot in time_slots:
            stage = slot['stage']
            if stage not in stages:
                stages[stage] = []
            stages[stage].append(slot)
        result = {
            'festival': festival,
            'day': data.get('day', 'Full Festival'),
            'total_artists': len(time_slots),
            'stages': list(stages.keys()),
            'timeline': time_slots,
            'stage_schedule': stages
        }
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "music_festival_lineup_visualizer",
    "description": "Generate a visual schedule or timeline for a music festival lineup, showing artist names, stage assignments, set times, and genre tags in a structured JSON output that can be rendered as a chart or calendar.",
    "category": "visualization",
    "domain": "entertainment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "festival_name": {
            "type": "string",
            "description": "Name of the music festival (e.g., Coachella, Lollapalooza).",
            "examples": [
                "Glastonbury 2025"
            ]
        },
        "lineup": {
            "type": "array",
            "description": "List of artist performance slots with stage, start time, end time, and genre.",
            "items": {
                "type": "object",
                "properties": {
                    "artist": {
                        "type": "string",
                        "description": "Name of the performing artist or band."
                    },
                    "stage": {
                        "type": "string",
                        "description": "Stage or venue area name where the artist performs."
                    },
                    "start_time": {
                        "type": "string",
                        "format": "HH:MM",
                        "description": "Performance start time in 24-hour format (e.g., 14:00)."
                    },
                    "end_time": {
                        "type": "string",
                        "format": "HH:MM",
                        "description": "Performance end time in 24-hour format (e.g., 15:30)."
                    },
                    "genre": {
                        "type": "string",
                        "description": "Primary music genre (e.g., rock, pop, electronic, hip-hop)."
                    }
                },
                "required": [
                    "artist",
                    "stage",
                    "start_time",
                    "end_time"
                ]
            }
        },
        "day": {
            "type": "string",
            "description": "Optional: Specific day of the festival (e.g., Friday, Saturday, or a date). If omitted, show full weekend.",
            "examples": [
                "Saturday"
            ]
        }
    },
    "required": [
        "festival_name",
        "lineup"
    ]
},
}
