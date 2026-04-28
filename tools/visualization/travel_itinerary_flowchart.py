"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a visual flowchart representation of a multi-destination travel itinerary."""
    import json
    try:
        data = json.loads(payload)
        destinations = data.get('destinations')
        if not destinations:
            return json.dumps({'error': 'At least one destination is required'}, ensure_ascii=False)
        
        activities = data.get('activities', [])
        transport = data.get('transport', [])
        accommodation = data.get('accommodation', [])
        style = data.get('style', 'ascii_art')
        
        # Build a timeline of events grouped by date
        events_by_date = {}
        for dest in destinations:
            from datetime import datetime
            arr = datetime.strptime(dest['arrival_date'], '%Y-%m-%d')
            dep = datetime.strptime(dest['departure_date'], '%Y-%m-%d')
            current = arr
            while current < dep:
                date_str = current.strftime('%Y-%m-%d')
                if date_str not in events_by_date:
                    events_by_date[date_str] = {'destination': dest, 'activities': [], 'transport': None, 'accommodation': None}
                current += __import__('datetime').timedelta(days=1)
        
        for act in activities:
            date_str = act['date']
            if date_str in events_by_date:
                events_by_date[date_str]['activities'].append(act)
        
        for seg in transport:
            # Find the date when this transport occurs (assume it's on departure date of from_city)
            for date_str, ev in events_by_date.items():
                if ev['destination']['city'] == seg['from_city']:
                    ev['transport'] = seg
                    break
        
        for acc in accommodation:
            check_in = acc['check_in']
            check_out = acc['check_out']
            from datetime import datetime, timedelta
            ci = datetime.strptime(check_in, '%Y-%m-%d')
            co = datetime.strptime(check_out, '%Y-%m-%d')
            current = ci
            while current < co:
                date_str = current.strftime('%Y-%m-%d')
                if date_str in events_by_date:
                    events_by_date[date_str]['accommodation'] = acc
                current += timedelta(days=1)
        
        # Sort dates
        sorted_dates = sorted(events_by_date.keys())
        
        # Generate flowchart
        lines = []
        if style == 'ascii_art':
            lines.append('╔════════════════════════════════════════╗')
            lines.append('║     TRAVEL ITINERARY FLOWCHART        ║')
            lines.append('╚════════════════════════════════════════╝')
            lines.append('')
            for i, date_str in enumerate(sorted_dates):
                ev = events_by_date[date_str]
                dest = ev['destination']
                lines.append(f'┌──────────────────────────────────────────┐')
                lines.append(f'│  {date_str}  {dest["city"]}, {dest["country"]}                           │')
                lines.append(f'├──────────────────────────────────────────┤')
                if ev.get('transport'):
                    t = ev['transport']
                    lines.append(f'│  🚗 {t["mode"].capitalize()}: {t["from_city"]} → {t["to_city"]} ({t["duration_hours"]}h)    │')
                if ev.get('accommodation'):
                    a = ev['accommodation']
                    lines.append(f'│  🏨 {a["property_name"]}                               │')
                for act in ev['activities']:
                    time_str = f'{act.get("time", "")}' if act.get('time') else ''
                    lines.append(f'│  {time_str+ " " if time_str else ""}📍 {act["description"]}                    │')
                lines.append(f'└──────────────────────────────────────────┘')
                if i < len(sorted_dates) - 1:
                    lines.append('         ↓')
                    lines.append('    (next day)')
        elif style == 'simple_boxes':
            lines.append('+==============================================+')
            lines.append('|           TRAVEL ITINERARY                  |')
            lines.append('+==============================================+')
            for i, date_str in enumerate(sorted_dates):
                ev = events_by_date[date_str]
                dest = ev['destination']
                lines.append('+------------------------------------------+')
                lines.append(f'| {date_str} | {dest["city"]}, {dest["country"]}')
                lines.append('+------------------------------------------+')
                if ev.get('transport'):
                    t = ev['transport']
                    lines.append(f'| TRANSPORT: {t["mode"].upper()} {t["from_city"]}->{t["to_city"]} ({t["duration_hours"]}h)')
                if ev.get('accommodation'):
                    a = ev['accommodation']
                    lines.append(f'| STAY AT: {a["property_name"]}')
                for act in ev['activities']:
                    lines.append(f'| ACTIVITY: {act["description"]}')
                lines.append('+------------------------------------------+')
                lines.append('               ||')
                lines.append('               \\/')
        else:  # indented_tree
            lines.append('Travel Itinerary')
            lines.append('=' * 40)
            for i, date_str in enumerate(sorted_dates):
                ev = events_by_date[date_str]
                dest = ev['destination']
                lines.append(f'├─ {date_str} - {dest["city"]}')
                if ev.get('transport'):
                    t = ev['transport']
                    lines.append(f'│  ├─ 🚗 {t["mode"]}: {t["from_city"]} → {t["to_city"]}')
                if ev.get('accommodation'):
                    a = ev['accommodation']
                    lines.append(f'│  ├─ 🏨 {a["property_name"]}')
                for act in ev['activities']:
                    lines.append(f'│  ├─ 📍 {act["description"]}')
                lines.append(f'│  └─ (next)')
        
        result = {'flowchart': '\n'.join(lines), 'dates_covered': len(sorted_dates), 'destinations_covered': len(set(d['city'] for d in destinations))}
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "travel_itinerary_flowchart",
    "description": "Generate a visual flowchart representation of a multi-destination travel itinerary, showing daily activities, transportation modes, and accommodation with time-based branching logic, returning an ASCII or text-based diagram of the travel plan for quick overview and sharing.",
    "category": "visualization",
    "domain": "travel",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "destinations": {
            "type": "array",
            "description": "List of destination objects in chronological order, each containing city name, country, arrival date, and departure date.",
            "items": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name of the destination."
                    },
                    "country": {
                        "type": "string",
                        "description": "Country name of the destination."
                    },
                    "arrival_date": {
                        "type": "string",
                        "description": "Arrival date in YYYY-MM-DD format."
                    },
                    "departure_date": {
                        "type": "string",
                        "description": "Departure date in YYYY-MM-DD format."
                    }
                },
                "required": [
                    "city",
                    "country",
                    "arrival_date",
                    "departure_date"
                ]
            }
        },
        "activities": {
            "type": "array",
            "description": "Optional: List of activities with date, time, location, and description to include in the flowchart nodes.",
            "items": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date of the activity in YYYY-MM-DD format."
                    },
                    "time": {
                        "type": "string",
                        "description": "Time of the activity in HH:MM format (24-hour)."
                    },
                    "location": {
                        "type": "string",
                        "description": "Location name or address where the activity takes place."
                    },
                    "description": {
                        "type": "string",
                        "description": "Short description of the activity (e.g., 'City walking tour', 'Museum visit')."
                    }
                },
                "required": [
                    "date",
                    "description"
                ]
            }
        },
        "transport": {
            "type": "array",
            "description": "Optional: List of transport segments between destinations, each specifying mode, provider, departure time, and duration.",
            "items": {
                "type": "object",
                "properties": {
                    "from_city": {
                        "type": "string",
                        "description": "Departure city name."
                    },
                    "to_city": {
                        "type": "string",
                        "description": "Arrival city name."
                    },
                    "mode": {
                        "type": "string",
                        "enum": [
                            "flight",
                            "train",
                            "bus",
                            "car",
                            "ferry",
                            "walking"
                        ],
                        "description": "Mode of transportation."
                    },
                    "provider": {
                        "type": "string",
                        "description": "Optional: Transport provider name (e.g., 'Delta Airlines', 'Eurostar')."
                    },
                    "departure_time": {
                        "type": "string",
                        "description": "Departure time in HH:MM format (24-hour)."
                    },
                    "duration_hours": {
                        "type": "number",
                        "description": "Duration of transport in hours (e.g., 2.5 for 2 hours 30 minutes).",
                        "minimum": 0
                    }
                },
                "required": [
                    "from_city",
                    "to_city",
                    "mode",
                    "duration_hours"
                ]
            }
        },
        "accommodation": {
            "type": "array",
            "description": "Optional: List of accommodation bookings with check-in/out dates and property name.",
            "items": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City where accommodation is located."
                    },
                    "property_name": {
                        "type": "string",
                        "description": "Name of the hotel, hostel, or rental."
                    },
                    "check_in": {
                        "type": "string",
                        "description": "Check-in date in YYYY-MM-DD format."
                    },
                    "check_out": {
                        "type": "string",
                        "description": "Check-out date in YYYY-MM-DD format."
                    }
                },
                "required": [
                    "city",
                    "property_name",
                    "check_in",
                    "check_out"
                ]
            }
        },
        "style": {
            "type": "string",
            "enum": [
                "ascii_art",
                "simple_boxes",
                "indented_tree"
            ],
            "description": "Optional: Visual style of the flowchart (default: ascii_art). Options: ascii_art (box-drawing characters), simple_boxes (text boxes with +---+ borders), indented_tree (hierarchical indentation).",
            "default": "ascii_art"
        }
    },
    "required": [
        "destinations"
    ]
},
}
