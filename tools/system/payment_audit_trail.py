"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Retrieve a chronological audit trail of payment transactions for a given account or business entity, returning filtered records by date range and status for compliance review and reconciliation."""
    import json
    from datetime import datetime, timedelta
    import hashlib
    import random

    try:
        data = json.loads(payload)
        account_id = data.get('account_id')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        status_filter = data.get('status_filter', 'all')
        max_records = data.get('max_records', 100)

        if not account_id or not start_date or not end_date:
            return json.dumps({'error': 'Missing required fields: account_id, start_date, end_date'}, ensure_ascii=False)

        # Validate date format
        try:
            datetime.strptime(start_date, '%Y-%m-%d')
            datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            return json.dumps({'error': 'Invalid date format. Use YYYY-MM-DD'}, ensure_ascii=False)

        if status_filter not in ['pending', 'completed', 'failed', 'refunded', 'all']:
            return json.dumps({'error': 'Invalid status_filter. Must be one of: pending, completed, failed, refunded, all'}, ensure_ascii=False)

        # Simulate audit trail generation (in production, query payment database)
        statuses = ['pending', 'completed', 'failed', 'refunded']
        transactions = []
        base_time = datetime.strptime(start_date, '%Y-%m-%d')
        end_time = datetime.strptime(end_date, '%Y-%m-%d')
        total_days = (end_time - base_time).days

        if total_days < 0:
            return json.dumps({'error': 'end_date must be after start_date'}, ensure_ascii=False)

        # Generate representative transaction records
        for i in range(min(max_records, 200)):
            tx_date = base_time + timedelta(days=random.randint(0, max(0, total_days)), hours=random.randint(0, 23), minutes=random.randint(0, 59))
            amount = round(random.uniform(10.0, 5000.0), 2)
            status = random.choice(statuses)
            if status_filter != 'all' and status != status_filter:
                continue
            tx_id = hashlib.sha256(f'{account_id}{i}{tx_date.isoformat()}'.encode()).hexdigest()[:12]
            transactions.append({
                'transaction_id': tx_id,
                'account_id': account_id,
                'amount': amount,
                'currency': 'USD',
                'status': status,
                'timestamp': tx_date.isoformat(),
                'description': f'Payment transaction {i+1}'
            })

        # Sort by timestamp
        transactions.sort(key=lambda x: x['timestamp'])

        result = {
            'account_id': account_id,
            'start_date': start_date,
            'end_date': end_date,
            'total_records': len(transactions),
            'status_filter_applied': status_filter,
            'transactions': transactions[:max_records],
            'generated_at': datetime.utcnow().isoformat()
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': f'Processing failed: {str(e)}'}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "payment_audit_trail",
    "description": "Retrieve a chronological audit trail of payment transactions for a given account or business entity, returning filtered records by date range and status for compliance review and reconciliation.",
    "category": "system",
    "domain": "finance",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "account_id": {
            "type": "string",
            "description": "Unique identifier of the account or business entity to audit"
        },
        "start_date": {
            "type": "string",
            "description": "Start date for filtering transactions in YYYY-MM-DD format"
        },
        "end_date": {
            "type": "string",
            "description": "End date for filtering transactions in YYYY-MM-DD format"
        },
        "status_filter": {
            "type": "string",
            "description": "Optional: Filter by payment status; one of: pending, completed, failed, refunded, all",
            "enum": [
                "pending",
                "completed",
                "failed",
                "refunded",
                "all"
            ]
        },
        "max_records": {
            "type": "integer",
            "description": "Optional: Maximum number of audit records to return (default 100, max 1000)",
            "minimum": 1,
            "maximum": 1000
        }
    },
    "required": [
        "account_id",
        "start_date",
        "end_date"
    ]
},
}
