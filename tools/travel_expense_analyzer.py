"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Analyze travel expense data for patterns and insights."""
    import json
    from collections import defaultdict
    from datetime import datetime

    try:
        data = json.loads(payload)
        expenses = data.get('expenses', [])
        if not expenses:
            return json.dumps({'error': 'No expenses provided'}, ensure_ascii=False)

        # Currency conversion rates (simplified static rates for demonstration)
        rates = {
            'USD': 1.0, 'EUR': 1.08, 'GBP': 1.27, 'JPY': 0.0067,
            'AUD': 0.66, 'CAD': 0.74, 'CHF': 1.12, 'INR': 0.012
        }
        base = data.get('base_currency', 'USD').upper()
        if base not in rates:
            return json.dumps({'error': f'Unsupported base currency: {base}'}, ensure_ascii=False)

        # Convert all expenses to base currency
        converted = []
        for e in expenses:
            if e['currency'] not in rates:
                return json.dumps({'error': f'Unsupported currency: {e["currency"]}'}, ensure_ascii=False)
            base_amount = e['amount'] * rates[e['currency']] / rates[base]
            converted.append({
                'category': e['category'],
                'amount_base': round(base_amount, 2),
                'date': e['date']
            })

        # Aggregate by category
        category_totals = defaultdict(float)
        category_counts = defaultdict(int)
        daily_spending = defaultdict(float)
        total = 0.0
        for e in converted:
            cat = e['category']
            category_totals[cat] += e['amount_base']
            category_counts[cat] += 1
            daily_spending[e['date']] += e['amount_base']
            total += e['amount_base']

        total = round(total, 2)

        # Build result
        result = {
            'total_spent': total,
            'currency': base,
            'category_breakdown': {}
        }

        for cat in ['flights', 'hotels', 'food', 'transport', 'activities', 'other']:
            if cat in category_totals:
                cat_total = round(category_totals[cat], 2)
                entry = {
                    'total': cat_total,
                    'percentage': round((cat_total / total) * 100, 1) if total > 0 else 0,
                    'count': category_counts[cat],
                    'average_per_item': round(cat_total / category_counts[cat], 2) if category_counts[cat] > 0 else 0
                }
                # Compare to budget if provided
                budget = data.get('budget', {})
                if cat in budget:
                    budget_amount = budget[cat]
                    entry['budget'] = budget_amount
                    entry['over_budget'] = cat_total > budget_amount
                    entry['variance'] = round(cat_total - budget_amount, 2)
                result['category_breakdown'][cat] = entry
            else:
                result['category_breakdown'][cat] = {
                    'total': 0,
                    'percentage': 0,
                    'count': 0,
                    'average_per_item': 0
                }

        # Daily averages if trip dates provided
        trip_start = data.get('trip_start')
        trip_end = data.get('trip_end')
        if trip_start and trip_end:
            try:
                start = datetime.strptime(trip_start, '%Y-%m-%d')
                end = datetime.strptime(trip_end, '%Y-%m-%d')
                days = (end - start).days + 1
                if days > 0:
                    result['trip_duration_days'] = days
                    result['average_daily_spend'] = round(total / days, 2)
                    result['highest_spending_day'] = max(daily_spending.items(), key=lambda x: x[1]) if daily_spending else None
                    result['lowest_spending_day'] = min(daily_spending.items(), key=lambda x: x[1]) if daily_spending else None
            except ValueError:
                pass

        # Flag outliers (transactions > 2x average per category)
        outliers = []
        for e in converted:
            cat = e['category']
            avg = category_totals[cat] / category_counts[cat] if category_counts[cat] > 0 else 0
            if avg > 0 and e['amount_base'] > 2 * avg:
                outliers.append({
                    'category': cat,
                    'amount': e['amount_base'],
                    'date': e['date'],
                    'reason': f'Amount {e["amount_base"]} exceeds 2x category average {round(avg, 2)}'
                })
        if outliers:
            result['outliers'] = outliers

        # Spending pattern summary
        if category_totals:
            top_category = max(category_totals, key=category_totals.get)
            result['top_spending_category'] = {
                'category': top_category,
                'amount': round(category_totals[top_category], 2),
                'percentage': round((category_totals[top_category] / total) * 100, 1)
            }

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "travel_expense_analyzer",
    "description": "Analyze travel expense data to identify spending patterns, compare costs across categories (flights, hotels, food, transport), calculate average daily spend, and highlight outliers or budget overruns for a given trip or date range.",
    "category": "analysis",
    "domain": "travel",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "expenses": {
            "type": "array",
            "description": "List of expense entries, each with category, amount, currency, and date",
            "items": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": [
                            "flights",
                            "hotels",
                            "food",
                            "transport",
                            "activities",
                            "other"
                        ],
                        "description": "Expense category"
                    },
                    "amount": {
                        "type": "number",
                        "description": "Expense amount in the specified currency, must be positive"
                    },
                    "currency": {
                        "type": "string",
                        "description": "Three-letter currency code (ISO 4217)"
                    },
                    "date": {
                        "type": "string",
                        "description": "Expense date in YYYY-MM-DD format"
                    }
                },
                "required": [
                    "category",
                    "amount",
                    "currency",
                    "date"
                ]
            }
        },
        "budget": {
            "type": "object",
            "description": "Optional: Budget limits per category to compare against actual spending",
            "properties": {
                "flights": {
                    "type": "number",
                    "description": "Budget for flights in base currency"
                },
                "hotels": {
                    "type": "number",
                    "description": "Budget for hotels"
                },
                "food": {
                    "type": "number",
                    "description": "Budget for food"
                },
                "transport": {
                    "type": "number",
                    "description": "Budget for local transport"
                },
                "activities": {
                    "type": "number",
                    "description": "Budget for activities"
                },
                "other": {
                    "type": "number",
                    "description": "Budget for other expenses"
                }
            }
        },
        "base_currency": {
            "type": "string",
            "description": "Optional: Currency to convert all amounts to for comparison (default USD)"
        },
        "trip_start": {
            "type": "string",
            "description": "Optional: Start date of trip (YYYY-MM-DD) to calculate daily averages"
        },
        "trip_end": {
            "type": "string",
            "description": "Optional: End date of trip (YYYY-MM-DD) to calculate daily averages"
        }
    },
    "required": [
        "expenses"
    ]
},
}
