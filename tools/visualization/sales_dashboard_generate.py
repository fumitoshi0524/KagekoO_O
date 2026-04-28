"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generates a structured sales performance dashboard summary from raw sales transaction data."""
    import json
    from datetime import datetime
    from collections import defaultdict

    try:
        data = json.loads(payload)
        records = data.get('sales_records')
        base_currency = data.get('base_currency', 'USD')

        if not isinstance(records, list) or len(records) == 0:
            return json.dumps({'error': 'sales_records must be a non-empty array.'})

        total_revenue = 0.0
        region_revenue = defaultdict(float)
        category_revenue = defaultdict(float)
        monthly_revenue = defaultdict(float)
        transaction_count = len(records)

        for i, rec in enumerate(records):
            if not all(k in rec for k in ('date', 'region', 'product_category', 'revenue')):
                return json.dumps({'error': f'Record at index {i} missing required fields.'})
            try:
                rev = float(rec['revenue'])
                if rev < 0:
                    return json.dumps({'error': f'Negative revenue at index {i}.'})
                parsed_date = datetime.strptime(rec['date'], '%Y-%m-%d')
                month_key = parsed_date.strftime('%Y-%m')
            except (ValueError, TypeError):
                return json.dumps({'error': f'Invalid date or revenue format at index {i}.'})

            total_revenue += rev
            region_revenue[rec['region']] += rev
            category_revenue[rec['product_category']] += rev
            monthly_revenue[month_key] += rev

        # Calculate month-over-month growth (percentage)
        sorted_months = sorted(monthly_revenue.keys())
        mom_growth = {}
        for i in range(1, len(sorted_months)):
            prev = monthly_revenue[sorted_months[i-1]]
            curr = monthly_revenue[sorted_months[i]]
            if prev > 0:
                growth = round(((curr - prev) / prev) * 100, 2)
            else:
                growth = None
            mom_growth[sorted_months[i]] = {'revenue': round(curr, 2), 'growth_percent': growth}

        # Convert defaultdicts to regular dicts with rounded values
        region_revenue = {k: round(v, 2) for k, v in region_revenue.items()}
        category_revenue = {k: round(v, 2) for k, v in category_revenue.items()}
        top_region = max(region_revenue, key=region_revenue.get)
        top_category = max(category_revenue, key=category_revenue.get)

        result = {
            'currency': base_currency,
            'total_revenue': round(total_revenue, 2),
            'transaction_count': transaction_count,
            'average_revenue_per_transaction': round(total_revenue / transaction_count, 2) if transaction_count > 0 else 0,
            'region_breakdown': region_revenue,
            'category_breakdown': category_revenue,
            'monthly_performance': {m: {'revenue': round(r, 2)} for m, r in monthly_revenue.items()},
            'month_over_month_growth': mom_growth,
            'top_region_by_revenue': {'region': top_region, 'revenue': region_revenue[top_region]},
            'top_category_by_revenue': {'category': top_category, 'revenue': category_revenue[top_category]}
        }

        return json.dumps(result, ensure_ascii=False)

    except json.JSONDecodeError:
        return json.dumps({'error': 'Invalid JSON payload.'})
    except Exception as e:
        return json.dumps({'error': f'Unexpected error: {str(e)}'})


TOOL_SPEC = {
    "name": "sales_dashboard_generate",
    "description": "Generates a structured sales performance dashboard summary from raw sales transaction data, including revenue totals, regional breakdowns, product category performance, and month-over-month trends, returning a JSON report suitable for embedding into reporting interfaces.",
    "category": "visualization",
    "domain": "business",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "sales_records": {
            "type": "array",
            "description": "Array of sales transaction objects, each containing date, region, product_category, and revenue.",
            "items": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Transaction date in ISO 8601 format (YYYY-MM-DD)."
                    },
                    "region": {
                        "type": "string",
                        "description": "Sales region name, e.g. North America, Europe, Asia."
                    },
                    "product_category": {
                        "type": "string",
                        "description": "Product category name, e.g. Electronics, Apparel, Home Goods."
                    },
                    "revenue": {
                        "type": "number",
                        "description": "Revenue amount for the transaction in USD, must be non-negative."
                    }
                },
                "required": [
                    "date",
                    "region",
                    "product_category",
                    "revenue"
                ]
            }
        },
        "base_currency": {
            "type": "string",
            "description": "Optional: Three-letter currency code for the revenue values. Default is USD. Acceptable values: USD, EUR, GBP, JPY, CNY.",
            "default": "USD",
            "enum": [
                "USD",
                "EUR",
                "GBP",
                "JPY",
                "CNY"
            ]
        }
    },
    "required": [
        "sales_records"
    ]
},
}
