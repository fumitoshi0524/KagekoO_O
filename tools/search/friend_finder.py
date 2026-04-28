"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Search for people in a social network by name, location, or mutual interests."""
    import json
    try:
        data = json.loads(payload)
        name = data.get('name')
        if not name:
            return json.dumps({'error': 'Missing required parameter: name'})
        location = data.get('location', '')
        interests = data.get('interests', [])
        max_results = min(data.get('max_results', 10), 100)
        
        # Simulated social network user database
        users_db = [
            {"id": 1, "name": "Alice Johnson", "location": "New York", "interests": ["hiking", "photography"], "email": "alice@example.com"},
            {"id": 2, "name": "Bob Smith", "location": "Los Angeles", "interests": ["jazz", "cooking"], "email": "bob@example.com"},
            {"id": 3, "name": "Carol White", "location": "Chicago", "interests": ["photography", "yoga"], "email": "carol@example.com"},
            {"id": 4, "name": "David Brown", "location": "New York", "interests": ["hiking", "reading"], "email": "david@example.com"}
        ]
        
        results = []
        for user in users_db:
            # Check name match (case-insensitive substring)
            if name.lower() not in user['name'].lower():
                continue
            # Check location (if provided)
            if location and location.lower() not in user['location'].lower():
                continue
            # Check interests overlap (if provided)
            if interests:
                match_found = False
                for interest in interests:
                    if interest.lower() in [i.lower() for i in user['interests']]:
                        match_found = True
                        break
                if not match_found:
                    continue
            results.append(user)
            if len(results) >= max_results:
                break
        
        return json.dumps({'matches': results, 'total_found': len(results)}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)})


TOOL_SPEC = {
    "name": "friend_finder",
    "description": "Search for people in a social network by name, location, or mutual interests, returning a ranked list of matching profiles with contact and connection details.",
    "category": "search",
    "domain": "social",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "name": {
            "type": "string",
            "description": "Full or partial name of the person to search for (case-insensitive)."
        },
        "location": {
            "type": "string",
            "description": "Optional: City, region, or postal code to filter results by geographic proximity."
        },
        "interests": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "Optional: List of interest tags (e.g., hiking, photography, jazz) to match against profile interests. At least one must match for inclusion."
        },
        "max_results": {
            "type": "integer",
            "description": "Optional: Maximum number of results to return (default 10, max 100)."
        }
    },
    "required": [
        "name"
    ]
},
}
