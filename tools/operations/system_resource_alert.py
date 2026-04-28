"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        resource_type = data.get("resource_type")
        threshold = data.get("threshold_value")
        current = data.get("current_value")
        severity = data.get("severity", "medium")
        host = data.get("host_identifier", "unknown")

        if resource_type not in ["cpu", "memory", "disk", "network"]:
            raise ValueError(f"Invalid resource_type: {resource_type}")
        if current < 0 or threshold < 0:
            raise ValueError("Values must be non-negative")
        if resource_type == "network" and (threshold > 10000 or current > 10000):
            raise ValueError("Network latency max is 10000ms")
        if resource_type != "network" and (threshold > 100 or current > 100):
            raise ValueError("CPU/memory/disk percentages must be 0-100")

        breached = current > threshold
        severity_order = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        severity_map = {1: "low", 2: "medium", 3: "high", 4: "critical"}

        if breached:
            severity_level = severity_order.get(severity, 2)
            if current > threshold * 1.5:
                severity_level = min(4, severity_level + 1)
            final_severity = severity_map[severity_level]
            recommended_action = get_recommended_action(resource_type, final_severity, host)
            result = {
                "alert": True,
                "resource_type": resource_type,
                "host": host,
                "severity": final_severity,
                "current_value": current,
                "threshold": threshold,
                "message": f"{resource_type.upper()} threshold breached on {host}: {current} > {threshold}",
                "recommended_action": recommended_action
            }
        else:
            result = {
                "alert": False,
                "resource_type": resource_type,
                "host": host,
                "current_value": current,
                "threshold": threshold,
                "message": f"{resource_type.upper()} within normal range on {host}"
            }

        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": str(e)})


def get_recommended_action(resource_type: str, severity: str, host: str) -> str:
    actions = {
        "cpu": {
            "low": "Monitor CPU usage trends.",
            "medium": "Check for runaway processes, consider adding CPU capacity.",
            "high": "Immediately identify top CPU consumers; escalate to system admin.",
            "critical": "Emergency: Kill high-CPU processes or automate scaling."
        },
        "memory": {
            "low": "Monitor memory usage trends.",
            "medium": "Check memory leaks; consider adding RAM.",
            "high": "Force restart memory-intensive applications.",
            "critical": "Emergency: OOM killer may activate; add swap or migrate workloads."
        },
        "disk": {
            "low": "Monitor disk usage trends.",
            "medium": "Archive old logs; clean temp directories.",
            "high": "Migrate data to larger volume or storage tier.",
            "critical": "Emergency: Free up space immediately to prevent data loss."
        },
        "network": {
            "low": "Monitor network latency trends.",
            "medium": "Check bandwidth usage; optimize traffic routing.",
            "high": "Investigate network congestion or DDoS symptoms.",
            "critical": "Emergency: Engage network operations team; consider failover."
        }
    }
    return actions.get(resource_type, {}).get(severity, "Contact system administrator.")


TOOL_SPEC = {
    "name": "system_resource_alert",
    "description": "Monitor and generate alerts for system resource thresholds such as CPU usage, memory consumption, disk space, and network latency. Returns a structured alert event with severity level and recommended action for operations teams.",
    "category": "operations",
    "domain": "technology",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "resource_type": {
            "type": "string",
            "enum": [
                "cpu",
                "memory",
                "disk",
                "network"
            ],
            "description": "Type of system resource to monitor"
        },
        "threshold_value": {
            "type": "number",
            "description": "Threshold percentage for CPU/memory/disk (0-100) or network latency in milliseconds"
        },
        "severity": {
            "type": "string",
            "enum": [
                "low",
                "medium",
                "high",
                "critical"
            ],
            "description": "Optional: Severity level for the alert if threshold is breached, default is 'medium'"
        },
        "host_identifier": {
            "type": "string",
            "description": "Optional: Hostname or IP of the system being monitored"
        },
        "current_value": {
            "type": "number",
            "description": "Current measured value of the resource"
        }
    },
    "required": [
        "resource_type",
        "threshold_value",
        "current_value"
    ]
},
}
