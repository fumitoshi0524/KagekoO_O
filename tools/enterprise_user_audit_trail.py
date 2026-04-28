"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Query and retrieve a chronological audit trail of user activity within an enterprise system."""
    import json
    from datetime import datetime, timedelta
    try:
        data = json.loads(payload)
        user_id = data.get('user_id')
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        action_type = data.get('action_type')
        if not user_id or not start_date_str:
            return json.dumps({'error': 'user_id and start_date are required'}, ensure_ascii=False)
        start_date = datetime.fromisoformat(start_date_str)
        if end_date_str:
            end_date = datetime.fromisoformat(end_date_str)
        else:
            end_date = datetime.now()
        # Simulate audit records from a database (in production, query real DB)
        audit_records = [
            {
                'timestamp': (start_date + timedelta(days=1)).isoformat(),
                'user_id': user_id,
                'action': 'role_change',
                'details': 'Changed from Viewer to Editor',
                'actor': 'admin@company.com'
            },
            {
                'timestamp': (start_date + timedelta(days=3)).isoformat(),
                'user_id': user_id,
                'action': 'permission_modify',
                'details': 'Granted access to Finance reports',
                'actor': 'admin@company.com'
            },
            {
                'timestamp': (start_date + timedelta(days=5)).isoformat(),
                'user_id': user_id,
                'action': 'login',
                'details': 'Login from IP 192.168.1.100',
                'actor': user_id
            }
        ]
        # Filter by date range
        filtered = [r for r in audit_records if start_date <= datetime.fromisoformat(r['timestamp']) <= end_date]
        # Filter by action type if provided
        if action_type:
            filtered = [r for r in filtered if r['action'] == action_type]
        # Sort by timestamp descending
        filtered.sort(key=lambda x: x['timestamp'], reverse=True)
        result = {
            'user_id': user_id,
            'record_count': len(filtered),
            'audit_records': filtered
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "enterprise_user_audit_trail",
    "description": "Query and retrieve a chronological audit trail of user activity within an enterprise system, including role changes, permissions modifications, and account status transitions, returning a list of audit records with timestamps, user identifiers, and action details for compliance and security monitoring.",
    "category": "system",
    "domain": "business",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "user_id": {
            "type": "string",
            "description": "The unique identifier of the user for whom audit records are requested."
        },
        "start_date": {
            "type": "string",
            "description": "ISO 8601 formatted date (e.g., 2023-01-01) to filter audit records from this date onward."
        },
        "end_date": {
            "type": "string",
            "description": "Optional: ISO 8601 formatted date (e.g., 2023-12-31) to filter audit records up to this date."
        },
        "action_type": {
            "type": "string",
            "description": "Optional: Filter by specific action type. Allowed values: role_change, permission_modify, account_activate, account_deactivate, login, logout",
            "enum": [
                "role_change",
                "permission_modify",
                "account_activate",
                "account_deactivate",
                "login",
                "logout"
            ]
        }
    },
    "required": [
        "user_id",
        "start_date"
    ]
},
}
