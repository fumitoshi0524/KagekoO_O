"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Validate business hours for a company timestamp."""
    import json
    from datetime import datetime, timedelta
    import pytz

    try:
        data = json.loads(payload)
        company_id = data.get('company_id')
        timestamp_str = data.get('timestamp')
        timezone = data.get('timezone')
        include_lunch = data.get('include_lunch_break', True)
        weekend_enabled = data.get('weekend_enabled', False)

        if not company_id or not timestamp_str or not timezone:
            return json.dumps({'status': 'error', 'message': 'company_id, timestamp, and timezone are required'})

        # Parse the timestamp
        try:
            dt = datetime.fromisoformat(timestamp_str)
        except ValueError:
            return json.dumps({'status': 'error', 'message': 'Invalid timestamp format. Use ISO 8601 format.'})

        # Get timezone object
        try:
            tz = pytz.timezone(timezone)
        except pytz.UnknownTimeZoneError:
            return json.dumps({'status': 'error', 'message': f'Unknown timezone: {timezone}'})

        # Localize the datetime
        if dt.tzinfo is None:
            dt_local = tz.localize(dt)
        else:
            dt_local = dt.astimezone(tz)

        # Define standard business hours (9 AM to 5 PM)
        weekday = dt_local.weekday()
        hour = dt_local.hour
        minute = dt_local.minute

        # Weekend check
        if not weekend_enabled and weekday >= 5:
            next_open = None
            # Find next Monday 9 AM
            days_ahead = 7 - weekday
            next_monday = dt_local + timedelta(days=days_ahead)
            next_open = next_monday.replace(hour=9, minute=0, second=0, microsecond=0)
            if weekday == 6:
                next_open = (dt_local + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
            return json.dumps({
                'status': 'success',
                'is_open': False,
                'reason': 'Weekend closed',
                'next_open': next_open.isoformat() if next_open else None,
                'previous_open': dt_local.replace(hour=17, minute=0, second=0, microsecond=0).isoformat() if weekday == 5 else None
            })

        # Business hours: 9:00 to 12:00 and 13:00 to 17:00 (with lunch break 12:00-13:00)
        if hour < 9 or hour >= 17:
            # Outside working hours
            next_open_time = dt_local.replace(hour=9, minute=0, second=0, microsecond=0)
            if hour >= 17:
                next_open_time += timedelta(days=1)
                if next_open_time.weekday() >= 5 and not weekend_enabled:
                    next_open_time += timedelta(days=7 - next_open_time.weekday())
            return json.dumps({
                'status': 'success',
                'is_open': False,
                'reason': 'Outside business hours',
                'next_open': next_open_time.isoformat(),
                'previous_open': dt_local.replace(hour=17, minute=0, second=0, microsecond=0).isoformat() if hour < 9 else None
            })

        # Lunch break check
        if include_lunch and hour == 12:
            return json.dumps({
                'status': 'success',
                'is_open': False,
                'reason': 'Lunch break (12:00-13:00)',
                'next_open': dt_local.replace(hour=13, minute=0, second=0, microsecond=0).isoformat(),
                'previous_open': dt_local.replace(hour=12, minute=0, second=0, microsecond=0).isoformat()
            })

        # It's open
        return json.dumps({
            'status': 'success',
            'is_open': True,
            'reason': 'Within business hours',
            'closing_time': dt_local.replace(hour=17, minute=0, second=0, microsecond=0).isoformat(),
            'opening_time': dt_local.replace(hour=9, minute=0, second=0, microsecond=0).isoformat()
        })

    except Exception as e:
        return json.dumps({'status': 'error', 'message': str(e)})



TOOL_SPEC = {
    "name": "business_hours_validator",
    "description": "Validate and check if a given timestamp falls within configured business hours for a company, including handling of timezone, lunch breaks, and weekday/weekend rules, returning the validity status and next/previous open time.",
    "category": "system",
    "domain": "business",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "company_id": {
            "type": "string",
            "description": "Unique identifier for the company whose business hours are to be checked"
        },
        "timestamp": {
            "type": "string",
            "description": "ISO 8601 datetime string (e.g., '2024-03-15T14:30:00') to validate against business hours"
        },
        "timezone": {
            "type": "string",
            "description": "IANA timezone name (e.g., 'America/New_York', 'Europe/London', 'Asia/Tokyo')",
            "enum": [
                "America/New_York",
                "America/Chicago",
                "America/Denver",
                "America/Los_Angeles",
                "Europe/London",
                "Europe/Paris",
                "Europe/Berlin",
                "Asia/Tokyo",
                "Asia/Shanghai",
                "Asia/Kolkata",
                "Australia/Sydney",
                "Pacific/Auckland"
            ]
        },
        "include_lunch_break": {
            "type": "boolean",
            "description": "Optional: Whether to consider lunch break closures when validating hours (default: True)"
        },
        "weekend_enabled": {
            "type": "boolean",
            "description": "Optional: Whether to consider weekend as part of business hours (default: False)"
        }
    },
    "required": [
        "company_id",
        "timestamp",
        "timezone"
    ]
},
}
