"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        entity_type = data.get('entity_type')
        entity_name = data.get('entity_name')
        year = data.get('year')
        include_trend = data.get('include_trend', True)
        compare_to = data.get('compare_to')
        if not entity_type or not entity_name or not year:
            return json.dumps({'error': 'Missing required fields: entity_type, entity_name, year'}, ensure_ascii=False)
        if year < 1990 or year > 2025:
            return json.dumps({'error': 'Year must be between 1990 and 2025'}, ensure_ascii=False)
        # Simulated data generation (in production, would query a real emissions database)
        import random
        random.seed(hash(entity_name + str(year)) % (2**31))
        base_emission = random.uniform(100, 10000)  # in megatonnes CO2e
        total_emissions = round(base_emission, 2)
        sectors = {
            'energy': round(base_emission * random.uniform(0.3, 0.5), 2),
            'transport': round(base_emission * random.uniform(0.1, 0.25), 2),
            'industry': round(base_emission * random.uniform(0.15, 0.3), 2),
            'agriculture': round(base_emission * random.uniform(0.05, 0.15), 2),
            'waste': round(base_emission * random.uniform(0.02, 0.08), 2)
        }
        trend = {}
        if include_trend:
            for y in range(1990, year + 1, 5):
                factor = 1 - (y - 1990) * random.uniform(-0.005, 0.01)
                trend[y] = round(base_emission * factor, 2)
        comparison = None
        if compare_to:
            random.seed(hash(compare_to + str(year)) % (2**31))
            comp_emission = round(random.uniform(100, 10000), 2)
            comparison = {
                'benchmark_name': compare_to,
                'benchmark_emission': comp_emission,
                'difference_percent': round((total_emissions - comp_emission) / comp_emission * 100, 2)
            }
        dashboard = {
            'entity': entity_name,
            'entity_type': entity_type,
            'year': year,
            'total_emissions_mtco2e': total_emissions,
            'sector_breakdown': sectors,
            'unit': 'megatonnes CO2 equivalent',
            'charts': {
                'pie_chart': {
                    'title': f'{entity_name} Emissions by Sector ({year})',
                    'labels': list(sectors.keys()),
                    'values': list(sectors.values())
                },
                'bar_chart': {
                    'title': f'{entity_name} Total Emissions ({year})',
                    'value': total_emissions
                }
            },
            'trend': trend if include_trend else None,
            'comparison': comparison
        }
        return json.dumps(dashboard, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "emission_dashboard",
    "description": "Generate a comprehensive dashboard visualization of greenhouse gas emissions data for a specified region or organization, including total emissions, sector breakdowns, trend lines, and comparative benchmarks, returning a JSON structure with chart configurations and summary statistics.",
    "category": "visualization",
    "domain": "environment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "entity_type": {
            "type": "string",
            "description": "Type of entity for which to generate the dashboard: region or organization.",
            "enum": [
                "region",
                "organization"
            ]
        },
        "entity_name": {
            "type": "string",
            "description": "Name of the region (e.g., country, state) or organization (e.g., company name) for the dashboard.",
            "examples": [
                "Germany",
                "Tesla",
                "California"
            ]
        },
        "year": {
            "type": "integer",
            "description": "Target year for the primary data point (e.g., 2023). Must be between 1990 and current year.",
            "minimum": 1990,
            "maximum": 2025
        },
        "include_trend": {
            "type": "boolean",
            "description": "Optional: Whether to include historical trend data from 1990 to the specified year in the dashboard.",
            "default": True
        },
        "compare_to": {
            "type": "string",
            "description": "Optional: Name of a benchmark entity for comparison (e.g., 'global average' or another region/organization).",
            "examples": [
                "global average",
                "European Union"
            ]
        }
    },
    "required": [
        "entity_type",
        "entity_name",
        "year"
    ]
},
}
