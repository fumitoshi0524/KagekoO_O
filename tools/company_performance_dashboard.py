"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        company_name = data.get('company_name')
        data_series = data.get('data_series')
        currency = data.get('currency')
        show_projections = data.get('show_projections', False)
        
        if not company_name or not data_series or not currency:
            return json.dumps({'error': 'Missing required fields: company_name, data_series, currency'})
        
        if len(data_series) < 2:
            return json.dumps({'error': 'At least 2 data points are required for meaningful dashboard'})
        
        # Calculate metrics for each period
        periods = []
        for entry in data_series:
            revenue = entry['revenue']
            expenses = entry['expenses']
            net_income = entry['net_income']
            profit_margin = round((net_income / revenue * 100), 2) if revenue != 0 else 0.0
            expense_ratio = round((expenses / revenue * 100), 2) if revenue != 0 else 0.0
            
            periods.append({
                'period': entry['period'],
                'revenue': revenue,
                'expenses': expenses,
                'net_income': net_income,
                'profit_margin_pct': profit_margin,
                'expense_ratio_pct': expense_ratio
            })
        
        # Calculate growth rates (period over period)
        growth_rates = []
        for i in range(1, len(periods)):
            prev_revenue = periods[i-1]['revenue']
            curr_revenue = periods[i]['revenue']
            growth_pct = round(((curr_revenue - prev_revenue) / prev_revenue * 100), 2) if prev_revenue != 0 else 0.0
            growth_rates.append({
                'from_period': periods[i-1]['period'],
                'to_period': periods[i]['period'],
                'growth_rate_pct': growth_pct
            })
        
        # Calculate averages
        avg_revenue = round(sum(p['revenue'] for p in periods) / len(periods), 2)
        avg_expenses = round(sum(p['expenses'] for p in periods) / len(periods), 2)
        avg_net_income = round(sum(p['net_income'] for p in periods) / len(periods), 2)
        avg_profit_margin = round(sum(p['profit_margin_pct'] for p in periods) / len(periods), 2)
        
        # Generate projections if requested
        projections = []
        if show_projections and len(periods) >= 3:
            # Simple linear regression for projection
            n = len(periods)
            x_values = list(range(n))
            y_values = [p['revenue'] for p in periods]
            
            # Calculate slope and intercept
            x_mean = sum(x_values) / n
            y_mean = sum(y_values) / n
            numerator = sum((x_values[i] - x_mean) * (y_values[i] - y_mean) for i in range(n))
            denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))
            slope = numerator / denominator if denominator != 0 else 0.0
            intercept = y_mean - slope * x_mean
            
            # Project next 2 periods
            for i in range(n, n + 2):
                projected_revenue = round(slope * i + intercept, 2)
                projected_expenses = round(projected_revenue * (avg_expenses / avg_revenue), 2) if avg_revenue != 0 else 0.0
                projected_net_income = projected_revenue - projected_expenses
                projections.append({
                    'period': f'Projected_{i - n + 1}',
                    'revenue': max(0, projected_revenue),
                    'expenses': max(0, projected_expenses),
                    'net_income': projected_net_income,
                    'profit_margin_pct': round((projected_net_income / projected_revenue * 100), 2) if projected_revenue > 0 else 0.0,
                    'expense_ratio_pct': round((projected_expenses / projected_revenue * 100), 2) if projected_revenue > 0 else 0.0
                })
        
        result = {
            'dashboard': {
                'company_name': company_name,
                'currency': currency,
                'summary': {
                    'total_periods': len(periods),
                    'avg_revenue': avg_revenue,
                    'avg_expenses': avg_expenses,
                    'avg_net_income': avg_net_income,
                    'avg_profit_margin_pct': avg_profit_margin
                },
                'performance_data': periods,
                'growth_rates': growth_rates
            }
        }
        
        if projections:
            result['dashboard']['projections'] = projections
        
        return json.dumps(result, ensure_ascii=False)
        
    except json.JSONDecodeError as e:
        return f'error: Invalid JSON - {e}'
    except KeyError as e:
        return f'error: Missing expected field in data_series - {e}'
    except ZeroDivisionError:
        return f'error: Division by zero encountered - check data validity'
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "company_performance_dashboard",
    "description": "Generate a business performance dashboard visualization from company financial data including revenue, expenses, profit margins, and growth rates across multiple time periods, returning structured data suitable for chart rendering.",
    "category": "visualization",
    "domain": "business",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "company_name": {
            "type": "string",
            "description": "Name of the company for dashboard title and branding"
        },
        "data_series": {
            "type": "array",
            "description": "Array of quarterly or monthly performance data points",
            "items": {
                "type": "object",
                "properties": {
                    "period": {
                        "type": "string",
                        "description": "Time period identifier in format YYYY-QQ for quarters or YYYY-MM for months"
                    },
                    "revenue": {
                        "type": "number",
                        "description": "Total revenue for the period in the specified currency"
                    },
                    "expenses": {
                        "type": "number",
                        "description": "Total operating expenses for the period in the specified currency"
                    },
                    "net_income": {
                        "type": "number",
                        "description": "Net income (profit) for the period in the specified currency"
                    }
                },
                "required": [
                    "period",
                    "revenue",
                    "expenses",
                    "net_income"
                ]
            }
        },
        "currency": {
            "type": "string",
            "description": "Currency code used for all monetary values (e.g., USD, EUR, GBP)",
            "enum": [
                "USD",
                "EUR",
                "GBP",
                "JPY",
                "CHF",
                "CAD",
                "AUD",
                "CNY"
            ]
        },
        "show_projections": {
            "type": "boolean",
            "description": "Optional: Include trend-based projections for next 2 periods in the visualization data"
        }
    },
    "required": [
        "company_name",
        "data_series",
        "currency"
    ]
},
}
