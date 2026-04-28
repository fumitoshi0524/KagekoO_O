"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a system health report for a healthcare facility's IT infrastructure."""
    import json
    import random
    import datetime

    try:
        data = json.loads(payload)
        facility_id = data.get("facility_id")
        report_type = data.get("report_type")
        include_network = data.get("include_network", True)
        include_storage = data.get("include_storage", True)
        time_range_hours = data.get("time_range_hours", 24)

        if not facility_id or not isinstance(facility_id, str):
            return json.dumps({"error": "facility_id must be a non-empty string"})
        if report_type not in ["summary", "detailed", "compliance"]:
            return json.dumps({"error": "report_type must be one of: summary, detailed, compliance"})
        if not isinstance(time_range_hours, int) or time_range_hours < 1 or time_range_hours > 168:
            return json.dumps({"error": "time_range_hours must be an integer between 1 and 168"})

        # Simulate system health data (real implementation would query monitoring systems)
        now = datetime.datetime.utcnow()
        start_time = now - datetime.timedelta(hours=time_range_hours)

        # Core server statuses (simulated)
        servers = [
            {"name": "ehr-app-server", "type": "application", "status": random.choice(["healthy", "healthy", "healthy", "degraded"])},
            {"name": "ehr-db-server", "type": "database", "status": random.choice(["healthy", "healthy", "healthy", "degraded"])},
            {"name": "pacs-server", "type": "storage", "status": random.choice(["healthy", "healthy", "degraded", "critical"])},
            {"name": "lab-info-system", "type": "application", "status": random.choice(["healthy", "healthy", "healthy", "offline"])},
            {"name": "pharmacy-mgmt", "type": "application", "status": random.choice(["healthy", "healthy", "healthy", "degraded"])}
        ]

        # Network components
        network_status = []
        if include_network:
            network_status = [
                {"component": "core-switch-01", "status": random.choice(["operational", "operational", "degraded"])},
                {"component": "firewall-cluster", "status": random.choice(["operational", "operational", "operational", "degraded"])},
                {"component": "vpn-gateway", "status": random.choice(["operational", "operational", "offline"])}
            ]

        # Storage systems
        storage_status = []
        if include_storage:
            storage_status = [
                {"component": "san-volume-01", "capacity_gb": 5000, "used_gb": 3200, "status": "healthy"},
                {"component": "san-volume-02", "capacity_gb": 2000, "used_gb": 1850, "status": "warning"},
                {"component": "backup-nas", "capacity_gb": 10000, "used_gb": 4500, "status": "healthy"}
            ]

        # Performance metrics
        cpu_avg = round(random.uniform(20, 90), 1)
        memory_avg = round(random.uniform(30, 95), 1)
        disk_io_avg = round(random.uniform(10, 80), 1)

        # Calculate overall health score
        total_components = len(servers) + len(network_status) + len(storage_status)
        healthy_count = sum(1 for s in servers if s["status"] == "healthy")
        healthy_count += sum(1 for n in network_status if n["status"] == "operational")
        healthy_count += sum(1 for st in storage_status if st["status"] == "healthy")
        health_score = round((healthy_count / max(total_components, 1)) * 100, 1)

        # Generate recommendations based on health
        recommendations = []
        for server in servers:
            if server["status"] == "degraded":
                recommendations.append(f"Investigate {server['name']} for performance degradation")
            elif server["status"] == "critical":
                recommendations.append(f"Immediate attention required for {server['name']} - component critical")
            elif server["status"] == "offline":
                recommendations.append(f"Restart {server['name']} - currently offline")
        
        if any(st["status"] == "warning" for st in storage_status):
            recommendations.append("Storage capacity on san-volume-02 is near full - consider expansion")
        
        if cpu_avg > 80:
            recommendations.append("High average CPU usage detected - consider scaling or load balancing")
        if memory_avg > 85:
            recommendations.append("High memory usage detected - review application memory allocation")

        if not recommendations:
            recommendations.append("All systems operational - no recommendations at this time")

        report_data = {
            "facility_id": facility_id,
            "generated_at": now.isoformat(),
            "report_type": report_type,
            "time_range": f"{time_range_hours} hours",
            "overall_health_score": health_score,
            "total_components_monitored": total_components,
            "healthy_components": healthy_count,
            "degraded_or_critical_components": total_components - healthy_count,
            "servers": servers,
            "network_components": network_status,
            "storage_components": storage_status,
            "performance_metrics": {
                "avg_cpu_percent": cpu_avg,
                "avg_memory_percent": memory_avg,
                "avg_disk_io_percent": disk_io_avg,
                "sample_period_hours": time_range_hours
            },
            "recommendations": recommendations
        }

        # If compliance report, add regulatory fields
        if report_type == "compliance":
            report_data["compliance_info"] = {
                "hipaa_audit_log_retention": "Compliant",
                "system_access_logs": "Enabled and monitored",
                "backup_frequency": "Daily",
                "disaster_recovery_tested": {
                    "status": random.choice(["Passed", "Failed", "Not Scheduled"]),
                    "last_test_date": (now - datetime.timedelta(days=random.randint(30, 365))).date().isoformat()
                }
            }

        # If summary, reduce detail
        if report_type == "summary":
            report_data.pop("servers", None)
            report_data.pop("network_components", None)
            report_data.pop("storage_components", None)
            report_data["summary_text"] = f"Health score {health_score}% - {healthy_count} of {total_components} components healthy"

        return json.dumps(report_data, ensure_ascii=False)

    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON input: {str(e)}"})
    except Exception as e:
        return json.dumps({"error": f"Unexpected error: {str(e)}"})


TOOL_SPEC = {
    "name": "system_health_report",
    "description": "Generate a system health report for a healthcare facility's IT infrastructure by aggregating component statuses, performance metrics, and recommended actions for system administrators.",
    "category": "system",
    "domain": "healthcare",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "facility_id": {
            "type": "string",
            "description": "Unique identifier for the healthcare facility (e.g., hospital, clinic)."
        },
        "report_type": {
            "type": "string",
            "enum": [
                "summary",
                "detailed",
                "compliance"
            ],
            "description": "Type of health report to generate: summary for overview, detailed for component-level metrics, compliance for regulatory requirements."
        },
        "include_network": {
            "type": "boolean",
            "description": "Optional: Whether to include network infrastructure status in the report.",
            "default": true
        },
        "include_storage": {
            "type": "boolean",
            "description": "Optional: Whether to include storage system status in the report.",
            "default": true
        },
        "time_range_hours": {
            "type": "integer",
            "description": "Optional: Number of hours of historical data to include in the report (minimum 1, maximum 168).",
            "examples": [
                24,
                72,
                168
            ],
            "default": 24
        }
    },
    "required": [
        "facility_id",
        "report_type"
    ]
},
}
