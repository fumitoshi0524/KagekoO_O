"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generates a sustainability report."""
    import json
    try:
        data = json.loads(payload)
        org = data['organization_name']
        carbon = data['carbon_emissions_tonnes']
        energy = data['energy_consumption_mwh']
        water = data['water_consumption_m3']
        waste = data['waste_production_tonnes']
        recycle = data['recycling_percentage']
        year = data['report_year']
        initiatives = data.get('initiatives', [])
        
        if not isinstance(carbon, (int, float)) or carbon < 0:
            return json.dumps({'error': 'carbon_emissions_tonnes must be a non-negative number'})
        if not isinstance(energy, (int, float)) or energy < 0:
            return json.dumps({'error': 'energy_consumption_mwh must be a non-negative number'})
        if not isinstance(water, (int, float)) or water < 0:
            return json.dumps({'error': 'water_consumption_m3 must be a non-negative number'})
        if not isinstance(waste, (int, float)) or waste < 0:
            return json.dumps({'error': 'waste_production_tonnes must be a non-negative number'})
        if not isinstance(recycle, (int, float)) or recycle < 0 or recycle > 100:
            return json.dumps({'error': 'recycling_percentage must be between 0 and 100'})
        
        report = {
            'title': f'Sustainability Report {year}',
            'organization': org,
            'year': year,
            'summary': f'In {year}, {org} emitted {carbon} tonnes of CO2, consumed {energy} MWh of energy, used {water} m3 of water, produced {waste} tonnes of waste, and recycled {recycle}% of waste.',
            'metrics': {
                'carbon_emissions_tonnes': carbon,
                'energy_consumption_mwh': energy,
                'water_consumption_m3': water,
                'waste_production_tonnes': waste,
                'recycling_percentage': recycle
            },
            'initiatives': initiatives if initiatives else ['None reported']
        }
        return json.dumps(report, ensure_ascii=False)
    except KeyError as e:
        return f'error: Missing required field {e}'
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "sustainability_report_generator",
    "description": "Generates a structured sustainability report for a specified organization by compiling environmental metrics such as carbon emissions, energy usage, water consumption, waste production, and sustainability initiatives into a comprehensive document for regulatory or stakeholder review.",
    "category": "generate",
    "domain": "environment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "organization_name": {
            "type": "string",
            "description": "The name of the organization for which the sustainability report is generated."
        },
        "carbon_emissions_tonnes": {
            "type": "number",
            "description": "Total carbon emissions in metric tonnes for the reporting period."
        },
        "energy_consumption_mwh": {
            "type": "number",
            "description": "Total energy consumption in megawatt-hours."
        },
        "water_consumption_m3": {
            "type": "number",
            "description": "Total water consumption in cubic meters."
        },
        "waste_production_tonnes": {
            "type": "number",
            "description": "Total waste production in metric tonnes."
        },
        "recycling_percentage": {
            "type": "number",
            "description": "Percentage of waste that is recycled, from 0 to 100."
        },
        "initiatives": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "Optional: List of sustainability initiatives undertaken by the organization, e.g., 'solar panel installation', 'zero-waste program'."
        },
        "report_year": {
            "type": "integer",
            "description": "The year the report covers, e.g., 2024."
        }
    },
    "required": [
        "organization_name",
        "carbon_emissions_tonnes",
        "energy_consumption_mwh",
        "water_consumption_m3",
        "waste_production_tonnes",
        "recycling_percentage",
        "report_year"
    ]
},
}
