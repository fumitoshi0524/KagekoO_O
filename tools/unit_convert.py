"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Convert between common units of length, mass, volume, area, and speed."""
    try:
        data = json.loads(payload)
        value = float(data.get("value", 0))
        from_unit = str(data.get("from", "")).lower().strip()
        to_unit = str(data.get("to", "")).lower().strip()
    except (json.JSONDecodeError, TypeError, ValueError):
        return "error: invalid payload — provide JSON with 'value', 'from', 'to'"

    # Conversion factors to base unit (SI)
    length = {
        "m": 1, "km": 1000, "cm": 0.01, "mm": 0.001,
        "in": 0.0254, "ft": 0.3048, "yd": 0.9144, "mi": 1609.344,
    }
    mass = {
        "kg": 1, "g": 0.001, "mg": 0.000001, "lb": 0.453592, "oz": 0.0283495,
    }
    volume = {
        "l": 1, "ml": 0.001, "gal": 3.78541, "qt": 0.946353, "cup": 0.236588,
    }
    area = {
        "m2": 1, "km2": 1_000_000, "ha": 10000, "ft2": 0.092903, "acre": 4046.86,
    }
    speed = {
        "ms": 1, "kmh": 0.277778, "mph": 0.44704, "knot": 0.514444,
    }

    all_units = {**length, **mass, **volume, **area, **speed}

    if from_unit not in all_units:
        return f"error: unknown unit '{from_unit}'"
    if to_unit not in all_units:
        return f"error: unknown unit '{to_unit}'"

    # Find which category each unit belongs to
    def find_category(u):
        for cat_name, cat_dict in [("length", length), ("mass", mass), ("volume", volume), ("area", area), ("speed", speed)]:
            if u in cat_dict:
                return cat_name, cat_dict
        return None, None

    from_cat, from_dict = find_category(from_unit)
    to_cat, to_dict = find_category(to_unit)

    if from_cat != to_cat:
        return f"error: cannot convert between different categories ('{from_cat}' and '{to_cat}')"

    base_value = value * from_dict[from_unit]
    result = base_value / to_dict[to_unit]

    return json.dumps({
        "value": value,
        "from": from_unit,
        "to": to_unit,
        "result": round(result, 6),
        "category": from_cat,
    }, indent=2, ensure_ascii=False)


TOOL_SPEC = {
    "name": "unit_convert",
    "description": "Convert between common units of length (m, km, mi, ft, etc.), mass (kg, lb, oz, etc.), volume (L, gal, cup, etc.), area (m2, acre, etc.), and speed (km/h, mph, etc.).",
    "category": "operations",
    "domain": "science",
    "risk_level": "read",
    "schema": {
        "type": "object",
        "properties": {
            "value": {
                "type": "number",
                "description": "The numeric value to convert."
            },
            "from": {
                "type": "string",
                "description": "Source unit abbreviation (e.g. m, km, lb, kg, gal, mph)."
            },
            "to": {
                "type": "string",
                "description": "Target unit abbreviation (e.g. ft, mi, g, oz, l, kmh)."
            }
        },
        "required": ["value", "from", "to"]
    }
}
