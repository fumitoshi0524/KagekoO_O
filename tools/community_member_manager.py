"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Manage community members by adding, removing, updating, or listing members."""
    import json
    try:
        data = json.loads(payload)
        action = data.get('action')
        community_id = data.get('community_id')
        member_id = data.get('member_id')
        
        if action not in ['add', 'remove', 'update', 'list']:
            return json.dumps({'error': 'Invalid action. Must be add, remove, update, or list.'})
        
        # Simulate a simple in-memory store (replace with DB in production)
        if not hasattr(run, 'members'):
            run.members = {}
        
        if community_id not in run.members:
            run.members[community_id] = {}
        
        community_members = run.members[community_id]
        
        if action == 'add':
            if member_id in community_members:
                return json.dumps({'error': 'Member already exists in community.'})
            member_name = data.get('member_name', f'User_{member_id}')
            role = data.get('role', 'member')
            status = data.get('status', 'active')
            community_members[member_id] = {
                'member_id': member_id,
                'member_name': member_name,
                'role': role,
                'status': status
            }
            summary = {'total_members': len(community_members), 'member_added': member_id}
            return json.dumps({'members': community_members, 'summary': summary}, ensure_ascii=False)
        
        elif action == 'remove':
            if member_id not in community_members:
                return json.dumps({'error': 'Member not found in community.'})
            del community_members[member_id]
            summary = {'total_members': len(community_members), 'member_removed': member_id}
            return json.dumps({'members': community_members, 'summary': summary}, ensure_ascii=False)
        
        elif action == 'update':
            if member_id not in community_members:
                return json.dumps({'error': 'Member not found in community.'})
            if 'member_name' in data:
                community_members[member_id]['member_name'] = data['member_name']
            if 'role' in data:
                community_members[member_id]['role'] = data['role']
            if 'status' in data:
                community_members[member_id]['status'] = data['status']
            summary = {'total_members': len(community_members), 'member_updated': member_id}
            return json.dumps({'members': community_members, 'summary': summary}, ensure_ascii=False)
        
        elif action == 'list':
            # Compute summary statistics
            total = len(community_members)
            roles = {}
            statuses = {}
            for m in community_members.values():
                roles[m['role']] = roles.get(m['role'], 0) + 1
                statuses[m['status']] = statuses.get(m['status'], 0) + 1
            summary = {
                'total_members': total,
                'roles': roles,
                'statuses': statuses
            }
            return json.dumps({'members': community_members, 'summary': summary}, ensure_ascii=False)
        
        return json.dumps({'error': 'Unknown error.'})
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "community_member_manager",
    "description": "Manage community members by adding, removing, or updating member roles, profiles, and statuses within a social group or organization, returning the updated member list and summary statistics.",
    "category": "system",
    "domain": "social",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": [
                "add",
                "remove",
                "update",
                "list"
            ],
            "description": "The operation to perform on community members."
        },
        "community_id": {
            "type": "string",
            "description": "Unique identifier for the community (e.g., group, organization, or channel)."
        },
        "member_id": {
            "type": "string",
            "description": "Unique identifier for the member being operated on."
        },
        "member_name": {
            "type": "string",
            "description": "Optional: Display name for the member when adding or updating."
        },
        "role": {
            "type": "string",
            "enum": [
                "admin",
                "moderator",
                "member",
                "viewer"
            ],
            "description": "Optional: Role to assign to the member."
        },
        "status": {
            "type": "string",
            "enum": [
                "active",
                "inactive",
                "banned",
                "pending"
            ],
            "description": "Optional: Status to set for the member."
        }
    },
    "required": [
        "action",
        "community_id",
        "member_id"
    ]
},
}
