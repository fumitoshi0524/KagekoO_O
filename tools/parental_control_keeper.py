"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Manage and enforce parental control settings across entertainment services."""
    import json
    try:
        data = json.loads(payload)
        platform = data.get("platform")
        action = data.get("action")
        if not platform or not action:
            return json.dumps({"error": "Missing required parameters: platform, action"})
        
        # Simulate persistence (in-memory store for demonstration)
        if not hasattr(run, "config_store"):
            run.config_store = {
                "streaming": {"rating_limit": "PG-13", "time_limit": 120},
                "gaming": {"rating_limit": "T", "time_limit": 90},
                "social_media": {"rating_limit": "13+", "time_limit": 60}
            }
        if not hasattr(run, "log_store"):
            run.log_store = [
                {"timestamp": "2025-03-21T14:30:00Z", "platform": "streaming", "user": "child1", "activity": "Attempted to watch R-rated movie", "action_taken": "blocked"}
            ]

        if action == "set_restrictions":
            platforms_to_update = ["streaming", "gaming", "social_media"] if platform == "all" else [platform]
            for p in platforms_to_update:
                if data.get("content_rating_limit"):
                    run.config_store[p]["rating_limit"] = data["content_rating_limit"]
                if data.get("daily_time_limit_minutes"):
                    run.config_store[p]["time_limit"] = data["daily_time_limit_minutes"]
            return json.dumps({"status": "updated", "config": run.config_store})
        
        elif action == "view_status":
            if platform == "all":
                return json.dumps({"status": "active", "config": run.config_store})
            return json.dumps({"status": "active", "config": run.config_store.get(platform, {})})
        
        elif action == "view_logs":
            logs = run.log_store
            if platform != "all":
                logs = [log for log in logs if log["platform"] == platform]
            if data.get("user_id"):
                logs = [log for log in logs if log["user"] == data["user_id"]]
            return json.dumps({"log_entries": logs, "count": len(logs)})
        
        elif action == "update_time_limit":
            if not data.get("daily_time_limit_minutes"):
                return json.dumps({"error": "daily_time_limit_minutes required for update_time_limit action"})
            if platform == "all":
                for p in run.config_store:
                    run.config_store[p]["time_limit"] = data["daily_time_limit_minutes"]
            else:
                run.config_store[platform]["time_limit"] = data["daily_time_limit_minutes"]
            return json.dumps({"status": "time_limit_updated", "config": run.config_store})
        
        else:
            return json.dumps({"error": f"Unknown action: {action}"})
    except Exception as e:
        return f"error: {e}"


TOOL_SPEC = {
    "name": "parental_control_keeper",
    "description": "Manage and enforce parental control settings across entertainment services (streaming platforms, gaming consoles, social media), updating content filters, time limits, and usage logs, and returning the current status of restrictions and any flagged activity.",
    "category": "system",
    "domain": "entertainment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "platform": {
            "type": "string",
            "description": "Target entertainment platform for parental control configuration",
            "enum": [
                "streaming",
                "gaming",
                "social_media",
                "all"
            ]
        },
        "action": {
            "type": "string",
            "description": "Operation to perform on parental controls",
            "enum": [
                "set_restrictions",
                "view_status",
                "view_logs",
                "update_time_limit"
            ]
        },
        "content_rating_limit": {
            "type": "string",
            "description": "Optional: Maximum content rating allowed (e.g., PG-13, TV-14, M). If not provided, existing limit is kept."
        },
        "daily_time_limit_minutes": {
            "type": "integer",
            "description": "Optional: Maximum daily usage time in minutes (1-1440). If not provided, existing limit is kept."
        },
        "user_id": {
            "type": "string",
            "description": "Optional: Identifier for the child user account. If omitted, applies to all child accounts under the parent profile."
        }
    },
    "required": [
        "platform",
        "action"
    ]
},
}
