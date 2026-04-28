"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        action = data.get('action')
        if action not in ['list', 'register', 'update', 'remove']:
            return json.dumps({'error': 'Invalid action.'}, ensure_ascii=False)
        # Simulated in-memory store
        if not hasattr(run, 'store'):
            run.store = {}
        store = run.store
        if action == 'register':
            site_id = data.get('site_id')
            if not site_id:
                return json.dumps({'error': 'site_id is required for register.'}, ensure_ascii=False)
            if site_id in store:
                return json.dumps({'error': 'Site ID already exists.'}, ensure_ascii=False)
            name = data.get('name', 'Unknown')
            stype = data.get('type', 'other')
            location = data.get('location', '')
            description = data.get('description', '')
            store[site_id] = {'name': name, 'type': stype, 'location': location, 'description': description}
            return json.dumps({'message': 'Site registered successfully.', 'site_id': site_id}, ensure_ascii=False)
        elif action == 'update':
            site_id = data.get('site_id')
            if not site_id or site_id not in store:
                return json.dumps({'error': 'Site not found.'}, ensure_ascii=False)
            if 'name' in data:
                store[site_id]['name'] = data['name']
            if 'type' in data:
                store[site_id]['type'] = data['type']
            if 'location' in data:
                store[site_id]['location'] = data['location']
            if 'description' in data:
                store[site_id]['description'] = data['description']
            return json.dumps({'message': 'Site updated successfully.', 'site_id': site_id}, ensure_ascii=False)
        elif action == 'remove':
            site_id = data.get('site_id')
            if not site_id or site_id not in store:
                return json.dumps({'error': 'Site not found.'}, ensure_ascii=False)
            del store[site_id]
            return json.dumps({'message': 'Site removed successfully.', 'site_id': site_id}, ensure_ascii=False)
        elif action == 'list':
            filters = data.get('filters', {})
            results = list(store.values())
            if filters.get('type'):
                results = [s for s in results if s['type'] == filters['type']]
            if filters.get('location'):
                results = [s for s in results if filters['location'].lower() in s['location'].lower()]
            return json.dumps({'sites': results, 'count': len(results)}, ensure_ascii=False)
        else:
            return json.dumps({'error': 'Unknown action.'}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "cultural_heritage_site_manager",
    "description": "Register, update, query, and remove cultural heritage sites (museums, monuments, galleries) in a local registry. Returns confirmation messages for modifications and a list of matching sites for queries.",
    "category": "system",
    "domain": "culture",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": [
                "list",
                "register",
                "update",
                "remove"
            ],
            "description": "Operation to perform: 'list' to query sites, 'register' to add a new site, 'update' to modify an existing site, 'remove' to delete a site."
        },
        "site_id": {
            "type": "string",
            "description": "Unique identifier for the site (used for update, remove, or filtering in list)."
        },
        "name": {
            "type": "string",
            "description": "Name of the cultural heritage site."
        },
        "type": {
            "type": "string",
            "enum": [
                "museum",
                "monument",
                "gallery",
                "library",
                "archive",
                "historical_building",
                "other"
            ],
            "description": "Category of the cultural site."
        },
        "location": {
            "type": "string",
            "description": "Address or geographic location description of the site."
        },
        "description": {
            "type": "string",
            "description": "Brief summary of the site's cultural or historical significance."
        },
        "filters": {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": [
                        "museum",
                        "monument",
                        "gallery",
                        "library",
                        "archive",
                        "historical_building",
                        "other"
                    ],
                    "description": "Filter by site type."
                },
                "location": {
                    "type": "string",
                    "description": "Filter by location keyword."
                }
            },
            "description": "Optional: Filter criteria for list queries."
        }
    },
    "required": [
        "action"
    ]
},
}
