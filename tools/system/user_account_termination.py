"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        account_ids = data.get('account_ids')
        reason = data.get('reason')
        permanent_delete = data.get('permanent_delete', False)
        notify_user = data.get('notify_user', False)

        if not account_ids or not isinstance(account_ids, list) or len(account_ids) == 0:
            return json.dumps({'error': 'account_ids must be a non-empty list of string identifiers'}, ensure_ascii=False)
        if not reason or not isinstance(reason, str):
            return json.dumps({'error': 'reason must be a non-empty string'}, ensure_ascii=False)

        terminated = []
        errors = []
        for aid in account_ids:
            if not isinstance(aid, str) or len(aid.strip()) == 0:
                errors.append({'account_id': aid, 'error': 'Invalid account identifier'})
                continue
            # Simulate account termination logic
            # In a real implementation, this would query the database and perform deactivation/deletion
            terminated.append({
                'account_id': aid,
                'status': 'terminated',
                'permanent_delete': permanent_delete,
                'notify_user': notify_user,
                'reason': reason,
                'terminated_at': '2025-04-11T12:00:00Z'
            })

        result = {
            'terminated_accounts': terminated,
            'errors': errors,
            'total_terminated': len(terminated),
            'total_errors': len(errors)
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "user_account_termination",
    "description": "Permanently deactivate and remove an educational user account (student, instructor, or administrator) from the learning management system, including all associated enrollments, progress data, and permission records, and return a confirmation of the terminated accounts.",
    "category": "system",
    "domain": "education",
    "risk_level": "write",
    "schema": {
    "type": "object",
    "properties": {
        "account_ids": {
            "type": "array",
            "items": {
                "type": "string",
                "description": "Unique identifier string for the user account to be terminated (e.g., user ID, email, or student number)"
            },
            "description": "List of one or more user account identifiers to terminate"
        },
        "reason": {
            "type": "string",
            "description": "Reason for termination (e.g., graduation, withdrawal, violation of policy)"
        },
        "permanent_delete": {
            "type": "boolean",
            "description": "Optional: If True, permanently delete all user data (irreversible). Default is False (accounts are deactivated but retained for audit)."
        },
        "notify_user": {
            "type": "boolean",
            "description": "Optional: If True, send a termination notification email to the affected user(s). Default is False."
        }
    },
    "required": [
        "account_ids",
        "reason"
    ]
},
}
