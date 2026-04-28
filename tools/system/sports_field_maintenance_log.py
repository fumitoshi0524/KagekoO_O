"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Record and track maintenance activities for sports facilities and fields."""
    import json
    from datetime import datetime

    try:
        data = json.loads(payload)

        # Validate required fields
        required = ["field_id", "action", "description", "assigned_to", "status"]
        for field in required:
            if field not in data:
                return json.dumps({"error": f"Missing required field: {field}"})

        field_id = data["field_id"]
        action = data["action"]
        description = data["description"]
        assigned_to = data["assigned_to"]
        status = data["status"]

        # Validate enum values
        valid_actions = ["inspection", "repair", "mowing", "lining", "fertilization", "aeration", "irrigation", "general_maintenance"]
        valid_statuses = ["completed", "in_progress", "scheduled", "deferred"]
        valid_severities = ["low", "medium", "high", "critical"]

        if action not in valid_actions:
            return json.dumps({"error": f"Invalid action: {action}. Must be one of {valid_actions}"})
        if status not in valid_statuses:
            return json.dumps({"error": f"Invalid status: {status}. Must be one of {valid_statuses}"})

        # Optional fields with validation
        severity = data.get("severity", "low")
        if severity not in valid_severities:
            return json.dumps({"error": f"Invalid severity: {severity}. Must be one of {valid_severities}"})

        cost = data.get("cost")
        if cost is not None and (not isinstance(cost, (int, float)) or cost < 0):
            return json.dumps({"error": "Cost must be a non-negative number"})

        # Create log entry
        log_entry = {
            "log_id": f"ML-{datetime.now().strftime('%Y%m%d%H%M%S')}-{field_id}",
            "field_id": field_id,
            "action": action,
            "description": description,
            "assigned_to": assigned_to,
            "status": status,
            "severity": severity,
            "cost": cost if cost is not None else 0.0,
            "timestamp": datetime.now().isoformat(),
            "recorded_by": "system"
        }

        # Simulate storage (in real system this would write to DB)
        # In this implementation we just return the log entry

        return json.dumps({
            "success": True,
            "message": f"Maintenance log created for field {field_id}",
            "log_entry": log_entry
        }, ensure_ascii=False)

    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON payload: {str(e)}"})
    except Exception as e:
        return json.dumps({"error": f"Unexpected error: {str(e)}"})


TOOL_SPEC = {
    "name": "sports_field_maintenance_log",
    "description": "Record and track maintenance activities for sports facilities and fields, including inspections, repairs, and scheduled upkeep. Returns a maintenance log entry with status, timestamp, and assigned personnel.",
    "category": "system",
    "domain": "sports",
    "risk_level": "write",
    "schema": {
    "type": "object",
    "properties": {
        "field_id": {
            "type": "string",
            "description": "Unique identifier for the sports field or facility"
        },
        "action": {
            "type": "string",
            "enum": [
                "inspection",
                "repair",
                "mowing",
                "lining",
                "fertilization",
                "aeration",
                "irrigation",
                "general_maintenance"
            ],
            "description": "Type of maintenance action performed"
        },
        "description": {
            "type": "string",
            "description": "Detailed description of the maintenance activity, including observed issues and work performed"
        },
        "assigned_to": {
            "type": "string",
            "description": "Name or ID of the person responsible for the maintenance task"
        },
        "status": {
            "type": "string",
            "enum": [
                "completed",
                "in_progress",
                "scheduled",
                "deferred"
            ],
            "description": "Current status of the maintenance activity"
        },
        "severity": {
            "type": "string",
            "enum": [
                "low",
                "medium",
                "high",
                "critical"
            ],
            "description": "Optional: Urgency level of the maintenance issue"
        },
        "cost": {
            "type": "number",
            "description": "Optional: Cost incurred for the maintenance activity in USD",
            "minimum": 0
        }
    },
    "required": [
        "field_id",
        "action",
        "description",
        "assigned_to",
        "status"
    ]
},
}
