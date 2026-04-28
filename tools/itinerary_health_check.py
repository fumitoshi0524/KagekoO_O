"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    from datetime import datetime, timedelta, timezone
    try:
        data = json.loads(payload)
        itinerary = data.get('itinerary')
        if not itinerary or not isinstance(itinerary, list):
            return json.dumps({'error': 'itinerary must be a non-empty list'}, ensure_ascii=False)
        assume_transfer = data.get('assume_transfer_time_minutes', 60)
        warnings = []
        criticals = []
        # Sort by start_datetime
        try:
            sorted_events = sorted(itinerary, key=lambda e: e['start_datetime'])
        except Exception:
            return json.dumps({'error': 'invalid datetime format in itinerary entries'}, ensure_ascii=False)
        for i, event in enumerate(sorted_events):
            # Check for missing confirmation numbers
            if not event.get('confirmation_number'):
                warnings.append(f"Event {i+1} ({event.get('event_type')} at {event['location']['city']}) missing confirmation number.")
            # Convert start/end to datetime objects for overlap checks
            try:
                start = datetime.fromisoformat(event['start_datetime'])
                end = datetime.fromisoformat(event['end_datetime'])
            except:
                criticals.append(f"Event {i+1}: invalid datetime format '{event['start_datetime']}' or '{event['end_datetime']}'.")
                continue
            if end < start:
                criticals.append(f"Event {i+1}: end_datetime ({event['end_datetime']}) before start_datetime ({event['start_datetime']}).")
            # Check overlap with previous event
            if i > 0:
                prev = sorted_events[i-1]
                try:
                    prev_end = datetime.fromisoformat(prev['end_datetime'])
                except:
                    prev_end = None
                if prev_end and start < prev_end:
                    criticals.append(f"Overlap between event {i} ({prev['event_type']} at {prev['location']['city']}) ending at {prev['end_datetime']} and event {i+1} ({event['event_type']} at {event['location']['city']}) starting at {event['start_datetime']}.")
                # Check transfer time between different locations
                if prev['location']['city'].lower() != event['location']['city'].lower() or prev['location']['country'].lower() != event['location']['country'].lower():
                    if prev_end:
                        gap = (start - prev_end).total_seconds() / 60
                        if gap < assume_transfer:
                            warnings.append(f"Short transfer time ({int(gap)} min) between event {i} ({prev['location']['city']}) and event {i+1} ({event['location']['city']}). Recommended at least {assume_transfer} minutes.")
            # Check for flights: ensure airport_code is present
            if event['event_type'] == 'flight' and not event['location'].get('airport_code'):
                warnings.append(f"Flight event {i+1} missing airport code in location.")
        result = {
            'status': 'pass' if not criticals else 'fail',
            'critical_count': len(criticals),
            'warning_count': len(warnings),
            'criticals': criticals,
            'warnings': warnings
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "itinerary_health_check",
    "description": "Analyze a travel itinerary for logical consistency and potential issues such as overlapping bookings, unrealistic transfer times, conflicting timezones, or missing confirmations, returning a structured report of warnings and critical errors.",
    "category": "system",
    "domain": "travel",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "itinerary": {
            "type": "array",
            "description": "List of itinerary entries, each representing a scheduled event or booking.",
            "items": {
                "type": "object",
                "properties": {
                    "event_type": {
                        "type": "string",
                        "description": "Type of event: flight, hotel_checkin, hotel_checkout, train, bus, rental_car, activity, meeting, other",
                        "enum": [
                            "flight",
                            "hotel_checkin",
                            "hotel_checkout",
                            "train",
                            "bus",
                            "rental_car",
                            "activity",
                            "meeting",
                            "other"
                        ]
                    },
                    "start_datetime": {
                        "type": "string",
                        "description": "Start date and time in ISO 8601 format with timezone offset (e.g., 2025-06-15T10:30:00+02:00)."
                    },
                    "end_datetime": {
                        "type": "string",
                        "description": "End date and time in ISO 8601 format with timezone offset. For events without a fixed end (e.g., hotel checkin) set to same as start_datetime."
                    },
                    "location": {
                        "type": "object",
                        "properties": {
                            "city": {
                                "type": "string",
                                "description": "City name (e.g., Paris)."
                            },
                            "country": {
                                "type": "string",
                                "description": "Country name (e.g., France)."
                            },
                            "airport_code": {
                                "type": "string",
                                "description": "Optional: IATA airport code for flights (e.g., CDG)."
                            }
                        },
                        "required": [
                            "city",
                            "country"
                        ]
                    },
                    "confirmation_number": {
                        "type": "string",
                        "description": "Optional: booking confirmation or reference number."
                    },
                    "notes": {
                        "type": "string",
                        "description": "Optional: additional notes for the entry."
                    }
                },
                "required": [
                    "event_type",
                    "start_datetime",
                    "end_datetime",
                    "location"
                ]
            }
        },
        "assume_transfer_time_minutes": {
            "type": "integer",
            "description": "Optional: default minimum transfer time in minutes between different locations (default 60). Must be >= 0.",
            "minimum": 0
        }
    },
    "required": [
        "itinerary"
    ]
},
}
