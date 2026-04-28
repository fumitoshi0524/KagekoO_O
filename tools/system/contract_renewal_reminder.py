"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Check business contracts against their expiration dates and return a list of contracts expiring within a specified number of days, including contract ID, counterparty, renewal status, and days until expiry."""
    import json
    import datetime
    import random

    try:
        data = json.loads(payload)
        # Validate required inputs
        if 'lookahead_days' not in data or not isinstance(data['lookahead_days'], int):
            return json.dumps({'error': 'Missing or invalid required parameter: lookahead_days (must be integer)'}, ensure_ascii=False)
        lookahead_days = data['lookahead_days']
        if lookahead_days < 1 or lookahead_days > 365:
            return json.dumps({'error': 'lookahead_days must be between 1 and 365'}, ensure_ascii=False)

        # Validate optional parameters
        status_filter = data.get('status_filter')
        include_renewed = data.get('include_renewed', False)

        # Simulate a database of business contracts
        today = datetime.date.today()
        contracts = [
            {'contract_id': 'CNTR-2023-001', 'counterparty': 'Acme Corp', 'start_date': '2023-06-01', 'end_date': '2024-05-31', 'renewed': True, 'renewed_contract_id': 'CNTR-2024-001'},
            {'contract_id': 'CNTR-2023-002', 'counterparty': 'GlobalTech Ltd', 'start_date': '2023-01-15', 'end_date': '2023-12-31', 'renewed': False, 'renewed_contract_id': None},
            {'contract_id': 'CNTR-2024-001', 'counterparty': 'Acme Corp', 'start_date': '2024-06-01', 'end_date': '2025-05-31', 'renewed': False, 'renewed_contract_id': None},
            {'contract_id': 'CNTR-2024-002', 'counterparty': 'DataFlow Inc', 'start_date': '2024-03-01', 'end_date': '2026-02-28', 'renewed': False, 'renewed_contract_id': None},
            {'contract_id': 'CNTR-2024-003', 'counterparty': 'SupplyChain Pro', 'start_date': '2024-09-01', 'end_date': '2025-03-15', 'renewed': False, 'renewed_contract_id': None},
            {'contract_id': 'CNTR-2025-001', 'counterparty': 'FinanceHub', 'start_date': '2025-01-01', 'end_date': '2025-06-30', 'renewed': False, 'renewed_contract_id': None},
        ]

        result = []
        for contract in contracts:
            try:
                end_date = datetime.datetime.strptime(contract['end_date'], '%Y-%m-%d').date()
            except ValueError:
                continue

            days_to_expiry = (end_date - today).days
            if days_to_expiry < 0:
                status = 'expired'
            elif days_to_expiry <= lookahead_days:
                status = 'expiring_soon'
            else:
                status = 'active'

            if contract['renewed'] and not include_renewed:
                continue

            if status_filter and status != status_filter:
                continue

            result.append({
                'contract_id': contract['contract_id'],
                'counterparty': contract['counterparty'],
                'end_date': contract['end_date'],
                'days_to_expiry': days_to_expiry,
                'status': status,
                'renewed': contract['renewed']
            })

        # Sort by days_to_expiry ascending
        result.sort(key=lambda x: x['days_to_expiry'])

        return json.dumps({'expiring_contracts': result, 'total_count': len(result)}, ensure_ascii=False)

    except json.JSONDecodeError:
        return json.dumps({'error': 'Invalid JSON payload'}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "contract_renewal_reminder",
    "description": "Check business contracts against their expiration dates and return a list of contracts expiring within a specified number of days, including contract ID, counterparty, renewal status, and days until expiry.",
    "category": "system",
    "domain": "business",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "lookahead_days": {
            "type": "integer",
            "description": "Number of days into the future to check for expiring contracts. Must be between 1 and 365.",
            "examples": [
                30,
                60,
                90
            ]
        },
        "status_filter": {
            "type": "string",
            "description": "Optional: Filter contracts by current renewal status. Allowed values: active, expiring_soon, expired, renewed.",
            "enum": [
                "active",
                "expiring_soon",
                "expired",
                "renewed"
            ],
            "examples": [
                "expiring_soon"
            ]
        },
        "include_renewed": {
            "type": "boolean",
            "description": "Optional: If True, include contracts that have already been renewed. Default is False.",
            "examples": [
                True,
                False
            ]
        }
    },
    "required": [
        "lookahead_days"
    ]
},
}
