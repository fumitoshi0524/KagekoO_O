"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        services = data.get('services', [])
        endpoints = data.get('endpoints', [])
        timeout = data.get('timeout_seconds', 5)
        if not isinstance(services, list) or len(services) == 0:
            return json.dumps({'error': 'services must be a non-empty list'})
        import socket
        from datetime import datetime
        results = {'timestamp': datetime.utcnow().isoformat(), 'services': {}, 'endpoints': {}}
        for svc in services:
            # Simulate check by trying to resolve service name
            try:
                socket.getaddrinfo(svc, 80, socket.AF_INET, socket.SOCK_STREAM)
                results['services'][svc] = 'UP'
            except socket.gaierror:
                results['services'][svc] = 'DOWN (unreachable)'
        for ep in endpoints:
            try:
                host, port = ep.rsplit(':', 1)
                port = int(port)
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                result = sock.connect_ex((host, port))
                sock.close()
                results['endpoints'][ep] = 'UP' if result == 0 else 'DOWN (connection refused)'
            except Exception as e:
                results['endpoints'][ep] = f'DOWN ({str(e)})'
        all_up = all(v == 'UP' for v in results['services'].values()) and all(v == 'UP' for v in results['endpoints'].values())
        results['overall_status'] = 'OK' if all_up else 'DEGRADED'
        return json.dumps(results, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)})


TOOL_SPEC = {
    "name": "system_health_check",
    "description": "Execute a series of diagnostic checks on the healthcare IT system infrastructure and report on the operational status of critical services, databases, and network endpoints, returning a consolidated health report with individual status flags for each monitored component.",
    "category": "system",
    "domain": "healthcare",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "services": {
            "type": "array",
            "items": {
                "type": "string",
                "description": "Name of a healthcare service to check (e.g., EHR, PACS, lab, billing)."
            },
            "description": "List of service names that should be running and reachable."
        },
        "endpoints": {
            "type": "array",
            "items": {
                "type": "string",
                "description": "URL or IP:port of an endpoint to verify connectivity."
            },
            "description": "Optional: List of network endpoints (URL or IP:port) to test connectivity to."
        },
        "timeout_seconds": {
            "type": "integer",
            "description": "Optional: Connection timeout in seconds per check (default 5).",
            "minimum": 1,
            "maximum": 120
        }
    },
    "required": [
        "services"
    ]
},
}
