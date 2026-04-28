"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        action = data.get('action')
        if action not in ['create', 'update', 'suspend', 'delete', 'list']:
            return 'error: invalid action'
        # In-memory user store (simulated)
        users = [
            {'username': 'dr_smith', 'role': 'doctor', 'department': 'cardiology', 'active': True},
            {'username': 'nurse_jones', 'role': 'nurse', 'department': 'emergency', 'active': True},
            {'username': 'patient_doe', 'role': 'patient', 'department': '', 'active': True}
        ]
        if action == 'list':
            department = data.get('department', None)
            role = data.get('role', None)
            result = users
            if department:
                result = [u for u in result if u.get('department') == department]
            if role:
                result = [u for u in result if u.get('role') == role]
            return json.dumps(result, ensure_ascii=False)
        else:
            username = data.get('username')
            if not username:
                return 'error: username required'
            if action == 'create':
                role = data.get('role')
                if not role:
                    return 'error: role required for create'
                new_user = {
                    'username': username,
                    'role': role,
                    'department': data.get('department', ''),
                    'active': True
                }
                users.append(new_user)
                return json.dumps({'status': 'created', 'user': new_user}, ensure_ascii=False)
            elif action == 'update':
                for u in users:
                    if u['username'] == username:
                        if 'role' in data:
                            u['role'] = data['role']
                        if 'department' in data:
                            u['department'] = data['department']
                        if 'active' in data:
                            u['active'] = data['active']
                        return json.dumps({'status': 'updated', 'user': u}, ensure_ascii=False)
                return 'error: user not found'
            elif action == 'suspend':
                for u in users:
                    if u['username'] == username:
                        u['active'] = False
                        return json.dumps({'status': 'suspended', 'user': u}, ensure_ascii=False)
                return 'error: user not found'
            elif action == 'delete':
                for i, u in enumerate(users):
                    if u['username'] == username:
                        deleted = users.pop(i)
                        return json.dumps({'status': 'deleted', 'user': deleted}, ensure_ascii=False)
                return 'error: user not found'
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "user_access_control",
    "description": "User access control tool for managing system authentication and authorization for healthcare staff and patients. Creates, updates, suspends, or deletes user accounts, assigns role-based permissions (e.g., doctor, nurse, admin, patient), and returns the current access status or a list of users filtered by role or department.",
    "category": "system",
    "domain": "healthcare",
    "risk_level": "write",
    "schema": {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "description": "Type of user access operation to perform: create, update, suspend, delete, or list.",
            "enum": [
                "create",
                "update",
                "suspend",
                "delete",
                "list"
            ]
        },
        "username": {
            "type": "string",
            "description": "Unique username for the healthcare system member. Required for all actions except list."
        },
        "role": {
            "type": "string",
            "description": "Role assigned to the user. Required for create and update. Options: doctor, nurse, patient, admin, technician.",
            "enum": [
                "doctor",
                "nurse",
                "patient",
                "admin",
                "technician"
            ]
        },
        "department": {
            "type": "string",
            "description": "Optional: Department or ward identifier (e.g., cardiology, emergency, pediatrics). Used for filtering when action=list."
        },
        "active": {
            "type": "boolean",
            "description": "Optional: Set account status. Default is True. Used with action=update or action=suspend."
        }
    },
    "required": [
        "action"
    ]
},
}
