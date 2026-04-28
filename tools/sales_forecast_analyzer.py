"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        records = data.get('sales_records', [])
        months = data.get('forecast_months', 1)
        if not records or months < 1 or months > 12:
            return json.dumps({'error': 'Invalid input: at least 1 record required, forecast_months between 1-12'}, ensure_ascii=False)
        # Extract sales values in chronological order
        sales = [r['total_sales'] for r in records]
        n = len(sales)
        if n < 2:
            return json.dumps({'error': 'Need at least 2 records for trend analysis'}, ensure_ascii=False)
        # Simple linear regression: y = a + b*x
        x_vals = list(range(n))
        sum_x = sum(x_vals)
        sum_y = sum(sales)
        sum_xy = sum(x * y for x, y in zip(x_vals, sales))
        sum_xx = sum(x*x for x in x_vals)
        denominator = n * sum_xx - sum_x * sum_x
        if denominator == 0:
            slope = 0.0
        else:
            slope = (n * sum_xy - sum_x * sum_y) / denominator
        intercept = (sum_y - slope * sum_x) / n
        # Forecast
        forecast = []
        for i in range(1, months+1):
            next_x = n + i - 1
            predicted = intercept + slope * next_x
            forecast.append({'month_offset': i, 'forecast_sales': round(predicted, 2)})
        # Trend and confidence
        trend = 'upward' if slope > 0 else ('downward' if slope < 0 else 'stable')
        growth_rate = round((slope / (sum_y/n)) * 100, 2) if sum_y > 0 else 0.0
        # Rough confidence interval based on residual std
        residuals = [sales[i] - (intercept + slope * i) for i in range(n)]
        variance = sum(r*r for r in residuals) / (n - 2) if n > 2 else 0.0
        std_error = variance ** 0.5
        confidence_lower = round(intercept + slope * (n + months - 1) - 1.96*std_error, 2)
        confidence_upper = round(intercept + slope * (n + months - 1) + 1.96*std_error, 2)
        result = {
            'trend': trend,
            'growth_rate_percent': growth_rate,
            'forecast': forecast,
            'confidence_interval': {'lower': confidence_lower, 'upper': confidence_upper},
            'analysis_period_months': n
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "sales_forecast_analyzer",
    "description": "Analyze historical sales data to generate a short-term revenue forecast, including trend direction, expected growth rate, and confidence intervals, returning structured predictions for strategic planning.",
    "category": "analysis",
    "domain": "business",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "sales_records": {
            "type": "array",
            "description": "Array of monthly sales records, each with a date (YYYY-MM format) and total_sales (positive number)",
            "items": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Month and year in YYYY-MM format"
                    },
                    "total_sales": {
                        "type": "number",
                        "description": "Total sales amount in the given month, must be non-negative"
                    }
                },
                "required": [
                    "date",
                    "total_sales"
                ]
            }
        },
        "forecast_months": {
            "type": "integer",
            "description": "Number of months ahead to forecast (1 to 12)"
        }
    },
    "required": [
        "sales_records",
        "forecast_months"
    ]
},
}
