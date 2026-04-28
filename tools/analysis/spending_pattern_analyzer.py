"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        current = data.get('current_month_transactions')
        if not current or not isinstance(current, list):
            return json.dumps({'error': 'Missing or invalid current_month_transactions'}, ensure_ascii=False)
        previous = data.get('previous_month_transactions', [])
        if not isinstance(previous, list):
            return json.dumps({'error': 'Invalid previous_month_transactions'}, ensure_ascii=False)
        threshold = data.get('anomaly_threshold_percentage', 50)
        if not isinstance(threshold, (int, float)) or threshold < 0:
            return json.dumps({'error': 'Invalid anomaly_threshold_percentage'}, ensure_ascii=False)

        # Aggregate current month
        current_totals = {}
        for t in current:
            cat = t.get('category')
            amt = t.get('amount')
            if not cat or not isinstance(amt, (int, float)) or amt <= 0:
                return json.dumps({'error': f'Invalid transaction: {t}'}, ensure_ascii=False)
            current_totals[cat] = current_totals.get(cat, 0) + amt

        current_total = sum(current_totals.values())

        # Aggregate previous month
        previous_totals = {}
        for t in previous:
            cat = t.get('category')
            amt = t.get('amount')
            if not cat or not isinstance(amt, (int, float)) or amt <= 0:
                return json.dumps({'error': f'Invalid transaction: {t}'}, ensure_ascii=False)
            previous_totals[cat] = previous_totals.get(cat, 0) + amt

        previous_total = sum(previous_totals.values())

        # Build category summary with percentages
        category_summary = []
        for cat in ['food', 'transport', 'housing', 'entertainment', 'other']:
            cur = current_totals.get(cat, 0)
            pct = round((cur / current_total * 100) if current_total > 0 else 0, 2)
            category_summary.append({'category': cat, 'amount': round(cur, 2), 'percentage': pct})

        # Compare with previous month
        comparison = []
        anomalies = []
        all_cats = set(list(current_totals.keys()) + list(previous_totals.keys()))
        for cat in ['food', 'transport', 'housing', 'entertainment', 'other']:
            cur = current_totals.get(cat, 0)
            prev = previous_totals.get(cat, 0)
            change = None
            if prev > 0:
                change = round(((cur - prev) / prev) * 100, 2)
                if abs(change) >= threshold:
                    anomalies.append({
                        'category': cat,
                        'change_percentage': change,
                        'reason': f"Spending {'increased' if change > 0 else 'decreased'} by {abs(change)}%, exceeding {threshold}% threshold"
                    })
            elif prev == 0 and cur > 0:
                anomalies.append({
                    'category': cat,
                    'change_percentage': None,
                    'reason': f'New spending category appeared with amount {round(cur, 2)}'
                })
            comparison.append({
                'category': cat,
                'current': round(cur, 2),
                'previous': round(prev, 2),
                'change_percentage': change
            })

        # Total comparison
        total_change = None
        if previous_total > 0:
            total_change = round(((current_total - previous_total) / previous_total) * 100, 2)
        if previous_total > 0 and abs(total_change) >= threshold:
            anomalies.append({
                'category': 'total',
                'change_percentage': total_change,
                'reason': f'Total spending {'increased' if total_change > 0 else 'decreased'} by {abs(total_change)}%, exceeding {threshold}% threshold'
            })

        result = {
            'current_total': round(current_total, 2),
            'previous_total': round(previous_total, 2) if previous else None,
            'total_change_percentage': total_change,
            'category_summary': category_summary,
            'comparison_with_previous': comparison,
            'anomalies': anomalies
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "spending_pattern_analyzer",
    "description": "Analyze monthly spending records to identify spending trends, categorize expenses (food, transport, housing, entertainment, other), calculate category percentages, and detect unusual spending spikes or drops compared to the previous month. Returns a summary table of category totals, a comparison with the previous period, and a list of flagged anomalies.",
    "category": "analysis",
    "domain": "lifestyle",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "current_month_transactions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Category of the transaction (e.g., food, transport, housing, entertainment, other)",
                        "enum": [
                            "food",
                            "transport",
                            "housing",
                            "entertainment",
                            "other"
                        ]
                    },
                    "amount": {
                        "type": "number",
                        "description": "Transaction amount in the user's base currency, must be positive"
                    },
                    "date": {
                        "type": "string",
                        "description": "Transaction date in ISO 8601 format (YYYY-MM-DD)"
                    }
                },
                "required": [
                    "category",
                    "amount",
                    "date"
                ]
            },
            "description": "List of transactions for the current month"
        },
        "previous_month_transactions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Category of the transaction (e.g., food, transport, housing, entertainment, other)",
                        "enum": [
                            "food",
                            "transport",
                            "housing",
                            "entertainment",
                            "other"
                        ]
                    },
                    "amount": {
                        "type": "number",
                        "description": "Transaction amount in the user's base currency, must be positive"
                    },
                    "date": {
                        "type": "string",
                        "description": "Transaction date in ISO 8601 format (YYYY-MM-DD)"
                    }
                },
                "required": [
                    "category",
                    "amount",
                    "date"
                ]
            },
            "description": "Optional: list of transactions for the previous month to enable trend comparison"
        },
        "anomaly_threshold_percentage": {
            "type": "number",
            "description": "Optional: percentage change threshold to flag an anomaly (default 50). For example, if a category spending increases by more than 50% compared to previous month, it is flagged."
        }
    },
    "required": [
        "current_month_transactions"
    ]
},
}
