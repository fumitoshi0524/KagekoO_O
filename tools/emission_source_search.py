"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Query a structured registry of greenhouse gas emission sources by industry sector, geographic region, or emission type and return a list of matching facilities with their estimated annual CO2-equivalent emissions."""
    import json
    try:
        data = json.loads(payload)
        # Validate required fields
        if 'industry_sector' not in data:
            return json.dumps({'error': 'Missing required parameter: industry_sector'}, ensure_ascii=False)
        # Simulate a database of emission sources
        emission_sources = [
            {'facility_id': 'SRC-001', 'name': 'Green Valley Power Plant', 'sector': 'energy', 'region': 'USA', 'emission_type': 'CO2', 'annual_emissions_tco2e': 8500000, 'location': {'lat': 40.7128, 'lon': -74.0060}},
            {'facility_id': 'SRC-002', 'name': 'Northern Farms Cooperative', 'sector': 'agriculture', 'region': 'Europe', 'emission_type': 'CH4', 'annual_emissions_tco2e': 230000, 'location': {'lat': 48.8566, 'lon': 2.3522}},
            {'facility_id': 'SRC-003', 'name': 'City Sanitary Landfill', 'sector': 'waste', 'region': 'China', 'emission_type': 'CH4', 'annual_emissions_tco2e': 1200000, 'location': {'lat': 39.9042, 'lon': 116.4074}},
            {'facility_id': 'SRC-004', 'name': 'Cement Plant Alpha', 'sector': 'industrial_processes', 'region': 'Southeast Asia', 'emission_type': 'CO2', 'annual_emissions_tco2e': 5600000, 'location': {'lat': 13.7563, 'lon': 100.5018}},
            {'facility_id': 'SRC-005', 'name': 'Deforestation Zone B', 'sector': 'land_use_change', 'region': 'South America', 'emission_type': 'CO2', 'annual_emissions_tco2e': 32000000, 'location': {'lat': -3.4653, 'lon': -62.2159}},
            {'facility_id': 'SRC-006', 'name': 'Port Container Terminal', 'sector': 'transportation', 'region': 'Europe', 'emission_type': 'CO2', 'annual_emissions_tco2e': 980000, 'location': {'lat': 51.5074, 'lon': -0.1278}},
        ]
        # Apply filters
        results = []
        for src in emission_sources:
            if src['sector'] != data['industry_sector']:
                continue
            if 'region' in data and data['region']:
                if src['region'].lower() != data['region'].lower():
                    continue
            if 'emission_type' in data and data['emission_type'] != 'all':
                if src['emission_type'] != data['emission_type']:
                    continue
            if 'min_emissions' in data and data['min_emissions'] is not None:
                if src['annual_emissions_tco2e'] < data['min_emissions']:
                    continue
            results.append(src)
        max_results = data.get('max_results', 20)
        results = results[:max_results]
        return json.dumps({'count': len(results), 'sources': results}, ensure_ascii=False)
    except json.JSONDecodeError as e:
        return json.dumps({'error': f'Invalid JSON payload: {e}'}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': f'Unexpected error: {e}'}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "emission_source_search",
    "description": "Query a structured registry of greenhouse gas emission sources by industry sector, geographic region, or emission type and return a list of matching facilities with their estimated annual CO2-equivalent emissions.",
    "category": "search",
    "domain": "environment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "industry_sector": {
            "type": "string",
            "description": "Industry sector to filter emission sources by (e.g., energy, agriculture, waste, industrial_processes, land_use_change).",
            "enum": [
                "energy",
                "agriculture",
                "waste",
                "industrial_processes",
                "land_use_change",
                "transportation"
            ]
        },
        "region": {
            "type": "string",
            "description": "Geographic region or country name to narrow the search (e.g., Europe, USA, China, Southeast Asia).",
            "examples": [
                "Europe",
                "USA",
                "China"
            ]
        },
        "emission_type": {
            "type": "string",
            "description": "Type of greenhouse gas emission to filter by.",
            "enum": [
                "CO2",
                "CH4",
                "N2O",
                "F_gases",
                "all"
            ],
            "default": "all"
        },
        "min_emissions": {
            "type": "number",
            "description": "Optional: Minimum annual emissions in metric tons of CO2-equivalent to filter results (inclusive).",
            "minimum": 0
        },
        "max_results": {
            "type": "integer",
            "description": "Optional: Maximum number of emission source records to return. Defaults to 20.",
            "minimum": 1,
            "maximum": 100,
            "default": 20
        }
    },
    "required": [
        "industry_sector"
    ]
},
}
