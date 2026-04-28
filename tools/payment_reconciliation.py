"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        batch = data.get("batch_payments", [])
        expected = data.get("expected_transactions", [])
        tolerance = data.get("tolerance", 0)
        if not batch or not expected:
            return json.dumps({"error": "Both batch_payments and expected_transactions are required"})
        matched = []
        unmatched_batch = list(batch)
        unmatched_expected = list(expected)
        for bp in batch:
            for i, et in enumerate(unmatched_expected):
                if abs(bp["amount"] - et["amount"]) <= tolerance and bp["currency"] == et["currency"]:
                    matched.append({"payment_id": bp["payment_id"], "transaction_id": et["transaction_id"]})
                    unmatched_batch = [x for x in unmatched_batch if x["payment_id"] != bp["payment_id"]]
                    unmatched_expected.pop(i)
                    break
        report = {
            "total_batch": len(batch),
            "total_expected": len(expected),
            "matched": matched,
            "matched_count": len(matched),
            "missing_payments": unmatched_expected,
            "missing_payments_count": len(unmatched_expected),
            "duplicate_payments": unmatched_batch,
            "duplicate_payments_count": len(unmatched_batch)
        }
        return json.dumps(report, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "payment_reconciliation",
    "description": "Reconciles batch payment records against expected transactions to identify matched, missing, and duplicate entries. Operates on payment records and transaction databases, returning a reconciliation report with counts and lists of discrepancies for finance teams.",
    "category": "system",
    "domain": "finance",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "batch_payments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "payment_id": {
                        "type": "string",
                        "description": "Unique identifier for the payment"
                    },
                    "amount": {
                        "type": "number",
                        "description": "Transaction amount"
                    },
                    "currency": {
                        "type": "string",
                        "description": "ISO 4217 currency code"
                    }
                },
                "required": [
                    "payment_id",
                    "amount",
                    "currency"
                ]
            },
            "description": "List of actual payment records received"
        },
        "expected_transactions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "transaction_id": {
                        "type": "string",
                        "description": "Unique identifier for the expected transaction"
                    },
                    "amount": {
                        "type": "number",
                        "description": "Expected transaction amount"
                    },
                    "currency": {
                        "type": "string",
                        "description": "ISO 4217 currency code"
                    }
                },
                "required": [
                    "transaction_id",
                    "amount",
                    "currency"
                ]
            },
            "description": "List of expected transactions from the system"
        },
        "tolerance": {
            "type": "number",
            "description": "Optional: Amount tolerance in smallest currency unit (e.g., cents) for matching amounts"
        }
    },
    "required": [
        "batch_payments",
        "expected_transactions"
    ]
},
}
