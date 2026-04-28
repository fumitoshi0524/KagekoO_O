"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    from collections import defaultdict
    try:
        data = json.loads(payload)
        transactions = data.get('transactions', [])
        if not transactions:
            return json.dumps({'error': 'No transactions provided.'}, ensure_ascii=False)
        budget = data.get('budget')
        if budget is not None and (budget < 0):
            return json.dumps({'error': 'Budget must be non-negative.'}, ensure_ascii=False)
        if len(transactions) > 1000:
            return json.dumps({'error': 'Transaction limit is 1000.'}, ensure_ascii=False)
        total = 0.0
        category_totals = defaultdict(float)
        for tx in transactions:
            cat = tx.get('category', 'other')
            amt = tx.get('amount', 0)
            if amt < 0:
                return json.dumps({'error': 'Negative amount found in transaction.'}, ensure_ascii=False)
            total += amt
            category_totals[cat] += amt
        num_days = 30
        avg_daily_spend = round(total / num_days, 2)
        sorted_categories = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
        top_categories = [{'category': cat, 'total': round(amt, 2)} for cat, amt in sorted_categories[:5]]
        result = {
            'total_spend': round(total, 2),
            'average_daily_spend': avg_daily_spend,
            'top_categories': top_categories,
            'summary': f'Your total spend is ${round(total,2)} over about 30 days. Top category: {top_categories[0]["category"] if top_categories else "N/A"}.'
        }
        if budget is not None:
            if total > budget:
                result['overspend_alert'] = True
                result['overspend_amount'] = round(total - budget, 2)
            else:
                result['overspend_alert'] = False
                result['overspend_amount'] = 0.0
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)})


TOOL_SPEC = {
    "name": "expense_analyzer",
    "description": "Analyze personal monthly spending data to identify top spending categories, compute average daily spend, and detect whether spending exceeds a user-defined monthly budget. Returns a summary with category breakdown, total spend, and an overspend alert.",
    "category": "analysis",
    "domain": "lifestyle",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "transactions": {
            "type": "array",
            "description": "List of individual expense transactions, each with a category and amount. Supports up to 1000 entries.",
            "items": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Spending category (e.g., 'groceries', 'dining', 'transport', 'bills', 'shopping', 'entertainment', 'health', 'other')."
                    },
                    "amount": {
                        "type": "number",
                        "description": "Transaction amount in dollars, must be non-negative."
                    }
                },
                "required": [
                    "category",
                    "amount"
                ]
            }
        },
        "budget": {
            "type": "number",
            "description": "Optional: Monthly budget in dollars for comparison and overspend detection. Must be positive if provided."
        }
    },
    "required": [
        "transactions"
    ]
},
}
