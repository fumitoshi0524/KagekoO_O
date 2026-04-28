"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate sales performance dashboard."""
    import json
    from datetime import datetime, timedelta
    import random
    import math

    try:
        data = json.loads(payload)

        business_unit = data.get('business_unit')
        time_period = data.get('time_period')
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        include_targets = data.get('include_targets', False)
        chart_types = data.get('chart_types', ['line', 'bar', 'pie', 'funnel'])

        if not business_unit or not time_period or not start_date_str or not end_date_str:
            return json.dumps({'error': 'Missing required fields: business_unit, time_period, start_date, end_date'}, ensure_ascii=False)

        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        except ValueError:
            return json.dumps({'error': 'Invalid date format. Use YYYY-MM-DD'}, ensure_ascii=False)

        if end_date <= start_date:
            return json.dumps({'error': 'end_date must be after start_date'}, ensure_ascii=False)

        total_days = (end_date - start_date).days
        if total_days > 730:
            return json.dumps({'error': 'Date range cannot exceed 2 years'}, ensure_ascii=False)

        random.seed(hash(business_unit + start_date_str + end_date_str))

        if time_period == 'monthly':
            num_periods = max(1, total_days // 28)
        elif time_period == 'quarterly':
            num_periods = max(1, total_days // 90)
        else:
            num_periods = max(1, total_days // 365)

        labels = []
        revenue_data = []
        conversion_rate_data = []
        growth_data = []

        current = start_date
        for i in range(num_periods):
            if time_period == 'monthly':
                label = current.strftime('%b %Y')
            elif time_period == 'quarterly':
                quarter = (current.month - 1) // 3 + 1
                label = f'Q{quarter} {current.year}'
            else:
                label = str(current.year)

            labels.append(label)

            base_revenue = 50000 + (i * 5000)
            noise = random.uniform(-10000, 10000)
            revenue = max(10000, base_revenue + noise)
            revenue_data.append(round(revenue, 2))

            conversion = random.uniform(0.02, 0.08)
            conversion_rate_data.append(round(conversion, 4))

            if i > 0:
                growth = ((revenue - revenue_data[i-1]) / revenue_data[i-1]) * 100
            else:
                growth = 0.0
            growth_data.append(round(growth, 2))

            if time_period == 'monthly':
                if current.month == 12:
                    current = current.replace(year=current.year + 1, month=1)
                else:
                    current = current.replace(month=current.month + 1)
            elif time_period == 'quarterly':
                next_month = current.month + 3
                year_inc = (next_month - 1) // 12
                new_month = ((next_month - 1) % 12) + 1
                current = current.replace(year=current.year + year_inc, month=new_month)
            else:
                current = current.replace(year=current.year + 1)

        total_revenue = round(sum(revenue_data), 2)
        avg_conversion = round(sum(conversion_rate_data) / len(conversion_rate_data), 4)
        avg_growth = round(sum(growth_data) / len(growth_data), 2)

        summary_stats = {
            'total_revenue': total_revenue,
            'average_revenue': round(total_revenue / num_periods, 2),
            'average_conversion_rate': avg_conversion,
            'average_growth_rate': avg_growth,
            'periods_analyzed': num_periods
        }

        if include_targets:
            target_revenue = [round(r * random.uniform(1.05, 1.2), 2) for r in revenue_data]
            target_conversion = [round(c * random.uniform(0.9, 1.1), 4) for c in conversion_rate_data]
        else:
            target_revenue = None
            target_conversion = None

        charts = {}
        if 'line' in chart_types:
            line_chart = {
                'type': 'line',
                'title': f'Revenue Trend - {business_unit}',
                'x_axis': {'label': 'Period', 'values': labels},
                'y_axis': {'label': 'Revenue (USD)'},
                'series': [{'name': 'Revenue', 'data': revenue_data}]
            }
            if target_revenue:
                line_chart['series'].append({'name': 'Target', 'data': target_revenue, 'dashed': True})
            charts['line'] = line_chart

        if 'bar' in chart_types:
            bar_chart = {
                'type': 'bar',
                'title': f'Conversion Rate by Period - {business_unit}',
                'x_axis': {'label': 'Period', 'values': labels},
                'y_axis': {'label': 'Conversion Rate (%)'},
                'series': [{'name': 'Conversion Rate', 'data': [r * 100 for r in conversion_rate_data]}]
            }
            if target_conversion:
                bar_chart['series'].append({'name': 'Target', 'data': [r * 100 for r in target_conversion], 'dashed': True})
            charts['bar'] = bar_chart

        if 'pie' in chart_types:
            segment_labels = ['New Customers', 'Repeat Customers', 'Referrals', 'Corporate Accounts']
            segment_values = []
            for _ in range(num_periods):
                weights = [random.uniform(0.2, 0.4), random.uniform(0.3, 0.5), random.uniform(0.1, 0.2), random.uniform(0.05, 0.15)]
                total_w = sum(weights)
                segment_values.append([round(w/total_w*100, 1) for w in weights])

            avg_segment = [round(sum(vals)/num_periods, 1) for vals in zip(*segment_values)]
            pie_chart = {
                'type': 'pie',
                'title': f'Revenue Distribution by Customer Segment - {business_unit}',
                'labels': segment_labels,
                'data': avg_segment
            }
            charts['pie'] = pie_chart

        if 'funnel' in chart_types:
            funnel_stages = ['Leads', 'Qualified', 'Proposal', 'Negotiation', 'Closed Won']
            funnel_values = []
            leads = random.randint(500, 2000)
            funnel_values.append(leads)
            for _ in range(4):
                leads = int(leads * random.uniform(0.3, 0.6))
                funnel_values.append(leads)

            funnel_chart = {
                'type': 'funnel',
                'title': f'Sales Funnel - {business_unit} (Last Period)',
                'stages': funnel_stages,
                'values': funnel_values,
                'conversion_rates': [round((funnel_values[i+1]/funnel_values[i])*100, 1) if funnel_values[i] > 0 else 0 for i in range(4)]
            }
            charts['funnel'] = funnel_chart

        result = {
            'dashboard': {
                'business_unit': business_unit,
                'time_period': time_period,
                'date_range': {'start': start_date_str, 'end': end_date_str},
                'summary_statistics': summary_stats,
                'charts': charts
            },
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'version': '1.0'
            }
        }

        return json.dumps(result, ensure_ascii=False)

    except json.JSONDecodeError:
        return json.dumps({'error': 'Invalid JSON payload'}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': f'Unexpected error: {str(e)}'}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "sales_performance_dashboard",
    "description": "Generate a comprehensive sales performance dashboard visualization for a specified business unit, including key metrics like revenue, conversion rate, and sales growth. Returns a structured JSON object containing chart data and summary statistics for executive reporting.",
    "category": "visualization",
    "domain": "business",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "business_unit": {
            "type": "string",
            "description": "Name of the business unit or sales region to generate the dashboard for",
            "examples": [
                "North America",
                "EMEA",
                "APAC"
            ]
        },
        "time_period": {
            "type": "string",
            "enum": [
                "monthly",
                "quarterly",
                "yearly"
            ],
            "description": "Time granularity for the dashboard data aggregation"
        },
        "start_date": {
            "type": "string",
            "description": "Start date for the dashboard data range (YYYY-MM-DD format)",
            "examples": [
                "2024-01-01"
            ]
        },
        "end_date": {
            "type": "string",
            "description": "End date for the dashboard data range (YYYY-MM-DD format)",
            "examples": [
                "2024-12-31"
            ]
        },
        "include_targets": {
            "type": "boolean",
            "description": "Optional: Include target vs actual comparison in the dashboard. Default is false"
        },
        "chart_types": {
            "type": "array",
            "description": "Optional: List of visualization chart types to include. Default includes all types",
            "items": {
                "type": "string",
                "enum": [
                    "line",
                    "bar",
                    "pie",
                    "funnel"
                ]
            }
        }
    },
    "required": [
        "business_unit",
        "time_period",
        "start_date",
        "end_date"
    ]
},
}
