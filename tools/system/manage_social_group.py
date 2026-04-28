"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Manage social groups: create, update, or delete a group in a social platform."""
    import json
    try:
        data = json.loads(payload)
        action = data.get('action')
        if action not in ('create', 'update', 'delete'):
            return 'error: action must be create, update, or delete'
        
        # Simulate group management
        if action == 'create':
            if 'name' not in data:
                return 'error: name is required for create'
            group_id = 'grp_' + str(hash(data['name']))[:8]
            result = {
                'status': 'created',
                'group_id': group_id,
                'name': data['name'],
                'description': data.get('description', ''),
                'visibility': data.get('visibility', 'public'),
                'members': data.get('members', [])
            }
        elif action == 'update':
            if 'group_id' not in data:
                return 'error: group_id is required for update'
            result = {
                'status': 'updated',
                'group_id': data['group_id'],
                'name': data.get('name', ''),
                'description': data.get('description', ''),
                'visibility': data.get('visibility', 'public')
            }
        else:  # delete
            if 'group_id' not in data:
                return 'error: group_id is required for delete'
            result = {
                'status': 'deleted',
                'group_id': data['group_id']
            }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "manage_social_group",
    "description": "Create, update, or delete a social group (e.g., a team, club, or community circle) in a social platform, including setting its name, description, visibility, and member list, and return the final group configuration or confirmation status.",
    "category": "system",
    "domain": "social",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "description": "Operation to perform: create, update, or delete the group.",
            "enum": [
                "create",
                "update",
                "delete"
            ]
        },
        "group_id": {
            "type": "string",
            "description": "Unique identifier of the group. Required for update and delete actions."
        },
        "name": {
            "type": "string",
            "description": "Display name for the group (1-100 characters). Required for create and update actions."
        },
        "description": {
            "type": "string",
            "description": "Optional: Free-text description of the group purpose or rules (max 500 characters)."
        },
        "visibility": {
            "type": "string",
            "description": "Optional: Who can see or find the group. Default is 'public'.",
            "enum": [
                "public",
                "private",
                "hidden"
            ]
        },
        "members": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "Optional: List of member usernames or user IDs to add to the group upon creation. Ignored for delete."
        }
    },
    "required": [
        "action"
    ]
},
}
