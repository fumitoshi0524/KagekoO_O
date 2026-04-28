"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    import math
    from datetime import datetime, timedelta

    try:
        data = json.loads(payload)
        portfolio_id = data.get('portfolio_id')
        period = data.get('period')
        report_format = data.get('report_format', 'summary')
        include_benchmarks = data.get('include_benchmarks', False)

        if not portfolio_id or not isinstance(portfolio_id, str) or portfolio_id.strip() == '':
            return json.dumps({'error': 'Invalid or missing portfolio_id'})
        if period not in ['1M', '3M', '6M', '1Y', '3Y', '5Y', 'YTD']:
            return json.dumps({'error': 'Invalid period. Must be one of: 1M, 3M, 6M, 1Y, 3Y, 5Y, YTD'})
        if report_format not in ['summary', 'detailed']:
            return json.dumps({'error': 'Invalid report_format. Must be summary or detailed'})

        # Simulate retrieval of portfolio data (in real scenario, query database)
        # Use deterministic data based on portfolio_id hash for demo purposes
        seed = sum(ord(c) for c in portfolio_id)
        total_value = 100000 + (seed % 500000)
        assets = [
            {'name': 'US Large Cap Equity', 'weight': 0.35, 'return_pct': 12.5, 'risk_pct': 15.0},
            {'name': 'International Equity', 'weight': 0.20, 'return_pct': 8.2, 'risk_pct': 18.0},
            {'name': 'US Small Cap Equity', 'weight': 0.10, 'return_pct': 14.7, 'risk_pct': 22.0},
            {'name': 'Government Bonds', 'weight': 0.20, 'return_pct': 3.1, 'risk_pct': 5.0},
            {'name': 'Corporate Bonds', 'weight': 0.10, 'return_pct': 4.8, 'risk_pct': 7.0},
            {'name': 'Cash & Equivalents', 'weight': 0.05, 'return_pct': 1.5, 'risk_pct': 0.5}
        ]

        # Adjust returns based on period
        period_multipliers = {'1M': 1/12, '3M': 0.25, '6M': 0.5, '1Y': 1.0, '3Y': 3.0, '5Y': 5.0, 'YTD': 0.75}
        mult = period_multipliers[period]

        # Calculate portfolio-level metrics
        portfolio_return = sum(a['weight'] * a['return_pct'] for a in assets) * mult
        # Simple risk: weighted standard deviation with correlation assumption
        avg_risk = sum(a['weight'] * a['risk_pct'] for a in assets)
        # Sharpe ratio (assuming risk-free rate 2%)
        risk_free = 2.0
        sharpe = (portfolio_return - risk_free) / avg_risk if avg_risk > 0 else 0

        # Asset allocation
        allocation = [{'name': a['name'], 'weight_pct': round(a['weight'] * 100, 1), 'value': round(total_value * a['weight'], 2)} for a in assets]

        # Top holdings (simulated)
        top_holdings = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA']

        # Benchmark (S&P 500 approximate return for period)
        benchmark_return_pct = round(10.0 * mult, 2)

        report = {
            'report_metadata': {
                'portfolio_id': portfolio_id,
                'generated_at': datetime.utcnow().isoformat(),
                'period': period,
                'report_format': report_format
            },
            'portfolio_summary': {
                'total_value': round(total_value, 2),
                'currency': 'USD',
                'portfolio_return_pct': round(portfolio_return, 2),
                'risk_volatility_pct': round(avg_risk, 2),
                'sharpe_ratio': round(sharpe, 2),
                'benchmark_return_pct': benchmark_return_pct if include_benchmarks else None
            },
            'asset_allocation': allocation
        }

        if report_format == 'detailed':
            report['detailed_metrics'] = {
                'top_holdings': top_holdings,
                'sector_exposure': [
                    {'sector': 'Technology', 'weight_pct': 30.0},
                    {'sector': 'Healthcare', 'weight_pct': 15.0},
                    {'sector': 'Financials', 'weight_pct': 12.0},
                    {'sector': 'Consumer Cyclical', 'weight_pct': 10.0},
                    {'sector': 'Other', 'weight_pct': 33.0}
                ],
                'risk_breakdown': {
                    'systematic_risk_pct': round(avg_risk * 0.7, 2),
                    'specific_risk_pct': round(avg_risk * 0.3, 2)
                },
                'historical_performance': {
                    'best_month_return_pct': round(5.0 * mult, 2),
                    'worst_month_return_pct': round(-2.5 * mult, 2),
                    'max_drawdown_pct': round(-8.0 * mult, 2)
                }
            }

        return json.dumps(report, ensure_ascii=False, default=str)

    except Exception as e:
        return json.dumps({'error': f'Failed to generate report: {str(e)}'})


TOOL_SPEC = {
    "name": "investment_report_generator",
    "description": "Generate a professional investment portfolio performance report with asset allocation, risk metrics, and return analysis for a given portfolio and time period.",
    "category": "generate",
    "domain": "finance",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "portfolio_id": {
            "type": "string",
            "description": "Unique identifier for the investment portfolio (e.g., portfolio code or account number). Must be a non-empty string."
        },
        "period": {
            "type": "string",
            "enum": [
                "1M",
                "3M",
                "6M",
                "1Y",
                "3Y",
                "5Y",
                "YTD"
            ],
            "description": "Performance period for the report: '1M' (1 month), '3M', '6M', '1Y' (1 year), '3Y', '5Y', 'YTD' (year-to-date)."
        },
        "report_format": {
            "type": "string",
            "enum": [
                "summary",
                "detailed"
            ],
            "description": "Optional: report format: 'summary' for overview, 'detailed' for full breakdown. Default is 'summary'."
        },
        "include_benchmarks": {
            "type": "boolean",
            "description": "Optional: whether to include benchmark comparison (e.g., S&P 500, relevant index). Default is false."
        }
    },
    "required": [
        "portfolio_id",
        "period"
    ]
},
}
