"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        user_id = data.get('user_id')
        if user_id is None:
            return 'error: user_id is required'
        if not isinstance(user_id, int):
            return 'error: user_id must be an integer'
        if user_id <= 0:
            return 'error: user_id must be positive'
        
        # Simulate a set of allowed user IDs (1..1000)
        if user_id < 1 or user_id > 1000:
            return 'error: user_id out of range (1..1000)'
        
        # Simulate disabling the user (in real system would update DB)
        result = {
            "user_id": user_id,
            "status": "disabled",
            "message": f"User {user_id} has been disabled successfully."
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "healthcare_user_disabler",
    "description": "Disable a healthcare system user account by user ID, preventing further system access while preserving audit logs and historical data integrity. Returns the user ID and status of the disablement operation.",
    "category": "system",
    "domain": "healthcare",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "user_id": {
            "type": "integer",
            "description": "Unique identifier of the healthcare system user account to disable."
        }
    },
    "required": [
        "user_id"
    ]
},
}
