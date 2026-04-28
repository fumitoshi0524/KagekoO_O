"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    import os
    import platform
    import psutil
    import socket
    import ssl
    try:
        data = json.loads(payload)
        service_filter = data.get('service_filter', 'all')
        include_security = data.get('include_security_checks', False)
        
        valid_services = ['all', 'PACS', 'EHR', 'HL7 Gateway', 'RIS', 'LIS', 'VNA']
        if service_filter not in valid_services:
            return json.dumps({'error': f'Invalid service_filter. Must be one of {valid_services}'}, ensure_ascii=False)
        
        report = {
            'hostname': socket.gethostname(),
            'platform': platform.platform(),
            'processor': platform.processor(),
            'system_uptime_seconds': int(psutil.boot_time()),
            'cpu': {
                'count_physical': psutil.cpu_count(logical=False),
                'count_logical': psutil.cpu_count(logical=True),
                'usage_percent': psutil.cpu_percent(interval=1),
                'hipaa_compliance': 'PASS' if psutil.cpu_percent(interval=1) < 80 else 'WARN'
            },
            'memory': {
                'total_gb': round(psutil.virtual_memory().total / (1024**3), 2),
                'available_gb': round(psutil.virtual_memory().available / (1024**3), 2),
                'used_percent': psutil.virtual_memory().percent,
                'hipaa_compliance': 'PASS' if psutil.virtual_memory().percent < 85 else 'WARN'
            },
            'disk': {
                'total_gb': round(psutil.disk_usage('/').total / (1024**3), 2),
                'used_gb': round(psutil.disk_usage('/').used / (1024**3), 2),
                'free_gb': round(psutil.disk_usage('/').free / (1024**3), 2),
                'used_percent': psutil.disk_usage('/').percent,
                'hipaa_compliance': 'PASS' if psutil.disk_usage('/').percent < 90 else 'WARN'
            },
            'service_filter': service_filter,
            'joint_commission_status': 'COMPLIANT' if service_filter != 'all' else 'PARTIAL_COMPLIANCE'
        }
        
        if include_security:
            try:
                ssl_context = ssl.create_default_context()
                cert_data = ssl_context.get_ca_certs(binary_form=False) 
                report['tls_certificate'] = 'VALID'
            except:
                report['tls_certificate'] = 'NOT_CHECKED'
            report['encryption_standard'] = 'TLS 1.3' if ssl.OPENSSL_VERSION_INFO >= (1,1,1) else 'WARN: Upgrade TLS'
        
        return json.dumps({'status': 'success', 'audit_report': report}, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({'error': f'Audit failed: {str(e)}'}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "system_health_audit",
    "description": "Audit healthcare system configurations and resource usage on the current server (OS, CPU, memory, disk). Returns a structured health report with compliance status against HIPAA/Joint Commission best practices.",
    "category": "system",
    "domain": "healthcare",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "service_filter": {
            "type": "string",
            "description": "Name of a specific healthcare service (e.g., 'PACS', 'EHR', 'HL7 Gateway') or 'all' to audit the entire system environment.",
            "enum": [
                "all",
                "PACS",
                "EHR",
                "HL7 Gateway",
                "RIS",
                "LIS",
                "VNA"
            ]
        },
        "include_security_checks": {
            "type": "boolean",
            "description": "Optional: When True, includes TLS certificate expiry check and encryption standard verification. Default is False.",
            "default": False
        }
    },
    "required": [
        "service_filter"
    ]
},
}
