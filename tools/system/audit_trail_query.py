"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    from datetime import datetime
    try:
        data = json.loads(payload)
        start = data.get('start_date')
        end = data.get('end_date')
        if not start or not end:
            return json.dumps({'error': 'start_date and end_date are required'})
        # Validate date format
        datetime.strptime(start, '%Y-%m-%d')
        datetime.strptime(end, '%Y-%m-%d')
        # Simulate audit log retrieval (in real system query a database)
        # Placeholder data generation
        audit_logs = [
            {'timestamp': '2024-06-15T10:30:00', 'user_id': 'u123', 'action': 'login', 'entity_type': 'user', 'entity_id': 'u123', 'details': 'User logged in'},
            {'timestamp': '2024-06-15T11:00:00', 'user_id': 'u456', 'action': 'transfer', 'entity_type': 'payment', 'entity_id': 't789', 'details': 'Payment transfer of amount 500.00'},
            {'timestamp': '2024-06-15T12:15:00', 'user_id': 'u123', 'action': 'update', 'entity_type': 'investment', 'entity_id': 'inv001', 'details': 'Updated investment allocation'}
        ]
        # Filter based on provided criteria (simplified)
        filtered = audit_logs
        if data.get('entity_type') and data['entity_type'] != 'all':
            filtered = [log for log in filtered if log['entity_type'] == data['entity_type']]
        if data.get('action_type') and data['action_type'] != 'all':
            filtered = [log for log in filtered if log['action'] == data['action_type']]
        if data.get('user_id'):
            filtered = [log for log in filtered if log['user_id'] == data['user_id']]
        return json.dumps({'audit_logs': filtered, 'count': len(filtered)}, ensure_ascii=False)
    except json.JSONDecodeError:
        return json.dumps({'error': 'Invalid JSON payload'})
    except ValueError:
        return json.dumps({'error': 'Invalid date format. Use YYYY-MM-DD.'})
    except Exception as e:
        return json.dumps({'error': f'Unexpected error: {str(e)}'})


TOOL_SPEC = {
    "name": "audit_trail_query",
    "description": "Retrieve audit trail entries for financial transactions or user actions by filtering on date range, entity type, action type, and user identifier. Returns a list of audit log records including timestamp, user, action, entity type, entity id, and details. Used for compliance reviews, forensic analysis, and monitoring system changes.",
    "category": "system",
    "domain": "finance",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "start_date": {
            "type": "string",
            "description": "Start of the date range for audit logs (ISO 8601 format, e.g., '2024-01-01')"
        },
        "end_date": {
            "type": "string",
            "description": "End of the date range for audit logs (ISO 8601 format, e.g., '2024-12-31')"
        },
        "entity_type": {
            "type": "string",
            "description": "Optional: Filter by the type of entity (e.g., 'payment', 'investment', 'user', 'account')",
            "enum": [
                "payment",
                "investment",
                "user",
                "account",
                "trade",
                "credit_card",
                "all"
            ]
        },
        "action_type": {
            "type": "string",
            "description": "Optional: Filter by the action performed (e.g., 'create', 'update', 'delete', 'login', 'transfer')",
            "enum": [
                "create",
                "update",
                "delete",
                "login",
                "transfer",
                "read",
                "all"
            ]
        },
        "user_id": {
            "type": "string",
            "description": "Optional: Filter by the user who performed the action (user identifier string)"
        }
    },
    "required": [
        "start_date",
        "end_date"
    ]
},
}
