"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Manage the community moderation queue by reviewing reported user content, applying actions (approve, warn, remove, ban), and tracking moderator decisions with timestamps and notes."""
    import json
    import uuid
    from datetime import datetime, timedelta

    try:
        data = json.loads(payload)
        action = data.get("action")
        report_ids = data.get("report_ids", [])
        moderator_id = data.get("moderator_id")
        reason = data.get("reason", "")
        duration_hours = data.get("duration_hours")

        if action not in ["approve", "warn", "remove", "ban"]:
            return json.dumps({"error": "Invalid action. Must be one of: approve, warn, remove, ban."})
        if not report_ids or not isinstance(report_ids, list):
            return json.dumps({"error": "report_ids must be a non-empty array of strings."})
        if not moderator_id or not isinstance(moderator_id, str):
            return json.dumps({"error": "moderator_id is required and must be a string."})

        results = []
        for rid in report_ids:
            if not isinstance(rid, str) or len(rid) == 0:
                results.append({"report_id": rid, "status": "skipped", "error": "Invalid report ID format"})
                continue

            timestamp = datetime.utcnow().isoformat() + "Z"
            entry = {
                "report_id": rid,
                "action": action,
                "moderator_id": moderator_id,
                "reason": reason,
                "action_timestamp": timestamp,
                "status": "processed"
            }

            if action in ["warn", "ban"] and duration_hours is not None:
                expiry = (datetime.utcnow() + timedelta(hours=duration_hours)).isoformat() + "Z"
                entry["expires_at"] = expiry
                entry["duration_hours"] = duration_hours
            else:
                entry["expires_at"] = None

            if action == "approve":
                entry["note"] = "Content approved. No further action."
            elif action == "warn":
                entry["note"] = f"User warned. Reason: {reason if reason else 'No reason provided.'}"
            elif action == "remove":
                entry["note"] = f"Content removed. Reason: {reason if reason else 'No reason provided.'}"
            elif action == "ban":
                entry["note"] = f"User banned. Reason: {reason if reason else 'No reason provided.'}"

            moderation_id = str(uuid.uuid4())
            entry["moderation_id"] = moderation_id
            results.append(entry)

        response = {
            "status": "success",
            "processed_count": len([r for r in results if r.get("status") == "processed"]),
            "results": results
        }
        return json.dumps(response, ensure_ascii=False)

    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON payload: {str(e)}"})
    except Exception as e:
        return json.dumps({"error": f"Unexpected error: {str(e)}"})



TOOL_SPEC = {
    "name": "moderation_queue_manager",
    "description": "Manage the community moderation queue by reviewing reported user content, applying actions (approve, warn, remove, ban), and tracking moderator decisions with timestamps and notes.",
    "category": "system",
    "domain": "social",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": [
                "approve",
                "warn",
                "remove",
                "ban"
            ],
            "description": "The moderation action to apply to the reported item."
        },
        "report_ids": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "List of report IDs to process. Each ID must be a UUID format string."
        },
        "moderator_id": {
            "type": "string",
            "description": "The unique identifier of the moderator performing the action."
        },
        "reason": {
            "type": "string",
            "description": "Optional: Explanation or note for the moderation action, visible to the reported user if applicable."
        },
        "duration_hours": {
            "type": "integer",
            "description": "Optional: Duration in hours for temporary actions (warn or ban). If not provided, defaults to permanent action.",
            "minimum": 1,
            "maximum": 8760
        }
    },
    "required": [
        "action",
        "report_ids",
        "moderator_id"
    ]
},
}
