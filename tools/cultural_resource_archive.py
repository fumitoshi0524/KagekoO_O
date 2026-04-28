"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        action = data.get('action')
        if not action:
            return json.dumps({'error': 'action is required'})
        # In-memory storage for demonstration (in production, use a database)
        if not hasattr(run, 'store'):
            run.store = {}
        store = run.store
        if action == 'add':
            resource_type = data.get('resource_type')
            title = data.get('title')
            if not resource_type or not title:
                return json.dumps({'error': 'resource_type and title are required for add action'})
            resource_id = str(len(store) + 1)
            store[resource_id] = {
                'resource_id': resource_id,
                'resource_type': resource_type,
                'title': title,
                'creator': data.get('creator', ''),
                'date_created': data.get('date_created', ''),
                'medium': data.get('medium', ''),
                'description': data.get('description', ''),
                'provenance': data.get('provenance', '')
            }
            return json.dumps({'status': 'success', 'resource_id': resource_id})
        elif action == 'update':
            resource_id = data.get('resource_id')
            if not resource_id or resource_id not in store:
                return json.dumps({'error': 'invalid or missing resource_id'})
            for field in ['resource_type', 'title', 'creator', 'date_created', 'medium', 'description', 'provenance']:
                if field in data:
                    store[resource_id][field] = data[field]
            return json.dumps({'status': 'updated', 'resource': store[resource_id]})
        elif action == 'delete':
            resource_id = data.get('resource_id')
            if not resource_id or resource_id not in store:
                return json.dumps({'error': 'invalid or missing resource_id'})
            deleted = store.pop(resource_id)
            return json.dumps({'status': 'deleted', 'resource': deleted})
        elif action == 'get':
            resource_id = data.get('resource_id')
            if not resource_id or resource_id not in store:
                return json.dumps({'error': 'resource not found'})
            return json.dumps({'resource': store[resource_id]})
        elif action == 'search':
            query = data.get('query', '').lower()
            if not query:
                return json.dumps({'error': 'query string required for search'})
            results = []
            for rid, rec in store.items():
                if (query in rec.get('title', '').lower() or
                    query in rec.get('creator', '').lower() or
                    query in rec.get('description', '').lower() or
                    query in rec.get('provenance', '').lower()):
                    results.append(rec)
            return json.dumps({'results': results})
        elif action == 'list_all':
            return json.dumps({'resources': list(store.values())})
        else:
            return json.dumps({'error': f'unknown action: {action}'})
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "cultural_resource_archive",
    "description": "Maintain a system-level archive of cultural heritage resources — supports adding, updating, deleting, and searching artworks, artifacts, literary works, and historical records with metadata such as creator, date, medium, and provenance.",
    "category": "system",
    "domain": "culture",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "description": "Operation to perform: add, update, delete, get, search, or list_all",
            "enum": [
                "add",
                "update",
                "delete",
                "get",
                "search",
                "list_all"
            ]
        },
        "resource_id": {
            "type": "string",
            "description": "Unique identifier for a resource (used with get, update, delete actions). Format: alphanumeric, max 64 characters."
        },
        "resource_type": {
            "type": "string",
            "description": "Category of the cultural resource: artwork, artifact, literary_work, historical_record",
            "enum": [
                "artwork",
                "artifact",
                "literary_work",
                "historical_record"
            ]
        },
        "title": {
            "type": "string",
            "description": "Title or name of the resource. Required for add and update."
        },
        "creator": {
            "type": "string",
            "description": "Creator, author, artist, or originating culture of the resource. Optional: use with add/update to specify attribution."
        },
        "date_created": {
            "type": "string",
            "description": "Date or approximate date of creation (e.g., '1889', 'circa 1500', '1960s'). Optional: provide as free-text string."
        },
        "medium": {
            "type": "string",
            "description": "Medium, material, or format (e.g., 'oil on canvas', 'bronze', 'manuscript', 'stone tablet'). Optional."
        },
        "description": {
            "type": "string",
            "description": "Brief textual description or summary of the resource. Optional: use for rich metadata."
        },
        "provenance": {
            "type": "string",
            "description": "Origin, history of ownership, or current location (e.g., 'Louvre Museum', 'private collection'). Optional."
        },
        "query": {
            "type": "string",
            "description": "Search query string to match against title, creator, description, or provenance (used with search action)."
        }
    },
    "required": [
        "action"
    ]
},
}
