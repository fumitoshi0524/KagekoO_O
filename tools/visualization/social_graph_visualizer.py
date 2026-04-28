"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a social network graph visualization from contacts and relationships."""
    import json
    try:
        data = json.loads(payload)
        
        # Validate required inputs
        if 'contacts' not in data or 'relationships' not in data:
            return json.dumps({'error': 'Missing required fields: contacts and relationships'})
        
        contacts = data['contacts']
        relationships = data['relationships']
        
        if not isinstance(contacts, list) or len(contacts) == 0:
            return json.dumps({'error': 'contacts must be a non-empty array'})
        if not isinstance(relationships, list):
            return json.dumps({'error': 'relationships must be an array'})
        
        # Validate contacts have required fields
        valid_contacts = {}
        for c in contacts:
            if 'id' not in c or 'name' not in c:
                return json.dumps({'error': 'Each contact must have id and name fields'})
            valid_contacts[c['id']] = {
                'name': c['name'],
                'group': c.get('group', 'Uncategorized')
            }
        
        # Build adjacency and statistics
        adjacency = {cid: {'connections': [], 'total_strength': 0.0} for cid in valid_contacts}
        processed_relationships = []
        
        for rel in relationships:
            if 'source' not in rel or 'target' not in rel:
                continue
            src, tgt = rel['source'], rel['target']
            if src not in valid_contacts or tgt not in valid_contacts:
                continue
            
            strength = min(1.0, max(0.0, rel.get('strength', 0.5)))
            processed_relationships.append({
                'source': src,
                'target': tgt,
                'strength': strength
            })
            
            adjacency[src]['connections'].append(tgt)
            adjacency[src]['total_strength'] += strength
            adjacency[tgt]['connections'].append(src)
            adjacency[tgt]['total_strength'] += strength
        
        # Prepare node data
        nodes = []
        for cid, info in valid_contacts.items():
            conn_count = len(adjacency[cid]['connections'])
            node = {
                'id': cid,
                'name': info['name'],
                'group': info['group'],
                'connection_count': conn_count,
                'total_strength': round(adjacency[cid]['total_strength'], 2)
            }
            nodes.append(node)
        
        # Build visualization data
        visualization = {
            'type': 'network_graph',
            'nodes': nodes,
            'edges': processed_relationships,
            'metadata': {
                'total_nodes': len(nodes),
                'total_edges': len(processed_relationships),
                'layout': data.get('layout', 'force_directed'),
                'color_by': data.get('color_by', 'group')
            }
        }
        
        # If focus user specified, add highlight info
        focus_id = data.get('focus_user_id')
        if focus_id and focus_id in valid_contacts:
            direct_connections = [
                conn for conn in processed_relationships 
                if conn['source'] == focus_id or conn['target'] == focus_id
            ]
            connected_ids = set()
            for conn in direct_connections:
                connected_ids.add(conn['source'])
                connected_ids.add(conn['target'])
            connected_ids.discard(focus_id)
            
            visualization['focus'] = {
                'user_id': focus_id,
                'user_name': valid_contacts[focus_id]['name'],
                'direct_connections': list(connected_ids),
                'connection_count': len(connected_ids)
            }
        
        return json.dumps(visualization, ensure_ascii=False)
        
    except json.JSONDecodeError as e:
        return json.dumps({'error': f'Invalid JSON payload: {str(e)}'})
    except Exception as e:
        return json.dumps({'error': f'Unexpected error: {str(e)}'})


TOOL_SPEC = {
    "name": "social_graph_visualizer",
    "description": "Generate an interactive network graph visualization of social connections from a user's contact list, showing relationships between individuals and groups with connection strength indicators.",
    "category": "visualization",
    "domain": "social",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "contacts": {
            "type": "array",
            "description": "List of contact objects, each containing id, name, and group affiliation",
            "items": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "Unique identifier for the contact"
                    },
                    "name": {
                        "type": "string",
                        "description": "Display name of the contact"
                    },
                    "group": {
                        "type": "string",
                        "description": "Group or organization the contact belongs to"
                    }
                },
                "required": [
                    "id",
                    "name"
                ]
            }
        },
        "relationships": {
            "type": "array",
            "description": "List of relationship edges between contacts, each with source, target, and optional strength score (0-1)",
            "items": {
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "description": "ID of the source contact"
                    },
                    "target": {
                        "type": "string",
                        "description": "ID of the target contact"
                    },
                    "strength": {
                        "type": "number",
                        "description": "Optional: Connection strength between 0 and 1, default 0.5"
                    }
                },
                "required": [
                    "source",
                    "target"
                ]
            }
        },
        "focus_user_id": {
            "type": "string",
            "description": "Optional: ID of a contact to center the visualization around, highlighting their direct connections"
        },
        "layout": {
            "type": "string",
            "description": "Optional: Network layout algorithm",
            "enum": [
                "force_directed",
                "circular",
                "hierarchical",
                "radial"
            ],
            "default": "force_directed"
        },
        "color_by": {
            "type": "string",
            "description": "Optional: Property to color nodes by",
            "enum": [
                "group",
                "connection_count",
                "none"
            ],
            "default": "group"
        }
    },
    "required": [
        "contacts",
        "relationships"
    ]
},
}
