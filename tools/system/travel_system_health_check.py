"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Execute a comprehensive health check across all registered travel services and return operational status."""
    import json
    import time
    import random

    try:
        data = json.loads(payload)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON payload: {e}"})

    include_detailed = data.get("include_detailed_metrics", False)
    service_filter = data.get("service_filter", None)
    timeout = data.get("timeout_seconds", 5)

    all_services = ["booking_engine", "payment_gateway", "itinerary_planner", "notification_service"]
    if service_filter:
        # Validate filter values
        valid_services = [s for s in service_filter if s in all_services]
        if not valid_services:
            return json.dumps({"error": "No valid services specified in service_filter"})
        services_to_check = valid_services
    else:
        services_to_check = all_services

    results = {}
    overall_status = "healthy"

    for service in services_to_check:
        start_time = time.time()
        # Simulate checking the service (real implementation would call actual endpoints)
        # For realism, simulate occasional degradation
        choice = random.random()
        if choice < 0.7:
            status = "healthy"
            response_time_ms = random.randint(50, 300)
            incidents = []
        elif choice < 0.9:
            status = "degraded"
            response_time_ms = random.randint(500, 2000)
            incidents = ["High latency detected"]
        else:
            status = "unreachable"
            response_time_ms = None
            incidents = ["Service did not respond within timeout"]
            if status == "unreachable":
                overall_status = "degraded"

        elapsed = (time.time() - start_time) * 1000  # ms
        if elapsed > timeout * 1000:
            status = "unreachable"
            response_time_ms = None
            incidents = ["Timeout exceeded"]
            overall_status = "degraded"

        service_result = {
            "status": status,
            "incidents": incidents
        }
        if include_detailed:
            if response_time_ms is not None:
                service_result["response_time_ms"] = response_time_ms
            service_result["checked_at_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        results[service] = service_result

    # If any service is unreachable, mark overall degraded
    if any(v["status"] == "unreachable" for v in results.values()):
        overall_status = "degraded"

    output = {
        "overall_status": overall_status,
        "services_checked": len(services_to_check),
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "services": results
    }

    return json.dumps(output, ensure_ascii=False)



TOOL_SPEC = {
    "name": "travel_system_health_check",
    "description": "Execute a comprehensive health check across all registered travel services (booking engine, payment gateway, itinerary planner, and notification service) and return the operational status, response times, and any active incidents for each subsystem.",
    "category": "system",
    "domain": "travel",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "include_detailed_metrics": {
            "type": "boolean",
            "description": "Optional: If True, includes per-service response times (in milliseconds) and last-accessed timestamp in the output."
        },
        "service_filter": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [
                    "booking_engine",
                    "payment_gateway",
                    "itinerary_planner",
                    "notification_service"
                ]
            },
            "description": "Optional: List of service names to check. If omitted, all registered services are checked."
        },
        "timeout_seconds": {
            "type": "integer",
            "minimum": 1,
            "maximum": 30,
            "description": "Optional: Maximum time to wait per service check (in seconds). Default is 5."
        }
    },
    "required": []
},
}
