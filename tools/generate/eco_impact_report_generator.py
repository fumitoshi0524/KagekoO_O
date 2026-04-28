"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a structured environmental impact report for a given set of business activities."""
    import json
    import math

    try:
        data = json.loads(payload)
        activities = data.get("activities")
        if not activities:
            return json.dumps({"error": "Missing required parameter: activities"}, ensure_ascii=False)

        location = data.get("location", "global")
        include_recommendations = data.get("include_recommendations", False)

        # Benchmark factors (simplified industry averages)
        # CO2 kg per unit, water liters per unit, waste kg per unit
        benchmarks = {
            "energy": {"co2": 0.5, "water": 0.001, "waste": 0.002},
            "transport": {"co2": 0.24, "water": 0.0005, "waste": 0.001},
            "manufacturing": {"co2": 1.2, "water": 0.05, "waste": 0.08},
            "waste": {"co2": 0.1, "water": 0.01, "waste": 1.0},
            "water": {"co2": 0.05, "water": 1.0, "waste": 0.02}
        }

        total_co2 = 0.0
        total_water = 0.0
        total_waste = 0.0
        details = []

        for act in activities:
            name = act.get("name", "unknown")
            category = act.get("category")
            qty = act.get("quantity", 0)
            unit = act.get("unit", "")
            factor = benchmarks.get(category, {"co2": 0, "water": 0, "waste": 0})
            co2 = qty * factor["co2"]
            water = qty * factor["water"]
            waste = qty * factor["waste"]
            total_co2 += co2
            total_water += water
            total_waste += waste
            details.append({
                "activity": name,
                "category": category,
                "co2_kg": round(co2, 2),
                "water_liters": round(water, 2),
                "waste_kg": round(waste, 2)
            })

        report = {
            "summary": {
                "total_co2_kg": round(total_co2, 2),
                "total_water_liters": round(total_water, 2),
                "total_waste_kg": round(total_waste, 2),
                "location": location
            },
            "details": details
        }

        if include_recommendations:
            recommendations = []
            if total_co2 > 10000:
                recommendations.append("Transition to renewable energy sources to reduce carbon emissions.")
            if total_water > 1000:
                recommendations.append("Implement water recycling systems in manufacturing processes.")
            if total_waste > 500:
                recommendations.append("Adopt circular economy principles to minimize waste generation.")
            if not recommendations:
                recommendations.append("Your impact is relatively low; continue monitoring and maintain best practices.")
            report["recommendations"] = recommendations

        return json.dumps(report, ensure_ascii=False)

    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON input"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "eco_impact_report_generator",
    "description": "Generate a structured environmental impact report for a given set of business activities or locations, including carbon footprint, water usage, and waste generation estimates based on industry benchmarks, and return a JSON summary with actionable recommendations.",
    "category": "generate",
    "domain": "environment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "activities": {
            "type": "array",
            "description": "List of business activities or processes to evaluate for environmental impact. Each item must have a name, category, and quantity (e.g., units per year).",
            "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Short identifier for the activity (e.g., 'manufacturing', 'transport_fleet')."
                    },
                    "category": {
                        "type": "string",
                        "description": "Category of the activity: 'energy', 'transport', 'manufacturing', 'waste', 'water'.",
                        "enum": [
                            "energy",
                            "transport",
                            "manufacturing",
                            "waste",
                            "water"
                        ]
                    },
                    "quantity": {
                        "type": "number",
                        "description": "Annual quantity of the activity in standard units (e.g., kWh for energy, km for transport, kg for waste)."
                    },
                    "unit": {
                        "type": "string",
                        "description": "Unit of measurement for the quantity (e.g., 'kWh', 'km', 'kg', 'liters')."
                    }
                },
                "required": [
                    "name",
                    "category",
                    "quantity",
                    "unit"
                ]
            }
        },
        "location": {
            "type": "string",
            "description": "Optional: Geographic location (country or region) to adjust benchmarks for local energy mix or regulations. Default is 'global'.",
            "default": "global"
        },
        "include_recommendations": {
            "type": "boolean",
            "description": "Optional: If True, include up to 3 actionable recommendations for reducing impact. Default is False.",
            "default": False
        }
    },
    "required": [
        "activities"
    ]
},
}
