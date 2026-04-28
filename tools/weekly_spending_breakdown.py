"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Analyze a list of personal expenses and return a weekly spending breakdown."""
    import json
    from collections import defaultdict
    from datetime import datetime, timedelta

    try:
        data = json.loads(payload)
        expenses = data.get('expenses')
        if not expenses:
            return json.dumps({'error': 'expenses list is required and must not be empty'}, ensure_ascii=False)

        week_start = data.get('week_start')
        if week_start:
            try:
                datetime.strptime(week_start, '%Y-%m-%d')
            except ValueError:
                return json.dumps({'error': 'week_start must be valid date format YYYY-MM-DD'}, ensure_ascii=False)

        # Validate each expense
        for idx, exp in enumerate(expenses):
            if not isinstance(exp.get('amount'), (int, float)) or exp['amount'] <= 0:
                return json.dumps({'error': f'Expense at index {idx}: amount must be a positive number'}, ensure_ascii=False)
            if exp.get('category') not in ['groceries', 'dining', 'transport', 'entertainment', 'utilities', 'shopping', 'health', 'other']:
                return json.dumps({'error': f'Expense at index {idx}: invalid category'}, ensure_ascii=False)

        # Aggregate by category
        totals = defaultdict(float)
        for exp in expenses:
            totals[exp['category']] += exp['amount']

        total_spend = sum(totals.values())
        num_days = 7
        average_daily = round(total_spend / num_days, 2)

        # Build breakdown list
        breakdown = []
        for cat, amt in sorted(totals.items(), key=lambda x: x[1], reverse=True):
            percent = round((amt / total_spend) * 100, 2) if total_spend > 0 else 0
            breakdown.append({
                'category': cat,
                'total': round(amt, 2),
                'percentage': percent
            })

        result = {
            'week_start': week_start if week_start else 'Not specified',
            'total_spend': round(total_spend, 2),
            'average_daily_spend': average_daily,
            'categories': breakdown,
            'total_expenses': len(expenses)
        }

        return json.dumps(result, ensure_ascii=False)

    except json.JSONDecodeError:
        return json.dumps({'error': 'Invalid JSON payload'}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': f'Unexpected error: {str(e)}'}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "weekly_spending_breakdown",
    "description": "Analyze a list of personal expenses categorized by type (e.g., groceries, dining, transport, entertainment, utilities) and generate a weekly spending breakdown with category totals, percentage of total spend, and average daily spend.",
    "category": "analysis",
    "domain": "lifestyle",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "expenses": {
            "type": "array",
            "description": "Array of expense objects, each with an amount (positive number) and a category from the enum.",
            "items": {
                "type": "object",
                "properties": {
                    "amount": {
                        "type": "number",
                        "description": "Monetary value of the expense in your local currency (e.g., USD). Must be a positive number."
                    },
                    "category": {
                        "type": "string",
                        "description": "Category of the expense.",
                        "enum": [
                            "groceries",
                            "dining",
                            "transport",
                            "entertainment",
                            "utilities",
                            "shopping",
                            "health",
                            "other"
                        ]
                    }
                },
                "required": [
                    "amount",
                    "category"
                ]
            },
            "minItems": 1
        },
        "week_start": {
            "type": "string",
            "description": "Optional: Start date of the week in YYYY-MM-DD format (Monday assumed if not provided). Used for labeling the report.",
            "pattern": "^\\d{4}-\\d{2}-\\d{2}$"
        }
    },
    "required": [
        "expenses"
    ]
},
}
