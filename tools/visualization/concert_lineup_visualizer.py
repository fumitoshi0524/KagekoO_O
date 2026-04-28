"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        festival_name = data.get('festival_name')
        stages = data.get('stages', [])
        performances = data.get('performances', [])
        day = data.get('day', '')
        output_format = data.get('output_format', 'json')

        if not festival_name:
            return 'error: festival_name is required'
        if not stages or not isinstance(stages, list):
            return 'error: stages must be a non-empty list'
        if not performances or not isinstance(performances, list):
            return 'error: performances must be a non-empty list'

        # Validate stage references
        stage_set = set(stages)
        for perf in performances:
            if perf.get('stage') not in stage_set:
                return f'error: performance stage "{perf.get("stage")}" not in stages list'

        # Sort performances by start time
        def parse_time(t):
            parts = t.split(':')
            return int(parts[0]) * 60 + int(parts[1])
        performances.sort(key=lambda x: parse_time(x['start_time']))

        # Build time slots (e.g., every 15 minutes) from min to max time
        all_times = [parse_time(p['start_time']) for p in performances]
        all_ends = [parse_time(p['start_time']) + p['duration_minutes'] for p in performances]
        min_time = min(all_times) // 15 * 15
        max_time = max(all_ends)
        if max_time % 15 != 0:
            max_time = (max_time // 15 + 1) * 15
        time_slots = list(range(min_time, max_time + 1, 15))

        def fmt_time(minutes):
            h = minutes // 60
            m = minutes % 60
            return f'{h:02d}:{m:02d}'

        # Generate SVG chart
        svg_parts = []
        width = 1200
        stage_colors = {stage: f'hsl({i * 360 // len(stages)}, 60%, 70%)' for i, stage in enumerate(stages)}
        row_height = 50
        header_height = 60
        timeline_width = 80
        cell_width = (width - timeline_width) // len(time_slots) if time_slots else 100
        total_height = header_height + len(stages) * row_height + 40

        svg_parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{total_height}" viewBox="0 0 {width} {total_height}">')
        svg_parts.append(f'<rect width="100%" height="100%" fill="#f8f9fa"/>')
        svg_parts.append(f'<text x="{width/2}" y="30" text-anchor="middle" font-size="24" font-weight="bold" fill="#333">{festival_name}</text>')
        if day:
            svg_parts.append(f'<text x="{width/2}" y="50" text-anchor="middle" font-size="14" fill="#666">{day}</text>')

        # Draw timeline header
        for i, t in enumerate(time_slots):
            x = timeline_width + i * cell_width
            time_str = fmt_time(t)
            svg_parts.append(f'<text x="{x + cell_width/2}" y="{header_height - 10}" text-anchor="middle" font-size="11" fill="#555">{time_str}</text>')

        # Draw rows for each stage
        for stage_idx, stage in enumerate(stages):
            y = header_height + stage_idx * row_height
            svg_parts.append(f'<text x="10" y="{y + row_height/2 + 4}" font-size="14" fill="#333">{stage}</text>')
            svg_parts.append(f'<line x1="{timeline_width}" y1="{y + row_height}" x2="{width}" y2="{y + row_height}" stroke="#ddd" stroke-width="1"/>')

        # Place performance blocks
        for perf in performances:
            artist = perf['artist']
            stage = perf['stage']
            start = parse_time(perf['start_time'])
            duration = perf['duration_minutes']
            end = start + duration
            stage_idx = stages.index(stage)
            y = header_height + stage_idx * row_height

            # Find start slot index
            start_slot = 0
            while start_slot < len(time_slots) - 1 and time_slots[start_slot] <= start:
                start_slot += 1
            start_slot -= 1
            if start_slot < 0:
                start_slot = 0

            # Find end slot index
            end_slot = start_slot
            while end_slot < len(time_slots) and time_slots[end_slot] < end:
                end_slot += 1

            # Calculate x and width
            x = timeline_width + start_slot * cell_width
            width_block = (end_slot - start_slot) * cell_width
            if width_block < 10:
                width_block = 10

            color = stage_colors.get(stage, '#ccc')
            svg_parts.append(f'<rect x="{x}" y="{y + 5}" width="{width_block}" height="{row_height - 10}" fill="{color}" rx="4" stroke="#fff" stroke-width="1"/>')
            # Artist name truncation
            artist_display = artist if len(artist) * 7 < width_block else artist[:int(width_block/7)-2] + '..'
            svg_parts.append(f'<text x="{x + 5}" y="{y + row_height/2 + 4}" font-size="12" fill="#000" font-weight="bold">{artist_display}</text>')
            # Time range
            time_range = f'{perf["start_time"]}-{fmt_time(end)}'
            svg_parts.append(f'<text x="{x + 5}" y="{y + row_height/2 + 16}" font-size="10" fill="#333">{time_range}</text>')

        svg_parts.append('</svg>')
        svg_content = '\n'.join(svg_parts)

        if output_format == 'svg':
            result = {'type': 'svg', 'content': svg_content}
        elif output_format == 'html':
            html = f'<!DOCTYPE html><html><head><title>{festival_name} Lineup</title></head><body>{svg_content}</body></html>'
            result = {'type': 'html', 'content': html}
        else:
            # JSON structured data
            perf_list = []
            for perf in performances:
                end = parse_time(perf['start_time']) + perf['duration_minutes']
                perf_list.append({
                    'artist': perf['artist'],
                    'stage': perf['stage'],
                    'start_time': perf['start_time'],
                    'end_time': fmt_time(end),
                    'duration_minutes': perf['duration_minutes'],
                    'genre': perf.get('genre', 'Unknown')
                })
            result = {
                'type': 'json',
                'festival': festival_name,
                'day': day,
                'stages': stages,
                'performances': perf_list
            }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "concert_lineup_visualizer",
    "description": "Generate an interactive timeline visualization of a music festival concert lineup, displaying artist names, stage assignments, performance times, and set durations as a color-coded schedule chart that can be exported as an image or embedded in a webpage.",
    "category": "visualization",
    "domain": "entertainment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "festival_name": {
            "type": "string",
            "description": "Name of the music festival or event for the lineup chart title"
        },
        "stages": {
            "type": "array",
            "description": "List of stage names where artists perform",
            "items": {
                "type": "string"
            }
        },
        "performances": {
            "type": "array",
            "description": "List of performance entries with artist, stage, start time, and duration",
            "items": {
                "type": "object",
                "properties": {
                    "artist": {
                        "type": "string",
                        "description": "Name of the performing artist or band"
                    },
                    "stage": {
                        "type": "string",
                        "description": "Name of the stage (must match one from stages list)"
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Start time in 24-hour format HH:MM"
                    },
                    "duration_minutes": {
                        "type": "integer",
                        "description": "Duration of the performance in minutes"
                    },
                    "genre": {
                        "type": "string",
                        "description": "Optional: Genre of the artist for color coding"
                    }
                },
                "required": [
                    "artist",
                    "stage",
                    "start_time",
                    "duration_minutes"
                ]
            }
        },
        "day": {
            "type": "string",
            "description": "Optional: Specific day date for the schedule (e.g., '2025-07-15')"
        },
        "output_format": {
            "type": "string",
            "description": "Optional: Desired output format",
            "enum": [
                "json",
                "html",
                "svg"
            ],
            "default": "json"
        }
    },
    "required": [
        "festival_name",
        "stages",
        "performances"
    ]
},
}
