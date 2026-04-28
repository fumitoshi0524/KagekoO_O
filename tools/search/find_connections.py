"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Search for mutual connections between two users in a social network."""
    import json
    try:
        data = json.loads(payload)
        user_a = data.get('user_id_a')
        user_b = data.get('user_id_b')
        max_depth = data.get('max_depth', 2)
        relationship_filter = data.get('include_relationship_types', None)
        
        if not user_a or not user_b:
            return json.dumps({'error': 'Both user_id_a and user_id_b are required'})
        
        # Simulated social graph database
        social_graph = {
            'user_001': {'connections': [('user_002', 'friend'), ('user_003', 'colleague'), ('user_004', 'follower')]},
            'user_002': {'connections': [('user_001', 'friend'), ('user_003', 'friend'), ('user_005', 'family')]},
            'user_003': {'connections': [('user_001', 'colleague'), ('user_002', 'friend'), ('user_004', 'classmate')]},
            'user_004': {'connections': [('user_001', 'follower'), ('user_003', 'classmate')]},
            'user_005': {'connections': [('user_002', 'family')]}
        }
        
        def bfs_connections(start_user, target_user, graph, max_depth):
            visited = {start_user}
            queue = [(start_user, 0)]
            mutual_connections = []
            
            while queue:
                current, depth = queue.pop(0)
                if depth >= max_depth:
                    continue
                    
                for neighbor, rel_type in graph.get(current, {}).get('connections', []):
                    if neighbor == target_user:
                        mutual_connections.append((current, rel_type))
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append((neighbor, depth + 1))
            
            return mutual_connections
        
        # Find mutual connections from user_a perspective
        mutual = bfs_connections(user_a, user_b, social_graph, max_depth)
        
        # Apply relationship filter if specified
        if relationship_filter:
            mutual = [conn for conn in mutual if conn[1].lower() in [r.lower() for r in relationship_filter]]
        
        # Calculate proximity score (higher = closer connection)
        connections_detail = []
        for connector_user, relationship in mutual:
            proximity_score = 1.0 - (len(connector_user) / 10)  # Simple scoring based on user_id length
            connections_detail.append({
                'connector_user': connector_user,
                'relationship_type': relationship,
                'proximity_score': round(proximity_score, 2)
            })
        
        # Sort by proximity score descending
        connections_detail.sort(key=lambda x: x['proximity_score'], reverse=True)
        
        result = {
            'user_a': user_a,
            'user_b': user_b,
            'mutual_connections': connections_detail,
            'total_mutual': len(connections_detail),
            'relationship_summary': 'Direct' if any(c['proximity_score'] > 0.8 for c in connections_detail) else 'Indirect'
        }
        
        return json.dumps(result, ensure_ascii=False)
        
    except json.JSONDecodeError as e:
        return json.dumps({'error': f'Invalid JSON payload: {str(e)}'})
    except KeyError as e:
        return json.dumps({'error': f'Missing key in social graph: {str(e)}'})
    except Exception as e:
        return json.dumps({'error': f'Unexpected error: {str(e)}'})


TOOL_SPEC = {
    "name": "find_connections",
    "description": "Search through a social network to find mutual connections between two users, returning a list of common contacts and their relationship proximity score.",
    "category": "search",
    "domain": "social",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "user_id_a": {
            "type": "string",
            "description": "Unique identifier of the first user in the social network"
        },
        "user_id_b": {
            "type": "string",
            "description": "Unique identifier of the second user in the social network"
        },
        "max_depth": {
            "type": "integer",
            "description": "Optional: Maximum degrees of separation to search (default: 2, range: 1-5)",
            "default": 2
        },
        "include_relationship_types": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [
                    "friend",
                    "follower",
                    "colleague",
                    "family",
                    "classmate"
                ]
            },
            "description": "Optional: Filter results to only include specific relationship types"
        }
    },
    "required": [
        "user_id_a",
        "user_id_b"
    ]
},
}
