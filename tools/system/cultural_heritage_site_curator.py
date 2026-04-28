"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Manages a registry of cultural heritage sites by adding, updating, listing, or removing site entries."""
    import json
    try:
        data = json.loads(payload)
        action = data.get('action')
        if not action or action not in ['add', 'update', 'list', 'remove']:
            return json.dumps({'error': 'Invalid or missing action. Must be one of: add, update, list, remove.'})
        
        # In-memory registry for demonstration (in production would use a database)
        if not hasattr(run, 'site_registry'):
            run.site_registry = {}
        registry = run.site_registry
        
        if action == 'add':
            site_name = data.get('site_name')
            if not site_name:
                return json.dumps({'error': 'site_name is required for add action.'})
            if site_name in registry:
                return json.dumps({'error': f'Site "{site_name}" already exists.'})
            registry[site_name] = {
                'location': data.get('location', 'unknown'),
                'site_type': data.get('site_type', 'other'),
                'historical_period': data.get('historical_period', ''),
                'significance': data.get('significance', '')
            }
            return json.dumps({'status': 'success', 'message': f'Site "{site_name}" added.', 'site': registry[site_name]})
        
        elif action == 'update':
            site_name = data.get('site_name')
            if not site_name or site_name not in registry:
                return json.dumps({'error': f'Site "{site_name}" not found for update.'})
            if 'location' in data:
                registry[site_name]['location'] = data['location']
            if 'site_type' in data:
                registry[site_name]['site_type'] = data['site_type']
            if 'historical_period' in data:
                registry[site_name]['historical_period'] = data['historical_period']
            if 'significance' in data:
                registry[site_name]['significance'] = data['significance']
            return json.dumps({'status': 'success', 'message': f'Site "{site_name}" updated.', 'site': registry[site_name]})
        
        elif action == 'list':
            if not registry:
                return json.dumps({'status': 'success', 'sites': [], 'count': 0})
            return json.dumps({'status': 'success', 'sites': [{'name': k, **v} for k, v in registry.items()], 'count': len(registry)})
        
        elif action == 'remove':
            site_name = data.get('site_name')
            if not site_name or site_name not in registry:
                return json.dumps({'error': f'Site "{site_name}" not found for removal.'})
            removed = registry.pop(site_name)
            return json.dumps({'status': 'success', 'message': f'Site "{site_name}" removed.', 'removed_site': {'name': site_name, **removed}})
        
        return json.dumps({'error': 'Unexpected error.'})
    except Exception as e:
        return json.dumps({'error': f'Failed to process request: {str(e)}'})


TOOL_SPEC = {
    "name": "cultural_heritage_site_curator",
    "description": "Manages a registry of cultural heritage sites by adding, updating, listing, or removing site entries (name, location, type, historical period, significance). Returns a confirmation or the curated site list for administrative oversight.",
    "category": "system",
    "domain": "culture",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": [
                "add",
                "update",
                "list",
                "remove"
            ],
            "description": "The curation operation to perform: add a new site, update an existing site, list all sites, or remove a site."
        },
        "site_name": {
            "type": "string",
            "description": "Unique name of the cultural heritage site."
        },
        "location": {
            "type": "string",
            "description": "Geographic location of the site (city, region, country)."
        },
        "site_type": {
            "type": "string",
            "enum": [
                "museum",
                "monument",
                "archaeological_site",
                "religious_building",
                "historical_district",
                "other"
            ],
            "description": "The category of the heritage site."
        },
        "historical_period": {
            "type": "string",
            "description": "Optional: The historical era or period associated with the site (e.g., 'Ming Dynasty', 'Ancient Rome', 'Medieval')."
        },
        "significance": {
            "type": "string",
            "description": "Optional: A brief description of the cultural or historical significance of the site."
        }
    },
    "required": [
        "action"
    ]
},
}
