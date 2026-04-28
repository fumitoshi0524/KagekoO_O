"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        source = data.get('source_transactions', [])
        target = data.get('target_transactions', [])
        tolerance = data.get('tolerance_amount', 0.01)
        date_window = data.get('date_matching_window_days', 0)
        if not source or not target:
            return json.dumps({"error": "Both source_transactions and target_transactions are required"}, ensure_ascii=False)
        
        def parse_date(d):
            from datetime import datetime
            return datetime.strptime(d, '%Y-%m-%d')
        
        from datetime import timedelta
        matched_source_ids = set()
        matched_target_ids = set()
        matches = []
        mismatches_source = []
        mismatches_target = []
        
        for s in source:
            s_date = parse_date(s['date'])
            s_amount = s['amount']
            best_match = None
            best_diff = float('inf')
            for t in target:
                if t['id'] in matched_target_ids:
                    continue
                t_date = parse_date(t['date'])
                t_amount = t['amount']
                date_diff = abs((s_date - t_date).days)
                if date_diff > date_window:
                    continue
                amount_diff = abs(s_amount - t_amount)
                if amount_diff <= tolerance and amount_diff < best_diff:
                    best_diff = amount_diff
                    best_match = t
            if best_match:
                matched_source_ids.add(s['id'])
                matched_target_ids.add(best_match['id'])
                matches.append({
                    "source_id": s['id'],
                    "target_id": best_match['id'],
                    "amount_diff": round(best_diff, 2),
                    "date_diff_days": abs((parse_date(s['date']) - parse_date(best_match['date'])).days)
                })
            else:
                mismatches_source.append(s)
        
        for t in target:
            if t['id'] not in matched_target_ids:
                mismatches_target.append(t)
        
        result = {
            "summary": {
                "total_source": len(source),
                "total_target": len(target),
                "matched_count": len(matches),
                "unmatched_source_count": len(mismatches_source),
                "unmatched_target_count": len(mismatches_target),
                "matched_amount": round(sum(s['amount'] for s in source if s['id'] in matched_source_ids), 2),
                "unmatched_source_amount": round(sum(s['amount'] for s in mismatches_source), 2),
                "unmatched_target_amount": round(sum(t['amount'] for t in mismatches_target), 2)
            },
            "matches": matches,
            "unmatched_source_transactions": mismatches_source,
            "unmatched_target_transactions": mismatches_target
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "finance_reconciliation_report",
    "description": "Generate a reconciliation report comparing two sets of financial transactions (e.g., bank statement vs. internal ledger) to identify matching, missing, and mismatched entries, and return a summary of discrepancies with counts and total amounts.",
    "category": "system",
    "domain": "finance",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "source_transactions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "Unique transaction identifier from source system"
                    },
                    "date": {
                        "type": "string",
                        "description": "Transaction date in YYYY-MM-DD format"
                    },
                    "amount": {
                        "type": "number",
                        "description": "Transaction amount (positive for credit, negative for debit)"
                    },
                    "description": {
                        "type": "string",
                        "description": "Brief description of the transaction"
                    }
                },
                "required": [
                    "id",
                    "date",
                    "amount"
                ]
            },
            "description": "List of transactions from the primary source (e.g., internal ledger)"
        },
        "target_transactions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "Unique transaction identifier from target system"
                    },
                    "date": {
                        "type": "string",
                        "description": "Transaction date in YYYY-MM-DD format"
                    },
                    "amount": {
                        "type": "number",
                        "description": "Transaction amount (positive for credit, negative for debit)"
                    },
                    "description": {
                        "type": "string",
                        "description": "Brief description of the transaction"
                    }
                },
                "required": [
                    "id",
                    "date",
                    "amount"
                ]
            },
            "description": "List of transactions from the target system (e.g., bank statement)"
        },
        "tolerance_amount": {
            "type": "number",
            "description": "Optional: Maximum allowed difference in amounts (in absolute value) for a transaction to be considered a match. Default is 0.01.",
            "default": 0.01
        },
        "date_matching_window_days": {
            "type": "integer",
            "description": "Optional: Number of days tolerance for matching transaction dates (e.g., 1 allows +/-1 day). Default is 0 (exact match).",
            "default": 0
        }
    },
    "required": [
        "source_transactions",
        "target_transactions"
    ]
},
}
