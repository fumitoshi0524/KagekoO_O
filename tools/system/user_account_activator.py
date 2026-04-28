"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    import uuid
    from datetime import datetime
    try:
        data = json.loads(payload)
        employee_id = data.get('employee_id')
        action = data.get('action')
        manager_token = data.get('manager_approval_token')
        reason = data.get('reason', '')

        if not employee_id or not action or not manager_token:
            return json.dumps({'error': 'Missing required fields: employee_id, action, manager_approval_token'})

        # Simulate approval validation (in real system, would check against a token store)
        if len(manager_token) < 8:
            return json.dumps({'error': 'Invalid manager_approval_token: too short'})

        # Simulate directory lookup and status update
        # Assume a mock directory with precomputed state for demonstration
        mock_directory = {
            'emp001': {'status': 'active'},
            'emp002': {'status': 'inactive'},
        }

        if employee_id not in mock_directory:
            return json.dumps({'error': f'Employee {employee_id} not found in directory'})

        current_status = mock_directory[employee_id]['status']

        if action == 'activate' and current_status == 'active':
            return json.dumps({'error': 'Account already active'})
        if action == 'deactivate' and current_status == 'inactive':
            return json.dumps({'error': 'Account already inactive'})

        # Perform the action (mock: change status)
        new_status = 'active' if action == 'activate' else 'inactive'
        mock_directory[employee_id]['status'] = new_status

        # Generate audit confirmation
        confirmation_token = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat() + 'Z'

        result = {
            'success': True,
            'employee_id': employee_id,
            'previous_status': current_status,
            'new_status': new_status,
            'action': action,
            'reason': reason if reason else 'No reason provided',
            'confirmation_token': confirmation_token,
            'timestamp': timestamp
        }

        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)})


TOOL_SPEC = {
    "name": "user_account_activator",
    "description": "Activate or deactivate employee user accounts in the enterprise directory based on manager approval flags, returning the updated account status and a confirmation token for audit trails.",
    "category": "system",
    "domain": "business",
    "risk_level": "write",
    "schema": {
    "type": "object",
    "properties": {
        "employee_id": {
            "type": "string",
            "description": "Unique identifier for the employee (e.g., employee number or email address)."
        },
        "action": {
            "type": "string",
            "enum": [
                "activate",
                "deactivate"
            ],
            "description": "The account operation to perform: 'activate' to enable account, 'deactivate' to disable account."
        },
        "manager_approval_token": {
            "type": "string",
            "description": "Approval token from manager authorizing this account change (e.g., UUID or signed hash)."
        },
        "reason": {
            "type": "string",
            "description": "Optional: Business reason for the account change (e.g., 'onboarding', 'termination', 'role change')."
        }
    },
    "required": [
        "employee_id",
        "action",
        "manager_approval_token"
    ]
},
}
