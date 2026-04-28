"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        total_emissions = 0.0
        breakdown = {}

        # Emission factors (kg CO2e per unit) — simplified estimates
        transport_factors = {
            "car_petrol": 0.192,
            "car_diesel": 0.171,
            "car_hybrid": 0.128,
            "car_electric": 0.052,
            "bus": 0.105,
            "train": 0.041,
            "domestic_flight": 0.255,
            "international_flight": 0.195
        }

        # Transportation
        transport = data.get("transportation", {})
        if transport:
            mode = transport.get("mode", "")
            distance_km = transport.get("distance_km", 0)
            if distance_km > 0:
                factor_key = mode
                if mode == "car":
                    car_type = transport.get("car_type", "petrol")
                    factor_key = f"car_{car_type}"
                factor = transport_factors.get(factor_key, 0.192)
                transport_emissions = distance_km * factor
                total_emissions += transport_emissions
                breakdown["transportation"] = round(transport_emissions, 2)

        # Energy
        energy = data.get("energy", {})
        if energy:
            electricity_kwh = energy.get("electricity_kwh", 0)
            natural_gas_kwh = energy.get("natural_gas_kwh", 0)
            energy_emissions = (electricity_kwh * 0.233) + (natural_gas_kwh * 0.202)
            if energy_emissions > 0:
                total_emissions += energy_emissions
                breakdown["energy"] = round(energy_emissions, 2)

        # Waste
        waste_kg = data.get("waste_kg", 0)
        if waste_kg > 0:
            waste_emissions = waste_kg * 0.6
            total_emissions += waste_emissions
            breakdown["waste"] = round(waste_emissions, 2)

        result = {
            "total_kg_co2e": round(total_emissions, 2),
            "breakdown": breakdown,
            "equivalent_info": f"Approximately equivalent to {round(total_emissions / 100, 2)} trees absorbing CO2 over a year"
        }

        if total_emissions == 0:
            result["warning"] = "No emissions calculated — at least one activity input required."

        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "carbon_footprint_estimator",
    "description": "Estimate the carbon footprint (kg CO2e) of common activities: transportation (car, bus, train, plane), energy usage (electricity, natural gas), and waste generation, returning a breakdown by category and a total emissions estimate.",
    "category": "operations",
    "domain": "environment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "transportation": {
            "type": "object",
            "description": "Transportation details for footprint calculation.",
            "properties": {
                "mode": {
                    "type": "string",
                    "description": "Mode of transport.",
                    "enum": [
                        "car",
                        "bus",
                        "train",
                        "domestic_flight",
                        "international_flight"
                    ]
                },
                "distance_km": {
                    "type": "number",
                    "description": "Distance traveled in kilometers."
                },
                "car_type": {
                    "type": "string",
                    "description": "Optional: Car fuel type (only if mode is 'car').",
                    "enum": [
                        "petrol",
                        "diesel",
                        "hybrid",
                        "electric"
                    ]
                }
            },
            "required": [
                "mode",
                "distance_km"
            ]
        },
        "energy": {
            "type": "object",
            "description": "Energy usage details for footprint calculation.",
            "properties": {
                "electricity_kwh": {
                    "type": "number",
                    "description": "Optional: Electricity consumption in kilowatt-hours."
                },
                "natural_gas_kwh": {
                    "type": "number",
                    "description": "Optional: Natural gas consumption in kilowatt-hours."
                }
            }
        },
        "waste_kg": {
            "type": "number",
            "description": "Optional: Waste generation in kilograms, assuming mixed disposal (landfill)."
        }
    },
    "required": []
},
}
