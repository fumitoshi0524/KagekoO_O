"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        portfolio_id = data.get('portfolio_id')
        sectors = data.get('sectors', [])
        risk_model = data.get('risk_model', 'var_95')
        date_range = data.get('date_range', None)
        
        if not portfolio_id or not sectors:
            return json.dumps({'error': 'Missing required fields: portfolio_id and sectors'})
        
        # Simulate fetching portfolio holdings (in real scenario, query database or API)
        # For this example, generate mock risk/return data per sector
        import random
        random.seed(hash(portfolio_id) % 2**32)
        
        heatmap_data = []
        for sector in sectors:
            num_assets = random.randint(3, 8)
            for _ in range(num_assets):
                asset = {
                    'asset_name': f'{sector.capitalize()}_Asset_{random.randint(1, 100)}',
                    'sector': sector,
                    'risk_score': round(random.uniform(0.1, 0.9), 2),
                    'expected_return': round(random.uniform(-0.02, 0.15), 4)
                }
                heatmap_data.append(asset)
        
        # Compute sector-level averages and identify high-risk clusters
        sector_summary = {}
        for item in heatmap_data:
            sec = item['sector']
            if sec not in sector_summary:
                sector_summary[sec] = {'risk_sum': 0, 'return_sum': 0, 'count': 0}
            sector_summary[sec]['risk_sum'] += item['risk_score']
            sector_summary[sec]['return_sum'] += item['expected_return']
            sector_summary[sec]['count'] += 1
        
        for sec in sector_summary:
            cnt = sector_summary[sec]['count']
            sector_summary[sec]['avg_risk'] = round(sector_summary[sec]['risk_sum'] / cnt, 2) if cnt else 0
            sector_summary[sec]['avg_return'] = round(sector_summary[sec]['return_sum'] / cnt, 4) if cnt else 0
        
        # Mark high-risk clusters (avg_risk > 0.7)
        alerts = [sec for sec, vals in sector_summary.items() if vals['avg_risk'] > 0.7]
        
        result = {
            'portfolio_id': portfolio_id,
            'risk_model': risk_model,
            'date_range': date_range or 'default_last_12_months',
            'heatmap': heatmap_data,
            'sector_summary': sector_summary,
            'high_risk_sectors': alerts
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "portfolio_risk_heatmap",
    "description": "Generate a risk heatmap for a financial portfolio, visualizing the correlation between asset risk scores and expected returns across market sectors, used for identifying high-risk concentrations.",
    "category": "visualization",
    "domain": "finance",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "portfolio_id": {
            "type": "string",
            "description": "Unique identifier of the portfolio to analyze (alphanumeric, up to 36 characters)."
        },
        "sectors": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [
                    "technology",
                    "healthcare",
                    "finance",
                    "energy",
                    "consumer_goods",
                    "utilities"
                ]
            },
            "description": "List of market sectors to include in the heatmap. Each sector must be one of the allowed values."
        },
        "risk_model": {
            "type": "string",
            "enum": [
                "var_95",
                "var_99",
                "beta",
                "standard_deviation"
            ],
            "description": "Risk measurement model used to compute asset risk scores. Default is 'var_95'."
        },
        "date_range": {
            "type": "string",
            "description": "Optional: Date range for historical data in format 'YYYY-MM-DD:YYYY-MM-DD' (e.g., '2024-01-01:2024-12-31'). Must be a valid period."
        }
    },
    "required": [
        "portfolio_id",
        "sectors"
    ]
},
}
