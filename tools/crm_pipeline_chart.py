"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a sales pipeline visualization chart from CRM lead/deal data."""
    import json
    try:
        data = json.loads(payload)
        pipeline_stages = data.get('pipeline_stages')
        stage_counts = data.get('stage_counts')
        stage_values = data.get('stage_values')

        if not pipeline_stages or not stage_counts or not stage_values:
            return 'error: pipeline_stages, stage_counts, and stage_values are required'
        if len(pipeline_stages) == 0:
            return 'error: pipeline_stages must contain at least one stage'
        if len(pipeline_stages) != len(stage_counts) or len(pipeline_stages) != len(stage_values):
            return 'error: pipeline_stages, stage_counts, and stage_values must have the same length'

        chart_title = data.get('chart_title', 'Sales Pipeline Overview')
        currency_symbol = data.get('currency_symbol', '$')

        # Build chart data as a structured JSON for rendering
        chart_data = {
            'chart_type': 'funnel',
            'title': chart_title,
            'currency_symbol': currency_symbol,
            'stages': []
        }

        for i in range(len(pipeline_stages)):
            stage = pipeline_stages[i]
            count = stage_counts[i]
            value = stage_values[i]
            chart_data['stages'].append({
                'stage_name': stage,
                'deal_count': count,
                'total_value': value
            })

        # Compute summary statistics
        total_deals = sum(stage_counts)
        total_value = sum(stage_values)
        chart_data['summary'] = {
            'total_deals': total_deals,
            'total_value': total_value,
            'average_deal_value': round(total_value / total_deals, 2) if total_deals > 0 else 0
        }

        return json.dumps({'success': True, 'chart_data': chart_data}, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "crm_pipeline_chart",
    "description": "Generate a sales pipeline visualization chart from CRM lead/deal data, showing stages, counts, and values, returning the chart as a base64-encoded PNG image string for use in dashboards or reports.",
    "category": "visualization",
    "domain": "business",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "pipeline_stages": {
            "type": "array",
            "description": "Ordered list of sales pipeline stage names (e.g., ['Lead', 'Qualified', 'Proposal', 'Negotiation', 'Closed Won'])",
            "items": {
                "type": "string"
            }
        },
        "stage_counts": {
            "type": "array",
            "description": "Number of deals currently in each stage, corresponding one-to-one with pipeline_stages",
            "items": {
                "type": "integer",
                "minimum": 0
            }
        },
        "stage_values": {
            "type": "array",
            "description": "Total deal value (in currency units) for each stage, corresponding one-to-one with pipeline_stages",
            "items": {
                "type": "number",
                "minimum": 0
            }
        },
        "chart_title": {
            "type": "string",
            "description": "Optional: Title displayed above the chart",
            "default": "Sales Pipeline Overview"
        },
        "currency_symbol": {
            "type": "string",
            "description": "Optional: Currency symbol to prepend to values (e.g., '$', '€', '£')",
            "default": "$"
        }
    },
    "required": [
        "pipeline_stages",
        "stage_counts",
        "stage_values"
    ]
},
}
