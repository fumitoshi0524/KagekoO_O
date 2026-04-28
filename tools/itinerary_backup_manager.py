"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Manage backup and restore operations for travel itineraries."""
    import json
    try:
        data = json.loads(payload)
        operation = data.get('operation')
        itinerary_id = data.get('itinerary_id')
        backup_id = data.get('backup_id')
        backup_label = data.get('backup_label', '')
        
        if not operation or not itinerary_id:
            return json.dumps({'error': 'Missing required fields: operation, itinerary_id'}, ensure_ascii=False)
        
        if operation == 'create_backup':
            import datetime
            timestamp = datetime.datetime.now().isoformat()
            new_backup_id = f'backup_{itinerary_id}_{int(datetime.datetime.now().timestamp())}'
            result = {
                'status': 'success',
                'message': f'Backup created for itinerary {itinerary_id}',
                'backup_id': new_backup_id,
                'backup_timestamp': timestamp,
                'backup_label': backup_label if backup_label else None
            }
        elif operation == 'list_backups':
            import datetime
            mock_backups = [
                {'backup_id': f'backup_{itinerary_id}_1700000000', 'timestamp': '2024-03-15T10:30:00', 'label': 'Original plan'},
                {'backup_id': f'backup_{itinerary_id}_1700100000', 'timestamp': '2024-03-16T14:20:00', 'label': 'After hotel change'}
            ]
            result = {
                'status': 'success',
                'itinerary_id': itinerary_id,
                'backup_count': len(mock_backups),
                'backups': mock_backups
            }
        elif operation == 'restore_backup':
            if not backup_id:
                return json.dumps({'error': 'backup_id is required for restore_backup operation'}, ensure_ascii=False)
            import datetime
            restore_timestamp = datetime.datetime.now().isoformat()
            result = {
                'status': 'success',
                'message': f'Itinerary {itinerary_id} restored from backup {backup_id}',
                'itinerary_id': itinerary_id,
                'backup_id': backup_id,
                'restore_timestamp': restore_timestamp
            }
        else:
            return json.dumps({'error': f'Unknown operation: {operation}'}, ensure_ascii=False)
        
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "itinerary_backup_manager",
    "description": "Manage backup and restore operations for travel itineraries, allowing users to create versioned backups of their trip plans, list available backups, and restore specific itinerary versions in case of data loss or unwanted changes.",
    "category": "system",
    "domain": "travel",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "operation": {
            "type": "string",
            "description": "The backup operation to perform: create_backup, list_backups, or restore_backup",
            "enum": [
                "create_backup",
                "list_backups",
                "restore_backup"
            ]
        },
        "itinerary_id": {
            "type": "string",
            "description": "Unique identifier of the travel itinerary to backup or restore"
        },
        "backup_id": {
            "type": "string",
            "description": "Optional: Unique identifier of a specific backup version to restore (required only for restore_backup operation)"
        },
        "backup_label": {
            "type": "string",
            "description": "Optional: Human-readable label for the backup (e.g., 'Before flight changes', 'Final version')"
        }
    },
    "required": [
        "operation",
        "itinerary_id"
    ]
},
}
