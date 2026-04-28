"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        itinerary = data.get('itinerary', [])
        if not itinerary:
            return 'error: itinerary array is required and must contain at least one activity'
        
        # Validate activity structure
        required_fields = ['day', 'start_time', 'end_time', 'activity_name', 'activity_type']
        for i, activity in enumerate(itinerary):
            for field in required_fields:
                if field not in activity or activity[field] is None:
                    return f'error: activity at index {i} is missing required field "{field}"'
            # Validate time format
            for tf in ['start_time', 'end_time']:
                parts = activity[tf].split(':')
                if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
                    return f'error: invalid time format in activity at index {i}: "{activity[tf]}" (expected HH:MM)'
                h, m = int(parts[0]), int(parts[1])
                if h < 0 or h > 23 or m < 0 or m > 59:
                    return f'error: invalid time value in activity at index {i}: "{activity[tf]}"'
            # Validate activity_type enum
            valid_types = ['sightseeing', 'dining', 'transportation', 'accommodation', 'leisure', 'shopping', 'other']
            if activity['activity_type'] not in valid_types:
                return f'error: invalid activity_type "{activity["activity_type"]}" at index {i}. Must be one of {valid_types}'
        
        trip_title = data.get('trip_title', 'Travel Itinerary')
        timezone = data.get('timezone', 'UTC')
        
        # Compute day range
        days = sorted(set(a['day'] for a in itinerary))
        
        # Process activities by day, compute columns/lanes for scheduling
        day_columns = {}
        for day in days:
            day_activities = [a for a in itinerary if a['day'] == day]
            # Sort by start_time then end_time
            day_activities.sort(key=lambda x: (x['start_time'], x['end_time']))
            # Simple lane assignment: place in first lane that doesn't overlap
            lanes = []
            for act in day_activities:
                s_h, s_m = map(int, act['start_time'].split(':'))
                e_h, e_m = map(int, act['end_time'].split(':'))
                start_mins = s_h * 60 + s_m
                end_mins = e_h * 60 + e_m
                placed = False
                for lane_idx, lane in enumerate(lanes):
                    # Check overlap with all activities in this lane
                    overlaps = False
                    for existing in lane:
                        es_h, es_m = map(int, existing['start_time'].split(':'))
                        ee_h, ee_m = map(int, existing['end_time'].split(':'))
                        ex_start = es_h * 60 + es_m
                        ex_end = ee_h * 60 + ee_m
                        if not (end_mins <= ex_start or start_mins >= ex_end):
                            overlaps = True
                            break
                    if not overlaps:
                        lane.append(act)
                        placed = True
                        break
                if not placed:
                    lanes.append([act])
            day_columns[day] = lanes
        
        # Build chart data structure
        chart = {
            'type': 'gantt',
            'title': trip_title,
            'timezone': timezone,
            'days': {}
        }
        for day in days:
            day_label = f'Day {day}'
            lanes_data = []
            for lane_idx, lane in enumerate(day_columns[day]):
                activities = []
                for act in lane:
                    activity_entry = {
                        'activity_name': act['activity_name'],
                        'start_time': act['start_time'],
                        'end_time': act['end_time'],
                        'activity_type': act['activity_type'],
                        'duration_minutes': (int(act['end_time'].split(':')[0]) * 60 + int(act['end_time'].split(':')[1])) - (int(act['start_time'].split(':')[0]) * 60 + int(act['start_time'].split(':')[1]))
                    }
                    if 'location' in act:
                        activity_entry['location'] = act['location']
                    if 'notes' in act:
                        activity_entry['notes'] = act['notes']
                    activities.append(activity_entry)
                lanes_data.append({'lane': lane_idx + 1, 'activities': activities})
            chart['days'][day_label] = {'lanes': lanes_data}
        
        # Summary statistics
        total_activities = len(itinerary)
        type_counts = {}
        for act in itinerary:
            atype = act['activity_type']
            type_counts[atype] = type_counts.get(atype, 0) + 1
        summary = {
            'total_days': len(days),
            'total_activities': total_activities,
            'activity_type_breakdown': type_counts
        }
        result = {
            'chart': chart,
            'summary': summary
        }
        return json.dumps(result, ensure_ascii=False)
    except json.JSONDecodeError:
        return 'error: invalid JSON payload'
    except Exception as e:
        return f'error: {str(e)}'


TOOL_SPEC = {
    "name": "travel_itinerary_chart",
    "description": "Generate a Gantt-style chart visualizing a travel itinerary by days, showing activity blocks with location, type, and duration for trip planning and schedule optimization.",
    "category": "visualization",
    "domain": "travel",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "itinerary": {
            "type": "array",
            "description": "Array of activity objects representing each planned event in the trip, ordered chronologically.",
            "items": {
                "type": "object",
                "properties": {
                    "day": {
                        "type": "integer",
                        "description": "Day number in the itinerary (1-based, e.g. 1 = first day of trip).",
                        "minimum": 1
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Start time of activity in 24-hour format (HH:MM)."
                    },
                    "end_time": {
                        "type": "string",
                        "description": "End time of activity in 24-hour format (HH:MM). Must be after start_time."
                    },
                    "activity_name": {
                        "type": "string",
                        "description": "Short descriptive name of the activity (e.g. 'Eiffel Tower visit', 'Lunch at Le Bistro')."
                    },
                    "location": {
                        "type": "string",
                        "description": "Optional: Name or address of the location for this activity."
                    },
                    "activity_type": {
                        "type": "string",
                        "description": "Category of activity for color-coding: sightseeing, dining, transportation, accommodation, leisure, shopping, or other.",
                        "enum": [
                            "sightseeing",
                            "dining",
                            "transportation",
                            "accommodation",
                            "leisure",
                            "shopping",
                            "other"
                        ]
                    },
                    "notes": {
                        "type": "string",
                        "description": "Optional: Additional notes or details about the activity (e.g. booking reference, contact info)."
                    }
                },
                "required": [
                    "day",
                    "start_time",
                    "end_time",
                    "activity_name",
                    "activity_type"
                ]
            },
            "minItems": 1
        },
        "trip_title": {
            "type": "string",
            "description": "Optional: Title for the itinerary chart (e.g. 'Summer Trip to Paris'). If omitted, defaults to 'Travel Itinerary'.",
            "maxLength": 100
        },
        "timezone": {
            "type": "string",
            "description": "Optional: IANA timezone identifier for the trip location (e.g. 'Europe/Paris'). Used for accurate time display. Defaults to UTC.",
            "pattern": "^[A-Za-z_]+/[A-Za-z_]+$"
        }
    },
    "required": [
        "itinerary"
    ]
},
}
