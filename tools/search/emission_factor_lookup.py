"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Search for greenhouse gas emission factors by fuel type, sector, and region."""
    import json
    try:
        data = json.loads(payload)
        fuel_type = data.get('fuel_type')
        if not fuel_type:
            return json.dumps({'error': 'fuel_type is required'})
        sector = data.get('sector', 'general')
        region = data.get('region', 'global')
        include_all = data.get('include_all_gases', True)

        # Simulated emission factor database (simplified hypothetical values)
        emission_db = {
            'natural_gas': {'co2': 2.0, 'ch4': 0.0005, 'n2o': 0.0001},
            'diesel': {'co2': 2.7, 'ch4': 0.0003, 'n2o': 0.0002},
            'coal': {'co2': 3.5, 'ch4': 0.001, 'n2o': 0.0003},
            'biomass': {'co2': 1.8, 'ch4': 0.002, 'n2o': 0.0004},
            'gasoline': {'co2': 2.3, 'ch4': 0.0004, 'n2o': 0.0002},
            'lpg': {'co2': 1.5, 'ch4': 0.0002, 'n2o': 0.0001},
            'wood': {'co2': 1.6, 'ch4': 0.003, 'n2o': 0.0005},
            'electricity_grid': {'co2': 0.5, 'ch4': 0.0001, 'n2o': 0.00005}
        }

        if fuel_type not in emission_db:
            return json.dumps({'error': f'Unknown fuel_type: {fuel_type}'})

        base_factors = emission_db[fuel_type]
        # Apply optional region-specific multiplier (simulated)
        region_multipliers = {
            'global': 1.0,
            'europe': 0.95,
            'asia': 1.1,
            'north_america': 1.05
        }
        multiplier = region_multipliers.get(region, 1.0)

        result = {
            'fuel_type': fuel_type,
            'sector': sector,
            'region': region,
            'unit': 'kg per unit of activity'
        }
        if include_all:
            result['co2_kg'] = round(base_factors['co2'] * multiplier, 4)
            result['ch4_kg'] = round(base_factors['ch4'] * multiplier, 6)
            result['n2o_kg'] = round(base_factors['n2o'] * multiplier, 6)
            result['co2e_kg'] = round((base_factors['co2'] + base_factors['ch4'] * 25 + base_factors['n2o'] * 298) * multiplier, 4)
        else:
            result['co2_kg'] = round(base_factors['co2'] * multiplier, 4)

        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "emission_factor_lookup",
    "description": "Search for greenhouse gas emission factors by fuel type, industry sector, or region, returning CO₂, CH₄, and N₂O values in kg per unit of activity.",
    "category": "search",
    "domain": "environment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "fuel_type": {
            "type": "string",
            "description": "Primary energy source or fuel type (e.g., natural gas, diesel, coal, biomass)",
            "enum": [
                "natural_gas",
                "diesel",
                "coal",
                "biomass",
                "gasoline",
                "lpg",
                "wood",
                "electricity_grid"
            ]
        },
        "sector": {
            "type": "string",
            "description": "Industry sector or activity context (e.g., transportation, power generation, manufacturing, residential)"
        },
        "region": {
            "type": "string",
            "description": "Optional: Geographic region or country for region-specific emission factors (default: global average)",
            "default": "global"
        },
        "include_all_gases": {
            "type": "boolean",
            "description": "Optional: If True, returns factors for CO₂, CH₄, and N₂O; otherwise only CO₂ (default: True)"
        }
    },
    "required": [
        "fuel_type"
    ]
},
}
