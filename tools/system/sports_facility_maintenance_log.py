"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Log and query maintenance records for sports facility equipment."""
    import json
    try:
        data = json.loads(payload)
        action = data.get("action")
        equipment_id = data.get("equipment_id")
        issue_description = data.get("issue_description")
        severity = data.get("severity")
        technician = data.get("technician", "")
        status = data.get("status", "open")
        if not action or not equipment_id or not issue_description or not severity:
            return json.dumps({"error": "Missing required fields: action, equipment_id, issue_description, severity"})
        # Simulated in-memory maintenance log (for real system would use DB)
        if not hasattr(run, "log"):
            run.log = []
        if action == "add":
            record = {
                "id": len(run.log) + 1,
                "equipment_id": equipment_id,
                "issue_description": issue_description,
                "severity": severity,
                "technician": technician,
                "status": status
            }
            run.log.append(record)
            return json.dumps({"success": True, "record": record})
        elif action == "list":
            filtered = [r for r in run.log if r["equipment_id"] == equipment_id or not equipment_id]
            if status and status != "all":
                filtered = [r for r in filtered if r["status"] == status]
            return json.dumps({"records": filtered})
        elif action == "update":
            record_id = data.get("record_id")
            if record_id is None:
                return json.dumps({"error": "record_id required for update"})
            for r in run.log:
                if r["id"] == record_id:
                    if "status" in data:
                        r["status"] = data["status"]
                    if "technician" in data:
                        r["technician"] = data["technician"]
                    if "issue_description" in data:
                        r["issue_description"] = data["issue_description"]
                    return json.dumps({"success": True, "record": r})
            return json.dumps({"error": f"Record id {record_id} not found"})
        else:
            return json.dumps({"error": f"Unknown action: {action}"})
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "sports_facility_maintenance_log",
    "description": "Log and query maintenance records for sports facility equipment (treadmills, weight machines, court surfaces, lighting) including issue description, severity level, and technician assignment.",
    "category": "system",
    "domain": "sports",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "description": "Action to perform: 'add' to create a new maintenance record, 'list' to retrieve records, or 'update' to modify an existing record.",
            "enum": [
                "add",
                "list",
                "update"
            ]
        },
        "equipment_id": {
            "type": "string",
            "description": "Unique identifier of the sports equipment being maintained (e.g., 'TM-001' for treadmill, 'WM-002' for weight machine)."
        },
        "issue_description": {
            "type": "string",
            "description": "Description of the issue or maintenance needed for the equipment."
        },
        "severity": {
            "type": "string",
            "description": "Severity level of the maintenance issue.",
            "enum": [
                "low",
                "medium",
                "high",
                "critical"
            ]
        },
        "technician": {
            "type": "string",
            "description": "Name or ID of the assigned technician for the maintenance task."
        },
        "status": {
            "type": "string",
            "description": "Optional: Current status of the maintenance record (e.g., 'open', 'in_progress', 'resolved', 'closed')."
        }
    },
    "required": [
        "action",
        "equipment_id",
        "issue_description",
        "severity"
    ]
},
}
