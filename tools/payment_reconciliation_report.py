"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        account_id = data.get('account_id')
        if not start_date or not end_date or not account_id:
            return json.dumps({'error': 'Missing required fields: start_date, end_date, account_id'}, ensure_ascii=False)
        threshold = data.get('threshold_amount', 0.01)
        include_disputes = data.get('include_disputes', False)
        # Simulated internal transactions
        internal_txns = [
            {'id': 'TXN001', 'date': '2025-03-01', 'amount': 1500.00, 'description': 'Invoice INV-1001'},
            {'id': 'TXN002', 'date': '2025-03-02', 'amount': 2345.50, 'description': 'Invoice INV-1002'},
            {'id': 'TXN003', 'date': '2025-03-03', 'amount': 89.99, 'description': 'Refund R-202'},
            {'id': 'TXN004', 'date': '2025-03-04', 'amount': 500.00, 'description': 'Invoice INV-1003'}
        ]
        # Simulated bank statements
        bank_txns = [
            {'id': 'BANK-A100', 'date': '2025-03-01', 'amount': 1500.00, 'reference': 'INV-1001'},
            {'id': 'BANK-A101', 'date': '2025-03-02', 'amount': 2345.50, 'reference': 'INV-1002'},
            {'id': 'BANK-A102', 'date': '2025-03-05', 'amount': 89.99, 'reference': 'R-202'},
            {'id': 'BANK-A103', 'date': '2025-03-06', 'amount': 600.00, 'reference': 'INV-1003'}
        ]
        matched = []
        unmatched_internal = []
        unmatched_bank = []
        disputed = []
        # Basic matching logic: compare amounts within threshold (ignoring reference alignment for simplicity)
        used_bank_ids = set()
        for inv in internal_txns:
            found = False
            for bank in bank_txns:
                if bank['id'] in used_bank_ids:
                    continue
                if abs(inv['amount'] - bank['amount']) <= threshold:
                    matched.append({'internal_id': inv['id'], 'bank_id': bank['id'], 'amount': inv['amount'], 'diff': round(inv['amount'] - bank['amount'], 2)})
                    used_bank_ids.add(bank['id'])
                    found = True
                    break
            if not found:
                unmatched_internal.append(inv)
        for bank in bank_txns:
            if bank['id'] not in used_bank_ids:
                unmatched_bank.append(bank)
        if include_disputes:
            # Simulated disputed transactions
            disputed = [
                {'internal_id': 'TXN003', 'bank_id': 'BANK-A102', 'reason': 'Date mismatch', 'status': 'open'}
            ]
        result = {
            'account_id': account_id,
            'period': {'start': start_date, 'end': end_date},
            'summary': {
                'total_internal': len(internal_txns),
                'total_bank': len(bank_txns),
                'matched_count': len(matched),
                'unmatched_internal_count': len(unmatched_internal),
                'unmatched_bank_count': len(unmatched_bank),
                'disputed_count': len(disputed)
            },
            'matched_payments': matched,
            'unmatched_internal_payments': unmatched_internal,
            'unmatched_bank_payments': unmatched_bank,
            'disputed_payments': disputed
        }
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({'error': f'Failed to generate report: {str(e)}'}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "payment_reconciliation_report",
    "description": "Generate a payment reconciliation report comparing internal transaction records with external bank statements for a given date range. Returns matched, unmatched, and disputed payments with status summaries for finance audit teams.",
    "category": "system",
    "domain": "finance",
    "risk_level": "elevated",
    "schema": {
    "type": "object",
    "properties": {
        "start_date": {
            "type": "string",
            "format": "date",
            "description": "Start date of the reconciliation period in YYYY-MM-DD format."
        },
        "end_date": {
            "type": "string",
            "format": "date",
            "description": "End date of the reconciliation period in YYYY-MM-DD format."
        },
        "account_id": {
            "type": "string",
            "description": "Unique identifier for the bank account to reconcile (e.g., account number or IBAN)."
        },
        "threshold_amount": {
            "type": "number",
            "description": "Optional: Maximum absolute difference in amount (in base currency units) allowed for a transaction to be considered matched. Default is 0.01.",
            "minimum": 0
        },
        "include_disputes": {
            "type": "boolean",
            "description": "Optional: If true, include transactions flagged as disputed in the report. Default is false."
        }
    },
    "required": [
        "start_date",
        "end_date",
        "account_id"
    ]
},
}
