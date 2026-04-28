"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Calculate BMI (Body Mass Index) and return health category."""
    try:
        data = json.loads(payload)
        weight_kg = float(data.get("weight_kg", 0))
        height_cm = float(data.get("height_cm", 0))
        unit = str(data.get("unit", "metric")).lower().strip()
    except (json.JSONDecodeError, TypeError, ValueError):
        return "error: invalid payload — provide JSON with weight and height"

    if unit == "imperial":
        weight_lb = float(data.get("weight_lb", weight_kg))
        height_in = float(data.get("height_in", height_cm))
        if weight_lb <= 0 or height_in <= 0:
            return "error: weight_lb and height_in must be positive"
        weight_kg = weight_lb * 0.453592
        height_cm = height_in * 2.54
    else:
        if weight_kg <= 0 or height_cm <= 0:
            return "error: weight_kg and height_cm must be positive"

    height_m = height_cm / 100
    bmi = round(weight_kg / (height_m * height_m), 1)

    if bmi < 18.5:
        category = "Underweight"
    elif bmi < 25:
        category = "Normal weight"
    elif bmi < 30:
        category = "Overweight"
    else:
        category = "Obese"

    return json.dumps({
        "bmi": bmi,
        "category": category,
        "weight_kg": round(weight_kg, 1),
        "height_cm": round(height_cm, 1),
    }, indent=2, ensure_ascii=False)


TOOL_SPEC = {
    "name": "bmi_calculator",
    "description": "Calculate Body Mass Index (BMI) from weight and height, supporting metric (kg/cm) and imperial (lb/in) units, with health category classification.",
    "category": "analysis",
    "domain": "healthcare",
    "risk_level": "read",
    "schema": {
        "type": "object",
        "properties": {
            "weight_kg": {
                "type": "number",
                "description": "Weight in kilograms (for metric units)."
            },
            "height_cm": {
                "type": "number",
                "description": "Height in centimeters (for metric units)."
            },
            "weight_lb": {
                "type": "number",
                "description": "Weight in pounds (for imperial units)."
            },
            "height_in": {
                "type": "number",
                "description": "Height in inches (for imperial units)."
            },
            "unit": {
                "type": "string",
                "description": "Unit system: metric (kg/cm) or imperial (lb/in).",
                "enum": ["metric", "imperial"],
                "default": "metric"
            }
        },
        "required": ["unit"]
    }
}
