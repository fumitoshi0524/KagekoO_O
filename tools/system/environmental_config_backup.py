"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Create a timestamped backup of environmental system configuration."""
    import json
    from datetime import datetime
    import uuid
    
    try:
        data = json.loads(payload)
        
        backup_name = data.get("backup_name")
        config_type = data.get("config_type")
        include_historical = data.get("include_historical_data", False)
        
        if not backup_name or not config_type:
            return json.dumps({"error": "Missing required fields: backup_name and config_type"})
        
        if config_type not in ["sensor_thresholds", "alert_rules", "reporting_intervals", "all"]:
            return json.dumps({"error": f"Invalid config_type: {config_type}"})
        
        backup_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        config_sizes = {
            "sensor_thresholds": 24,
            "alert_rules": 15,
            "reporting_intervals": 8,
            "all": 47
        }
        
        result = {
            "backup_id": backup_id,
            "backup_name": backup_name,
            "config_type": config_type,
            "timestamp": timestamp,
            "configuration_entries_backed_up": config_sizes.get(config_type, 0),
            "historical_data_included": include_historical,
            "status": "success",
            "message": f"Environmental configuration backup {backup_name} created successfully"
        }
        
        if include_historical:
            result["historical_records_count"] = 156
        
        return json.dumps(result, ensure_ascii=False)
        
    except json.JSONDecodeError as e:
        return f"error: Invalid JSON payload - {e}"
    except Exception as e:
        return f"error: {e}"


TOOL_SPEC = {
    "name": "environmental_config_backup",
    "description": "Create a timestamped backup of the current environmental system configuration including sensor thresholds, alert rules, and reporting intervals, returning a backup ID and configuration summary for system rollback purposes.",
    "category": "system",
    "domain": "environment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "backup_name": {
            "type": "string",
            "description": "Human-readable label for the backup snapshot, alphanumeric with underscores"
        },
        "config_type": {
            "type": "string",
            "enum": [
                "sensor_thresholds",
                "alert_rules",
                "reporting_intervals",
                "all"
            ],
            "description": "Type of environmental configuration to back up"
        },
        "include_historical_data": {
            "type": "boolean",
            "description": "Optional: Whether to include historical sensor readings in the backup, defaults to False"
        }
    },
    "required": [
        "backup_name",
        "config_type"
    ]
},
}
