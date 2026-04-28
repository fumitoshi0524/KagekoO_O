"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    from datetime import datetime, timedelta
    try:
        data = json.loads(payload)
        account_id = data.get('account_id')
        reason = data.get('reason')
        duration_hours = data.get('duration_hours')
        if not account_id or not reason or duration_hours is None:
            return json.dumps({'error': 'Missing required fields: account_id, reason, duration_hours'})
        if reason not in ['policy_violation', 'security_breach', 'spam', 'harassment', 'other']:
            return json.dumps({'error': 'Invalid reason'})
        if not isinstance(duration_hours, int) or duration_hours < 1 or duration_hours > 8760:
            return json.dumps({'error': 'duration_hours must be integer between 1 and 8760'})
        suspension_time = datetime.utcnow().isoformat() + 'Z'
        unsuspension_time = (datetime.utcnow() + timedelta(hours=duration_hours)).isoformat() + 'Z'
        result = {
            'status': 'suspended',
            'account_id': account_id,
            'reason': reason,
            'duration_hours': duration_hours,
            'suspension_timestamp': suspension_time,
            'unsuspension_timestamp': unsuspension_time,
            'admin_id': data.get('admin_id', None),
            'note': data.get('note', '')
            }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "social_media_account_suspender",
    "description": "Temporarily suspend or deactivate a social media user account for policy violations or security reasons, returning a suspension confirmation with the account identifier, suspension timestamp, duration, and administrative notes for the moderation team.",
    "category": "system",
    "domain": "social",
    "risk_level": "high",
    "schema": {
    "type": "object",
    "properties": {
        "account_id": {
            "type": "string",
            "description": "Unique identifier of the social media user account to suspend."
        },
        "reason": {
            "type": "string",
            "description": "Reason for the suspension (policy_violation, security_breach, spam, harassment, other).",
            "enum": [
                "policy_violation",
                "security_breach",
                "spam",
                "harassment",
                "other"
            ]
        },
        "duration_hours": {
            "type": "integer",
            "description": "Duration of suspension in hours (must be between 1 and 8760).",
            "minimum": 1,
            "maximum": 8760
        },
        "admin_id": {
            "type": "string",
            "description": "Optional: Identifier of the administrator issuing the suspension."
        },
        "note": {
            "type": "string",
            "description": "Optional: Additional administrative note or context for the suspension."
        }
    },
    "required": [
        "account_id",
        "reason",
        "duration_hours"
    ]
},
}
