"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        community_id = data.get('community_id')
        member_id = data.get('member_id')
        role = data.get('role')
        action = data.get('action')
        if not all([community_id, member_id, role, action]):
            return json.dumps({'error': 'Missing required fields'}, ensure_ascii=False)
        valid_roles = ['admin', 'moderator', 'member', 'guest']
        if role not in valid_roles:
            return json.dumps({'error': f'Invalid role: {role}'}, ensure_ascii=False)
        valid_actions = ['assign', 'remove']
        if action not in valid_actions:
            return json.dumps({'error': f'Invalid action: {action}'}, ensure_ascii=False)
        # Simulate role assignment logic
        result = {
            'community_id': community_id,
            'member_id': member_id,
            'role': role,
            'action': action,
            'status': 'success'
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "community_role_assigner",
    "description": "Assign or remove a role to/from a member in a community group based on member ID and role name; returns the updated membership status.",
    "category": "system",
    "domain": "social",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "community_id": {
            "type": "string",
            "description": "Unique identifier for the community group"
        },
        "member_id": {
            "type": "string",
            "description": "Unique identifier for the community member"
        },
        "role": {
            "type": "string",
            "description": "Role name to assign or remove",
            "enum": [
                "admin",
                "moderator",
                "member",
                "guest"
            ]
        },
        "action": {
            "type": "string",
            "description": "Action to perform on the role",
            "enum": [
                "assign",
                "remove"
            ]
        }
    },
    "required": [
        "community_id",
        "member_id",
        "role",
        "action"
    ]
},
}
