"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        records = data.get('revenue_data')
        if not records:
            return json.dumps({'error': 'revenue_data is required'})
        group_by = data.get('group_by', 'product_line')
        period_type = data.get('period_type', 'monthly')
        # Validate period format
        for r in records:
            if not r.get('period') or not r.get('entity'):
                return json.dumps({'error': 'Each record must have period and entity'})
        # Aggregate by entity and period
        from collections import defaultdict
        entity_periods = defaultdict(lambda: defaultdict(lambda: {'revenue': 0, 'units': 0}))
        for r in records:
            ent = r['entity']
            per = r['period']
            entity_periods[ent][per]['revenue'] += r['revenue']
            entity_periods[ent][per]['units'] += r['units_sold']
        # Build summary text
        summary_lines = []
        for entity in sorted(entity_periods.keys()):
            periods = sorted(entity_periods[entity].keys())
            revs = [entity_periods[entity][p]['revenue'] for p in periods]
            units = [entity_periods[entity][p]['units'] for p in periods]
            total_rev = sum(revs)
            total_units = sum(units)
            if len(revs) >= 2:
                growth = ((revs[-1] - revs[0]) / revs[0]) * 100 if revs[0] != 0 else 0
                trend = 'upward' if growth > 5 else ('downward' if growth < -5 else 'stable')
                summary_lines.append(f"{entity}: {len(periods)} periods, total revenue ${total_rev:,.2f}, total units {total_units}, {trend} trend (growth {growth:.1f}%)")
            else:
                summary_lines.append(f"{entity}: single period, revenue ${total_rev:,.2f}, units {total_units}")
        summary_text = ' | '.join(summary_lines)
        # Prepare structured data for chart
        result = {
            'summary': summary_text,
            'trend_data': {}
        }
        for entity in entity_periods:
            result['trend_data'][entity] = [
                {'period': p, 'revenue': entity_periods[entity][p]['revenue'], 'units_sold': entity_periods[entity][p]['units']}
                for p in sorted(entity_periods[entity].keys())
            ]
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({'error': str(e)})


TOOL_SPEC = {
    "name": "sales_trend_summary",
    "description": "Generates a structured textual summary and data table of quarterly or monthly sales trends (revenue, units sold, growth rate) across product lines or regions, returning a JSON object with summary text and raw data for dashboard embedding.",
    "category": "visualization",
    "domain": "business",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "revenue_data": {
            "type": "array",
            "description": "Array of sales records, each containing period, product_line or region, revenue, and units_sold.",
            "items": {
                "type": "object",
                "properties": {
                    "period": {
                        "type": "string",
                        "description": "Time period in YYYY-MM or YYYY-QQ format.",
                        "examples": [
                            "2024-01",
                            "2024-Q1"
                        ]
                    },
                    "entity": {
                        "type": "string",
                        "description": "Product line name or region identifier.",
                        "examples": [
                            "Electronics",
                            "North America"
                        ]
                    },
                    "revenue": {
                        "type": "number",
                        "description": "Total revenue in USD for that period and entity."
                    },
                    "units_sold": {
                        "type": "integer",
                        "description": "Number of units sold."
                    }
                },
                "required": [
                    "period",
                    "entity",
                    "revenue",
                    "units_sold"
                ]
            }
        },
        "group_by": {
            "type": "string",
            "description": "Optional: Grouping dimension for trend analysis: 'product_line' or 'region'.",
            "enum": [
                "product_line",
                "region"
            ],
            "default": "product_line"
        },
        "period_type": {
            "type": "string",
            "description": "Optional: Time granularity: 'monthly' or 'quarterly'.",
            "enum": [
                "monthly",
                "quarterly"
            ],
            "default": "monthly"
        }
    },
    "required": [
        "revenue_data"
    ]
},
}
