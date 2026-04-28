"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    import math
    import random
    try:
        data = json.loads(payload)
        region = data.get('region_or_facility')
        year = data.get('year')
        baseline_year = data.get('baseline_year', 1990)
        include_sector = data.get('include_sector_breakdown', True)
        output_format = data.get('output_format', 'chart_json')
        
        if not region or not year:
            return json.dumps({'error': 'Missing required parameters: region_or_facility, year'})
        if year < 2000 or year > 2030:
            return json.dumps({'error': 'Year must be between 2000 and 2030'})
        
        # Simulate realistic emissions data (in metric tons CO2 equivalent)
        # Use pseudo-random seeded by region name for reproducibility
        seed = hash(region) % 100000
        random.seed(seed + year)
        
        # Emission factors by source (simplified)
        energy_co2 = round(random.uniform(100000000, 5000000000) * (1 + (year - 2000) * 0.02), 2)
        transport_co2 = round(random.uniform(50000000, 2000000000), 2)
        waste_co2 = round(random.uniform(10000000, 500000000), 2)
        industrial_co2 = round(random.uniform(80000000, 3000000000), 2)
        
        total = energy_co2 + transport_co2 + waste_co2 + industrial_co2
        
        # Baseline year data (same region, different seed)
        random.seed(seed + baseline_year)
        baseline_energy = round(random.uniform(100000000, 5000000000) * (1 + (baseline_year - 2000) * 0.02), 2)
        baseline_transport = round(random.uniform(50000000, 2000000000), 2)
        baseline_waste = round(random.uniform(10000000, 500000000), 2)
        baseline_industrial = round(random.uniform(80000000, 3000000000), 2)
        baseline_total = baseline_energy + baseline_transport + baseline_waste + baseline_industrial
        
        # Sector breakdown if requested
        sector_data = {}
        if include_sector:
            random.seed(seed + year + 1)
            sectors = ['residential', 'commercial', 'industrial', 'transportation', 'agriculture']
            sector_values = [random.uniform(total * 0.05, total * 0.3) for _ in sectors]
            sector_total = sum(sector_values)
            sector_pct = [round(v / sector_total * 100, 2) for v in sector_values]
            sector_data = {
                'sector_names': sectors,
                'sector_emissions_mt': [round(v / 1e6, 2) for v in sector_values],
                'sector_percentage': sector_pct
            }
        
        # Annual trend (last 5 years including target)
        trend_years = list(range(year - 4, year + 1))
        trend_emissions = []
        for y in trend_years:
            random.seed(seed + y)
            e = round(random.uniform(0.8, 1.2) * total, 2)
            trend_emissions.append(e)
        trend_series = [{'year': y, 'total_emissions_mt': round(e / 1e6, 2)} for y, e in zip(trend_years, trend_emissions)]
        
        # Comparison to baseline
        change_pct = round((total - baseline_total) / baseline_total * 100, 2)
        
        if output_format == 'table_json':
            result = {
                'region': region,
                'year': year,
                'baseline_year': baseline_year,
                'source_breakdown': [
                    {'source': 'Energy', 'emissions_mt': round(energy_co2 / 1e6, 2)},
                    {'source': 'Transport', 'emissions_mt': round(transport_co2 / 1e6, 2)},
                    {'source': 'Waste', 'emissions_mt': round(waste_co2 / 1e6, 2)},
                    {'source': 'Industrial', 'emissions_mt': round(industrial_co2 / 1e6, 2)}
                ],
                'total_emissions_mt': round(total / 1e6, 2),
                'baseline_total_mt': round(baseline_total / 1e6, 2),
                'change_vs_baseline_pct': change_pct,
                'trend_data': trend_series,
                'sector_data': sector_data if include_sector else None
            }
        else:
            # chart_json format - arrays for plotting
            result = {
                'region': region,
                'year': year,
                'total_emissions_mt': round(total / 1e6, 2),
                'source_breakdown_chart': {
                    'labels': ['Energy', 'Transport', 'Waste', 'Industrial'],
                    'values_mt': [round(energy_co2 / 1e6, 2), round(transport_co2 / 1e6, 2), round(waste_co2 / 1e6, 2), round(industrial_co2 / 1e6, 2)]
                },
                'trend_chart': {
                    'labels': [str(y) for y in trend_years],
                    'values_mt': [t['total_emissions_mt'] for t in trend_series]
                },
                'baseline_comparison': {
                    'baseline_year': baseline_year,
                    'baseline_total_mt': round(baseline_total / 1e6, 2),
                    'current_total_mt': round(total / 1e6, 2),
                    'change_pct': change_pct
                },
                'sector_chart': sector_data if include_sector else None
            }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "carbon_emissions_dashboard",
    "description": "Generate a structured carbon emissions dashboard report for a given region or facility, including total emissions by source (energy, transport, waste, industrial), sector breakdown, annual trends, and comparison to baseline targets. Returns a JSON object with chart-ready data for visualization libraries.",
    "category": "visualization",
    "domain": "environment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "region_or_facility": {
            "type": "string",
            "description": "Name of the region (e.g., 'European Union', 'North America') or facility (e.g., 'Factory A', 'Port of Rotterdam') to generate the dashboard for."
        },
        "year": {
            "type": "integer",
            "description": "Target year for the dashboard data (e.g., 2023). Must be between 2000 and 2030.",
            "minimum": 2000,
            "maximum": 2030
        },
        "baseline_year": {
            "type": "integer",
            "description": "Optional: Baseline year for comparison (e.g., 1990). If omitted, uses 1990 as default.",
            "minimum": 1990,
            "maximum": 2020
        },
        "include_sector_breakdown": {
            "type": "boolean",
            "description": "Optional: If True, include sector-level breakdown (residential, commercial, industrial, transportation, agriculture). Default True."
        },
        "output_format": {
            "type": "string",
            "description": "Optional: Format of returned data. 'chart_json' (default) returns arrays for labels and values. 'table_json' returns row-wise data.",
            "enum": [
                "chart_json",
                "table_json"
            ]
        }
    },
    "required": [
        "region_or_facility",
        "year"
    ]
},
}
