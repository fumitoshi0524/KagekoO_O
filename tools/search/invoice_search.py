"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Search through issued and received invoices by date range, counterparty, amount, and status."""
    import json
    import random
    from datetime import datetime, timedelta
    try:
        data = json.loads(payload)
        query_type = data.get('query_type', '')
        keyword = data.get('keyword', '').strip()
        start_date = data.get('start_date', '')
        end_date = data.get('end_date', '')
        status_filter = data.get('status_filter', 'any')
        min_amount = data.get('min_amount')
        max_amount = data.get('max_amount')

        if query_type not in ['invoice_number', 'counterparty', 'date_range']:
            return json.dumps({'error': 'Invalid query_type. Must be invoice_number, counterparty, or date_range.'})

        if query_type in ['invoice_number', 'counterparty'] and not keyword or len(keyword) < 2:
            return json.dumps({'error': 'Keyword must be at least 2 characters for invoice_number or counterparty queries.'})

        if query_type == 'date_range':
            if not start_date or not end_date:
                return json.dumps({'error': 'Both start_date and end_date are required for date_range query.'})
            try:
                datetime.strptime(start_date, '%Y-%m-%d')
                datetime.strptime(end_date, '%Y-%m-%d')
            except ValueError:
                return json.dumps({'error': 'Dates must be in YYYY-MM-DD format.'})
            if start_date > end_date:
                return json.dumps({'error': 'start_date must not be after end_date.'})

        # Simulate invoice database (in production, this would query an actual database or API)
        sample_invoices = [
            {'invoice_number': 'INV-2024-001', 'counterparty': 'Acme Corp', 'issue_date': '2024-01-15', 'due_date': '2024-02-14', 'amount': 1500.00, 'status': 'paid'},
            {'invoice_number': 'INV-2024-002', 'counterparty': 'Globex Inc', 'issue_date': '2024-02-20', 'due_date': '2024-03-21', 'amount': 2750.50, 'status': 'unpaid'},
            {'invoice_number': 'INV-2024-003', 'counterparty': 'Initech', 'issue_date': '2024-03-10', 'due_date': '2024-04-09', 'amount': 8200.00, 'status': 'overdue'},
            {'invoice_number': 'INV-2024-004', 'counterparty': 'Acme Corp', 'issue_date': '2024-04-05', 'due_date': '2024-05-04', 'amount': 650.75, 'status': 'paid'},
            {'invoice_number': 'INV-2024-005', 'counterparty': 'Hooli', 'issue_date': '2024-05-22', 'due_date': '2024-06-21', 'amount': 12000.00, 'status': 'cancelled'}
        ]

        results = []
        for inv in sample_invoices:
            query_match = False
            if query_type == 'invoice_number':
                if keyword.lower() in inv['invoice_number'].lower():
                    query_match = True
            elif query_type == 'counterparty':
                if keyword.lower() in inv['counterparty'].lower():
                    query_match = True
            elif query_type == 'date_range':
                if start_date <= inv['issue_date'] <= end_date:
                    query_match = True

            if not query_match:
                continue

            if status_filter != 'any' and inv['status'] != status_filter:
                continue

            if min_amount is not None and inv['amount'] < min_amount:
                continue
            if max_amount is not None and inv['amount'] > max_amount:
                continue

            results.append(inv)

        return json.dumps({
            'query_type': query_type,
            'total_matches': len(results),
            'invoices': results
        }, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "invoice_search",
    "description": "Search through issued and received invoices by date range, counterparty, amount, and status to quickly locate specific invoices for reconciliation, auditing, or payment tracking. Returns matching invoices with their metadata including invoice number, issue date, due date, counterparty, total amount, and current status.",
    "category": "search",
    "domain": "finance",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "query_type": {
            "type": "string",
            "description": "Type of search to perform: by invoice number, counterparty name, or custom date range",
            "enum": [
                "invoice_number",
                "counterparty",
                "date_range"
            ]
        },
        "keyword": {
            "type": "string",
            "description": "Search keyword for invoice_number or counterparty queries. Must be at least 2 characters."
        },
        "start_date": {
            "type": "string",
            "description": "Optional: Start of date range in YYYY-MM-DD format. Used only when query_type is date_range."
        },
        "end_date": {
            "type": "string",
            "description": "Optional: End of date range in YYYY-MM-DD format. Used only when query_type is date_range."
        },
        "status_filter": {
            "type": "string",
            "description": "Optional: Filter invoices by their current status",
            "enum": [
                "paid",
                "unpaid",
                "overdue",
                "cancelled",
                "any"
            ]
        },
        "min_amount": {
            "type": "number",
            "description": "Optional: Minimum invoice amount in the base currency (e.g., USD). Filters for invoices greater than or equal to this value."
        },
        "max_amount": {
            "type": "number",
            "description": "Optional: Maximum invoice amount in the base currency (e.g., USD). Filters for invoices less than or equal to this value."
        }
    },
    "required": [
        "query_type"
    ]
},
}
