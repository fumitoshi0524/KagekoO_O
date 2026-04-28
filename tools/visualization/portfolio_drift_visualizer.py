"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    import math
    try:
        data = json.loads(payload)
        portfolio_id = data.get('portfolio_id')
        target = data.get('target_weights', {})
        actual = data.get('actual_weights', {})
        threshold = data.get('drift_threshold', 0.05)
        chart_title = data.get('chart_title', 'Portfolio Drift Report')
        
        if not portfolio_id:
            return json.dumps({'error': 'Missing required field: portfolio_id'})
        if not target or not actual:
            return json.dumps({'error': 'Missing target_weights or actual_weights'})
        
        # Validate keys match
        target_keys = set(target.keys())
        actual_keys = set(actual.keys())
        if target_keys != actual_keys:
            return json.dumps({'error': 'target_weights and actual_weights must have identical asset keys'})
        
        # Validate percentage sums
        target_sum = sum(target.values())
        actual_sum = sum(actual.values())
        if abs(target_sum - 1.0) > 0.02:
            return json.dumps({'error': f'Target weights sum to {target_sum:.4f}, expected ~1.0'})
        if abs(actual_sum - 1.0) > 0.02:
            return json.dumps({'error': f'Actual weights sum to {actual_sum:.4f}, expected ~1.0'})
        
        # Compute drift and generate chart data
        drift_data = []
        total_deviation = 0.0
        rebalance_assets = []
        
        for asset in sorted(target.keys()):
            t = target[asset]
            a = actual.get(asset, 0.0)
            drift = round(a - t, 6)
            abs_drift = abs(drift)
            total_deviation += abs_drift
            status = 'overweight' if drift > 0 else 'underweight' if drift < 0 else 'aligned'
            requires_rebalance = abs_drift > threshold
            
            drift_data.append({
                'asset': asset,
                'target_pct': round(t * 100, 2),
                'actual_pct': round(a * 100, 2),
                'drift_pct': round(drift * 100, 2),
                'abs_drift_pct': round(abs_drift * 100, 2),
                'status': status,
                'requires_rebalance': requires_rebalance
            })
            if requires_rebalance:
                rebalance_assets.append(asset)
        
        # Summary statistics
        summary = {
            'portfolio_id': portfolio_id,
            'chart_title': chart_title,
            'total_assets': len(target),
            'total_deviation_pct': round(total_deviation * 100, 2),
            'avg_deviation_per_asset_pct': round((total_deviation / len(target)) * 100, 2),
            'num_rebalance_needed': len(rebalance_assets),
            'rebalance_assets': rebalance_assets,
            'drift_threshold_pct': round(threshold * 100, 2)
        }
        
        # Chart data for bar chart visualization (mock SVG or data points)
        chart_data = {
            'type': 'bar',
            'title': chart_title,
            'labels': [d['asset'] for d in drift_data],
            'datasets': [
                {
                    'label': 'Target %',
                    'data': [d['target_pct'] for d in drift_data],
                    'color': '#4CAF50'
                },
                {
                    'label': 'Actual %',
                    'data': [d['actual_pct'] for d in drift_data],
                    'color': '#2196F3'
                }
            ]
        }
        
        result = {
            'summary': summary,
            'drift_details': drift_data,
            'chart_data': chart_data
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)})


TOOL_SPEC = {
    "name": "portfolio_drift_visualizer",
    "description": "Visualize asset allocation drift of a financial portfolio by comparing actual vs target weights, highlight over/under-weight positions, generate a drift bar chart and a rebalancing priority table, and return summary statistics including total deviation and number of assets requiring rebalancing.",
    "category": "visualization",
    "domain": "finance",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "portfolio_id": {
            "type": "string",
            "description": "Unique identifier for the portfolio (e.g., account number or portfolio name). Must be non-empty."
        },
        "target_weights": {
            "type": "object",
            "description": "Object mapping asset ticker symbols to their target allocation percentages (e.g., {\"AAPL\": 0.25, \"BND\": 0.50}). Sum of values should ideally be 1.0.",
            "additionalProperties": {
                "type": "number",
                "minimum": 0,
                "maximum": 1
            }
        },
        "actual_weights": {
            "type": "object",
            "description": "Object mapping asset ticker symbols to their actual current allocation percentages (same structure as target_weights). Keys must match target_weights exactly.",
            "additionalProperties": {
                "type": "number",
                "minimum": 0,
                "maximum": 1
            }
        },
        "drift_threshold": {
            "type": "number",
            "description": "Optional: Threshold (in absolute decimal difference) above which an asset is flagged for rebalancing. Default 0.05 (5%).",
            "default": 0.05,
            "minimum": 0,
            "maximum": 1
        },
        "chart_title": {
            "type": "string",
            "description": "Optional: Custom title for the generated bar chart. Default: 'Portfolio Drift Report'."
        }
    },
    "required": [
        "portfolio_id",
        "target_weights",
        "actual_weights"
    ]
},
}
