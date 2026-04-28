"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        months = data.get('months')
        revenues = data.get('revenues')
        currency = data.get('currency', 'USD')
        title = data.get('title', 'Monthly Revenue Dashboard')
        if not months or not revenues:
            return json.dumps({'error': 'Both months and revenues are required.'})
        if len(months) != len(revenues):
            return json.dumps({'error': 'months and revenues must have the same length.'})
        if len(months) == 0:
            return json.dumps({'error': 'At least one month and revenue value required.'})
        total = sum(revenues)
        average = total / len(revenues)
        if len(revenues) >= 2:
            trend = 'upward' if revenues[-1] > revenues[0] else 'downward' if revenues[-1] < revenues[0] else 'stable'
        else:
            trend = 'stable'
        chart_data = {
            'title': title,
            'currency': currency,
            'months': months,
            'revenues': revenues,
            'total_revenue': round(total, 2),
            'average_monthly_revenue': round(average, 2),
            'trend': trend
        }
        return json.dumps(chart_data, ensure_ascii=False)
    except json.JSONDecodeError as e:
        return f'error: Invalid JSON input - {e}'
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "revenue_dashboard_chart",
    "description": "Generate a structured JSON representation of a revenue dashboard chart from monthly revenue data, including aggregated totals, average revenue, and trend direction, for use in business performance presentations and executive reporting.",
    "category": "visualization",
    "domain": "business",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "months": {
            "type": "array",
            "description": "Array of month labels (e.g., 'January', 'Feb') in chronological order, each a non-empty string.",
            "items": {
                "type": "string",
                "minLength": 1
            },
            "minItems": 1
        },
        "revenues": {
            "type": "array",
            "description": "Array of monthly revenue numbers (positive floats or ints) in the same order as months, representing currency amounts (e.g., in USD).",
            "items": {
                "type": "number",
                "minimum": 0
            },
            "minItems": 1
        },
        "currency": {
            "type": "string",
            "description": "Optional: Three-letter currency code for display (e.g., 'USD', 'EUR', 'GBP'). Defaults to 'USD'.",
            "default": "USD",
            "enum": [
                "USD",
                "EUR",
                "GBP",
                "JPY",
                "CNY",
                "INR"
            ]
        },
        "title": {
            "type": "string",
            "description": "Optional: Custom chart title. If not provided, defaults to 'Monthly Revenue Dashboard'.",
            "default": "Monthly Revenue Dashboard"
        }
    },
    "required": [
        "months",
        "revenues"
    ]
},
}
