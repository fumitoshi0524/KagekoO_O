"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Find mutual contacts (shared connections) among specified users."""
    import json
    try:
        data = json.loads(payload)
        user_ids = data.get('user_ids')
        if not user_ids or len(user_ids) < 2:
            return json.dumps({'error': 'At least 2 user IDs are required'})
        min_mutual = data.get('min_mutual_connections', 1)
        include_summary = data.get('include_profile_summary', False)
        
        # Simulate a social graph stored in memory (in production this would query a database)
        # Each user has a list of contact IDs
        mock_contacts = {
            'user_001': ['contact_a', 'contact_b', 'contact_c', 'contact_d'],
            'user_002': ['contact_b', 'contact_d', 'contact_e'],
            'user_003': ['contact_c', 'contact_d', 'contact_f'],
            'user_004': ['contact_a', 'contact_d', 'contact_g'],
            'user_005': ['contact_b', 'contact_d', 'contact_h'],
        }
        
        # Gather contacts for each requested user (if user not found, treat them as having no contacts)
        users_contacts = []
        for uid in user_ids:
            contacts = mock_contacts.get(uid, [])
            users_contacts.append(set(contacts))
        
        if not users_contacts:
            return json.dumps({'mutual_contacts': [], 'count': 0})
        
        # Compute intersection of all contact sets
        common = set.intersection(*users_contacts)
        
        # Filter by minimum mutual connections (here all from intersection are shared by all users)
        mutual_list = sorted(common)
        
        # If include_summary, add mock profiles
        results = []
        for cid in mutual_list:
            item = {'contact_id': cid}
            if include_summary:
                item['profile'] = {
                    'name': f'Contact {cid}',
                    'headline': f'Professional at company for {cid}',
                    'location': 'Remote'
                }
            results.append(item)
        
        return json.dumps({'mutual_contacts': results, 'count': len(results)}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)})



TOOL_SPEC = {
    "name": "find_common_contacts",
    "description": "Finds people or organizations that are connected to multiple specified users in a social network. Given a list of user IDs, returns the intersection of their contact lists — useful for discovering mutual acquaintances, shared collaborators, or overlapping community members.",
    "category": "search",
    "domain": "social",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "user_ids": {
            "type": "array",
            "items": {
                "type": "string",
                "description": "Unique user identifier (e.g., 'user_12345')"
            },
            "minItems": 2,
            "maxItems": 100,
            "description": "Array of at least 2 user IDs whose contacts will be intersected"
        },
        "min_mutual_connections": {
            "type": "integer",
            "minimum": 1,
            "default": 1,
            "description": "Optional: Minimum number of users from the input list that must share a contact for it to appear in results (default: 1, meaning at least 2 users share the contact)"
        },
        "include_profile_summary": {
            "type": "boolean",
            "default": false,
            "description": "Optional: If true, include a brief profile summary (name, headline, location) for each mutual contact"
        }
    },
    "required": [
        "user_ids"
    ]
},
}
