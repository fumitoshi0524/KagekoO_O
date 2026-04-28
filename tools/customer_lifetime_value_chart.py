"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a customer lifetime value (CLV) distribution chart and summary statistics."""
    import json
    import math
    try:
        data = json.loads(payload)
        customers = data.get('customers')
        chart_format = data.get('chart_format')
        thresholds = data.get('segmentation_thresholds', {})
        include_raw = data.get('include_raw_data', False)

        if not customers or len(customers) == 0:
            return json.dumps({'error': 'No customer data provided'}, ensure_ascii=False)

        # Validate chart_format
        if chart_format not in ['bar', 'pie', 'histogram']:
            return json.dumps({'error': 'Invalid chart_format. Must be one of: bar, pie, histogram'}, ensure_ascii=False)

        # Compute CLV for each customer: CLV = total_revenue - acquisition_cost (simplified)
        customer_clvs = []
        for cust in customers:
            clv = cust['total_revenue'] - cust['acquisition_cost']
            customer_clvs.append({
                'customer_id': cust['customer_id'],
                'name': cust['name'],
                'clv': round(clv, 2),
                'tenure_months': cust['tenure_months']
            })

        # Sort by CLV descending
        customer_clvs.sort(key=lambda x: x['clv'], reverse=True)

        # Compute summary statistics
        clv_values = [c['clv'] for c in customer_clvs]
        n = len(clv_values)
        total_clv = sum(clv_values)
        avg_clv = round(total_clv / n, 2) if n > 0 else 0
        max_clv = max(clv_values) if clv_values else 0
        min_clv = min(clv_values) if clv_values else 0
        median_clv = sorted(clv_values)[n // 2] if n > 0 else 0

        # Segmentation
        high_min = thresholds.get('high_value_min', avg_clv * 1.5) if 'high_value_min' not in thresholds else thresholds['high_value_min']
        medium_min = thresholds.get('medium_value_min', avg_clv * 0.8) if 'medium_value_min' not in thresholds else thresholds['medium_value_min']

        high_value = [c for c in customer_clvs if c['clv'] >= high_min]
        medium_value = [c for c in customer_clvs if medium_min <= c['clv'] < high_min]
        low_value = [c for c in customer_clvs if c['clv'] < medium_min]

        # Build chart data structure based on format
        if chart_format == 'histogram':
            # Create bins (e.g., 10 bins)
            num_bins = min(10, n)
            if n < 2:
                bins = [{'label': f'${v:.2f}', 'count': 1, 'customers': [c]} for v, c in zip(clv_values, customer_clvs)]
            else:
                bin_min = min_clv
                bin_max = max_clv
                bin_width = (bin_max - bin_min) / num_bins if num_bins > 0 else 1
                bins = []
                for i in range(num_bins):
                    lower = bin_min + i * bin_width
                    upper = bin_min + (i + 1) * bin_width
                    count = sum(1 for c in clv_values if lower <= c < upper)
                    bins.append({
                        'label': f'${lower:.2f} - ${upper:.2f}',
                        'count': count
                    })
                # Include max value in last bin
                bins[-1]['count'] = sum(1 for c in clv_values if bin_min + (num_bins - 1) * bin_width <= c <= max_clv)
            chart_data = {'type': 'histogram', 'bins': bins}
        elif chart_format == 'pie':
            segments = [
                {'label': f'Low Value (< ${medium_min:.2f})', 'value': len(low_value), 'percentage': round(len(low_value)/n*100, 2)},
                {'label': f'Medium Value (${medium_min:.2f} - ${high_min:.2f})', 'value': len(medium_value), 'percentage': round(len(medium_value)/n*100, 2)},
                {'label': f'High Value (>= ${high_min:.2f})', 'value': len(high_value), 'percentage': round(len(high_value)/n*100, 2)}
            ]
            chart_data = {'type': 'pie', 'segments': segments}
        else:  # bar
            # Bar chart: top 10 customers by CLV (or all if less than 10)
            top_customers = customer_clvs[:min(10, n)]
            bars = [{'label': c['customer_id'], 'value': c['clv'], 'name': c['name']} for c in top_customers]
            chart_data = {'type': 'bar', 'bars': bars}

        result = {
            'summary': {
                'total_customers': n,
                'total_clv': round(total_clv, 2),
                'average_clv': avg_clv,
                'median_clv': round(median_clv, 2),
                'max_clv': round(max_clv, 2),
                'min_clv': round(min_clv, 2),
                'segmentation': {
                    'high_value_count': len(high_value),
                    'medium_value_count': len(medium_value),
                    'low_value_count': len(low_value),
                    'thresholds': {
                        'high_value_min': round(high_min, 2),
                        'medium_value_min': round(medium_min, 2)
                    }
                }
            },
            'chart': chart_data
        }

        if include_raw:
            result['raw_customer_clvs'] = customer_clvs

        return json.dumps(result, ensure_ascii=False)
    except json.JSONDecodeError:
        return json.dumps({'error': 'Invalid JSON payload'}, ensure_ascii=False)
    except KeyError as e:
        return json.dumps({'error': f'Missing required key: {e}'}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': f'Processing error: {str(e)}'}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "customer_lifetime_value_chart",
    "description": "Generate a customer lifetime value (CLV) distribution chart and summary statistics from a list of customer profiles, enabling businesses to segment high-value customers and optimize retention strategies.",
    "category": "visualization",
    "domain": "business",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "customers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "string",
                        "description": "Unique identifier for the customer"
                    },
                    "name": {
                        "type": "string",
                        "description": "Customer name"
                    },
                    "total_revenue": {
                        "type": "number",
                        "description": "Total revenue generated from this customer in the period"
                    },
                    "acquisition_cost": {
                        "type": "number",
                        "description": "Cost to acquire this customer"
                    },
                    "tenure_months": {
                        "type": "integer",
                        "description": "Number of months the customer has been active"
                    }
                },
                "required": [
                    "customer_id",
                    "total_revenue",
                    "acquisition_cost",
                    "tenure_months"
                ]
            },
            "description": "List of customer objects with revenue, cost, and tenure data"
        },
        "chart_format": {
            "type": "string",
            "enum": [
                "bar",
                "pie",
                "histogram"
            ],
            "description": "Type of chart to generate for CLV distribution"
        },
        "segmentation_thresholds": {
            "type": "object",
            "properties": {
                "high_value_min": {
                    "type": "number",
                    "description": "Optional: Minimum CLV to be considered high-value"
                },
                "medium_value_min": {
                    "type": "number",
                    "description": "Optional: Minimum CLV to be considered medium-value"
                }
            },
            "description": "Optional: Custom thresholds for segmenting customers into high, medium, and low value tiers"
        },
        "include_raw_data": {
            "type": "boolean",
            "description": "Optional: Whether to include computed CLV values per customer in the output"
        }
    },
    "required": [
        "customers",
        "chart_format"
    ]
},
}
