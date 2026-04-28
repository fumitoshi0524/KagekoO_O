"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        periods = data.get('periods')
        series = data.get('series')
        chart_type = data.get('chart_type', 'line')
        title = data.get('title')

        if not periods or not isinstance(periods, list) or len(periods) == 0:
            return json.dumps({'error': 'periods must be a non-empty array of strings'})
        if not series or not isinstance(series, list) or len(series) == 0:
            return json.dumps({'error': 'series must be a non-empty array of objects'})

        # Validate series structure and compute totals
        validated_series = []
        grand_totals = [0] * len(periods)
        for s in series:
            if 'name' not in s or 'values' not in s:
                return json.dumps({'error': f'Each series must have name and values fields'})
            if not isinstance(s['values'], list) or len(s['values']) != len(periods):
                return json.dumps({'error': f'Series "{s.get("name","unknown")}" values length must match periods count'})
            for v in s['values']:
                if not isinstance(v, (int, float)):
                    return json.dumps({'error': f'All revenue values must be numbers, got {type(v).__name__}'})
            # Calculate per-period total and per-series total
            series_total = sum(s['values'])
            for i in range(len(periods)):
                grand_totals[i] += s['values'][i]
            validated_series.append({
                'name': s['name'],
                'values': s['values'],
                'total': series_total,
                'average': round(series_total / len(periods), 2) if len(periods) > 0 else 0
            })

        if not title:
            names = [s['name'] for s in validated_series]
            if len(names) == 1:
                title = f'{names[0]} Revenue Trend'
            else:
                title = f'Revenue Comparison: {', '.join(names[:3])}{"" if len(names) <= 3 else "..."}'

        # Compute trend insights
        insights = []
        for i in range(1, len(periods)):
            diff = grand_totals[i] - grand_totals[i-1]
            pct = round((diff / grand_totals[i-1]) * 100, 2) if grand_totals[i-1] != 0 else 0.0
            insights.append({
                'from_period': periods[i-1],
                'to_period': periods[i],
                'change_absolute': round(diff, 2),
                'change_percentage': pct
            })

        # Determine overall trend direction
        if len(insights) >= 2:
            recent = insights[-3:] if len(insights) >= 3 else insights
            avg_pct = sum(i['change_percentage'] for i in recent) / len(recent)
            if avg_pct > 2:
                trend = 'upward'
            elif avg_pct < -2:
                trend = 'downward'
            else:
                trend = 'stable'
        else:
            trend = 'insufficient_data'

        result = {
            'chart_data': {
                'type': chart_type,
                'title': title,
                'labels': periods,
                'datasets': [
                    {
                        'label': s['name'],
                        'data': s['values'],
                        'total': s['total'],
                        'average': s['average']
                    }
                    for s in validated_series
                ]
            },
            'summary': {
                'total_revenue': round(sum(grand_totals), 2),
                'average_per_period': round(sum(grand_totals) / len(periods), 2),
                'highest_period': periods[grand_totals.index(max(grand_totals))],
                'highest_revenue': round(max(grand_totals), 2),
                'lowest_period': periods[grand_totals.index(min(grand_totals))],
                'lowest_revenue': round(min(grand_totals), 2),
                'trend': trend
            },
            'period_insights': insights
        }
        return json.dumps(result, ensure_ascii=False)
    except json.JSONDecodeError as e:
        return f'error: Invalid JSON payload - {e}'
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "revenue_trend_visualizer",
    "description": "Generate a revenue trend chart data from monthly revenue records across product lines or business units, returning structured chart data suitable for line or bar chart rendering to help stakeholders quickly spot sales patterns and growth opportunities.",
    "category": "visualization",
    "domain": "business",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "periods": {
            "type": "array",
            "description": "Array of time period labels in chronological order (e.g. months, quarters, years).",
            "items": {
                "type": "string"
            }
        },
        "series": {
            "type": "array",
            "description": "Array of data series objects. Each series is a named group (e.g. a product line, region, or business unit) with its revenue values per period.",
            "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Series name identifying the revenue source (e.g. 'Cloud Services', 'Enterprise Licenses', 'EMEA Region')."
                    },
                    "values": {
                        "type": "array",
                        "description": "Revenue values in the same order as periods, each representing revenue in the same base currency unit (e.g. USD).",
                        "items": {
                            "type": "number"
                        }
                    }
                },
                "required": [
                    "name",
                    "values"
                ]
            }
        },
        "chart_type": {
            "type": "string",
            "description": "Optional: The preferred chart type for rendering. Defaults to 'line' if not specified.",
            "enum": [
                "line",
                "bar"
            ],
            "default": "line"
        },
        "title": {
            "type": "string",
            "description": "Optional: Custom chart title. If omitted, a default title is generated from the series names."
        }
    },
    "required": [
        "periods",
        "series"
    ]
},
}
