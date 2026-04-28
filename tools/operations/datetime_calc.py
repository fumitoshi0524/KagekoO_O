"""Auto-generated tool module."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone


def run(payload: str) -> str:
    """Perform date/time calculations and formatting."""
    try:
        data = json.loads(payload)
        operation = str(data.get("operation", "now")).lower().strip()
        date_str = str(data.get("date", ""))
        amount = int(data.get("amount", 0))
        unit = str(data.get("unit", "days")).lower().strip()
        fmt = str(data.get("format", "%Y-%m-%d %H:%M:%S"))
    except (json.JSONDecodeError, TypeError, ValueError):
        return "error: invalid payload"

    now = datetime.now(timezone.utc)

    if operation == "now":
        return json.dumps({
            "utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "local": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "timestamp": int(now.timestamp()),
            "day_of_week": now.strftime("%A"),
            "week_number": now.isocalendar()[1],
        }, indent=2, ensure_ascii=False)

    if operation in ("add", "subtract"):
        if not date_str:
            dt = now
        else:
            try:
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                return f"error: cannot parse date '{date_str}'. Use ISO format (e.g. 2024-01-15 or 2024-01-15T10:30:00Z)"

        delta = amount
        if operation == "subtract":
            delta = -delta

        unit_map = {
            "seconds": timedelta(seconds=1), "minutes": timedelta(minutes=1),
            "hours": timedelta(hours=1), "days": timedelta(days=1),
            "weeks": timedelta(weeks=1),
        }
        if unit not in unit_map:
            return f"error: unknown unit '{unit}'. Use: {', '.join(unit_map.keys())}"

        result = dt + delta * unit_map[unit]
        return json.dumps({
            "operation": operation,
            "input_date": dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "amount": amount,
            "unit": unit,
            "result": result.strftime(fmt),
        }, indent=2, ensure_ascii=False)

    if operation == "diff":
        if not date_str:
            return "error: 'date' is required for diff operation"
        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return f"error: cannot parse date '{date_str}'"
        diff = now - dt if dt.tzinfo else now.replace(tzinfo=None) - dt
        return json.dumps({
            "date1": dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "date2": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "total_seconds": int(diff.total_seconds()),
            "days": diff.days,
            "hours": diff.seconds // 3600,
            "minutes": (diff.seconds % 3600) // 60,
        }, indent=2, ensure_ascii=False)

    return f"error: unknown operation '{operation}'. Use: now, add, subtract, or diff"


TOOL_SPEC = {
    "name": "datetime_calc",
    "description": "Perform date/time operations: get current time (now), add/subtract time intervals, or compute difference between two dates.",
    "category": "operations",
    "domain": "technology",
    "risk_level": "read",
    "schema": {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "description": "Operation: 'now' for current time, 'add' to add time, 'subtract' to subtract time, 'diff' for date difference.",
                "enum": ["now", "add", "subtract", "diff"]
            },
            "date": {
                "type": "string",
                "description": "ISO-format date string (e.g. 2024-01-15 or 2024-01-15T10:30:00Z). Required for add/subtract/diff."
            },
            "amount": {
                "type": "integer",
                "description": "Number of time units to add or subtract."
            },
            "unit": {
                "type": "string",
                "description": "Time unit: seconds, minutes, hours, days, weeks.",
                "enum": ["seconds", "minutes", "hours", "days", "weeks"]
            },
            "format": {
                "type": "string",
                "description": "Output date format string (default: %Y-%m-%d %H:%M:%S)."
            }
        },
        "required": ["operation"]
    }
}
