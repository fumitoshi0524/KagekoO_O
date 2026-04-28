"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Registers and monitors the estimated energy consumption of household appliances."""
    import json
    try:
        data = json.loads(payload)
        required = ['appliance_name', 'power_rating_watts', 'hours_used', 'electricity_rate_per_kwh']
        for field in required:
            if field not in data:
                return f'error: missing required field {field}'
        appliance_name = data['appliance_name']
        power_watts = float(data['power_rating_watts'])
        hours = float(data['hours_used'])
        rate = float(data['electricity_rate_per_kwh'])
        if power_watts <= 0 or hours < 0 or rate <= 0:
            return f'error: power_rating_watts and electricity_rate_per_kwh must be positive, hours_used must be non-negative'
        kwh = (power_watts * hours) / 1000.0
        cost = round(kwh * rate, 2)
        result = {
            'appliance_name': appliance_name,
            'energy_consumed_kwh': round(kwh, 2),
            'estimated_cost': cost,
            'currency': 'local'
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "home_appliance_energy_monitor",
    "description": "Registers and monitors the estimated energy consumption of household appliances based on usage duration and power rating. Returns the calculated energy usage in kWh and estimated cost based on the user's configured electricity rate.",
    "category": "system",
    "domain": "lifestyle",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "appliance_name": {
            "type": "string",
            "description": "Name of the appliance (e.g., 'Air Conditioner', 'Refrigerator')"
        },
        "power_rating_watts": {
            "type": "number",
            "description": "Power rating of the appliance in watts"
        },
        "hours_used": {
            "type": "number",
            "description": "Number of hours the appliance was used today"
        },
        "electricity_rate_per_kwh": {
            "type": "number",
            "description": "Cost per kilowatt-hour in the user's local currency"
        }
    },
    "required": [
        "appliance_name",
        "power_rating_watts",
        "hours_used",
        "electricity_rate_per_kwh"
    ]
},
}
