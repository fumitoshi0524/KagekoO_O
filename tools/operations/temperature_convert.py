"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Convert temperature between Celsius, Fahrenheit, and Kelvin."""
    try:
        data = json.loads(payload)
        value = float(data.get("value", 0))
        from_unit = str(data.get("from", "celsius")).lower().strip()
        to_unit = str(data.get("to", "fahrenheit")).lower().strip()
    except (json.JSONDecodeError, TypeError, ValueError):
        return "error: invalid payload — provide JSON with 'value', 'from', 'to'"

    valid = {"celsius", "fahrenheit", "kelvin"}
    from_unit = from_unit.rstrip("s")
    to_unit = to_unit.rstrip("s")

    if from_unit not in valid or to_unit not in valid:
        return f"error: units must be one of: {', '.join(sorted(valid))}"

    # Convert to Celsius first
    if from_unit == "celsius":
        celsius = value
    elif from_unit == "fahrenheit":
        celsius = (value - 32) * 5 / 9
    else:  # kelvin
        celsius = value - 273.15

    # Convert from Celsius to target
    if to_unit == "celsius":
        result = celsius
    elif to_unit == "fahrenheit":
        result = celsius * 9 / 5 + 32
    else:  # kelvin
        result = celsius + 273.15

    return json.dumps({
        "value": value,
        "from": from_unit,
        "to": to_unit,
        "result": round(result, 2),
    }, indent=2, ensure_ascii=False)


TOOL_SPEC = {
    "name": "temperature_convert",
    "description": "Convert temperature values between Celsius, Fahrenheit, and Kelvin scales.",
    "category": "operations",
    "domain": "environment",
    "risk_level": "read",
    "schema": {
        "type": "object",
        "properties": {
            "value": {
                "type": "number",
                "description": "The temperature value to convert."
            },
            "from": {
                "type": "string",
                "description": "Source temperature unit: celsius, fahrenheit, or kelvin.",
                "enum": ["celsius", "fahrenheit", "kelvin"]
            },
            "to": {
                "type": "string",
                "description": "Target temperature unit: celsius, fahrenheit, or kelvin.",
                "enum": ["celsius", "fahrenheit", "kelvin"]
            }
        },
        "required": ["value", "from", "to"]
    }
}
