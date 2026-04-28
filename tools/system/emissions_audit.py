"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        facility_id = data.get('facility_id')
        gas_therms = data.get('natural_gas_therms')
        electricity = data.get('electricity_kwh')
        refrig_type = data.get('refrigerant_type')
        refrig_leak = data.get('refrigerant_leak_lbs', 0)

        if not facility_id:
            return json.dumps({'error': 'facility_id is required'}, ensure_ascii=False)
        if gas_therms is None or electricity is None:
            return json.dumps({'error': 'natural_gas_therms and electricity_kwh are required'}, ensure_ascii=False)
        if refrig_type != 'none' and refrig_leak is None:
            return json.dumps({'error': 'refrigerant_leak_lbs required when refrigerant_type is specified'}, ensure_ascii=False)

        # Emission factors (kg CO2e per unit) - simplified estimates
        gas_factor = 5.3  # kg CO2e per therm
        elect_factor = 0.4  # kg CO2e per kWh (US average)
        refrig_factors = {
            'R-410A': 2088,
            'R-22': 1810,
            'R-134a': 1430,
            'R-404A': 3922,
            'none': 0
        }

        co2_gas = gas_therms * gas_factor
        co2_elect = electricity * elect_factor
        co2_refrig = refrig_leak * refrig_factors.get(refrig_type, 0)
        total_co2e = co2_gas + co2_elect + co2_refrig

        result = {
            'facility_id': facility_id,
            'total_co2e_kg': round(total_co2e, 2),
            'breakdown': {
                'natural_gas_kg': round(co2_gas, 2),
                'electricity_kg': round(co2_elect, 2),
                'refrigerant_kg': round(co2_refrig, 2)
            },
            'unit': 'kg CO2e'
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "emissions_audit",
    "description": "Audit and log greenhouse gas emission sources from a facility's operational data (fuel consumption, electricity usage, and refrigerant leaks) using standard emission factors.",
    "category": "system",
    "domain": "environment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "facility_id": {
            "type": "string",
            "description": "Unique identifier for the facility being audited."
        },
        "natural_gas_therms": {
            "type": "number",
            "description": "Natural gas consumption in therms for the reporting period."
        },
        "electricity_kwh": {
            "type": "number",
            "description": "Electricity usage in kilowatt-hours for the reporting period."
        },
        "refrigerant_type": {
            "type": "string",
            "description": "Type of refrigerant used (e.g., R-410A, R-22, or 'none' if no refrigerant).",
            "enum": [
                "R-410A",
                "R-22",
                "R-134a",
                "R-404A",
                "none"
            ]
        },
        "refrigerant_leak_lbs": {
            "type": "number",
            "description": "Optional: Refrigerant leaked in pounds during the period. Required if refrigerant_type is not 'none'."
        }
    },
    "required": [
        "facility_id",
        "natural_gas_therms",
        "electricity_kwh",
        "refrigerant_type"
    ]
},
}
