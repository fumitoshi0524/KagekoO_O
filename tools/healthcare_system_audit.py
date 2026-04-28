"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    from datetime import datetime, timedelta
    import hashlib
    import random
    try:
        data = json.loads(payload)
        institution_id = data.get('institution_id')
        audit_type = data.get('audit_type')
        max_findings = data.get('max_findings', 50)
        include_historical = data.get('include_historical', False)
        
        if not institution_id or audit_type not in ['security', 'compliance', 'performance', 'full']:
            return json.dumps({'error': 'Invalid input: institution_id (string) and audit_type (enum) required'}, ensure_ascii=False)
        
        # Simulate system analysis with deterministic randomness based on input
        seed = institution_id + audit_type + str(int(include_historical))
        rng = random.Random(hashlib.sha256(seed.encode()).hexdigest())
        
        findings = []
        
        # Security checks (always run for security or full)
        if audit_type in ['security', 'full']:
            # Check for open ports
            for port in [3389, 22, 23, 445]:
                if rng.random() < 0.15:
                    findings.append({
                        'category': 'security',
                        'severity': 'high',
                        'type': 'open_port',
                        'port': port,
                        'description': f'Port {port} is exposed to the network, potential for unauthorized access.',
                        'recommendation': 'Restrict port access using firewall rules'
                    })
            # Check password policy
            if rng.random() < 0.2:
                findings.append({
                    'category': 'security',
                    'severity': 'medium',
                    'type': 'weak_password_policy',
                    'details': 'Password policy does not require special characters or minimum length',
                    'recommendation': 'Enforce password complexity: min 12 chars, uppercase, lowercase, digits, special chars'
                })
            # Check encryption
            if rng.random() < 0.1:
                findings.append({
                    'category': 'security',
                    'severity': 'critical',
                    'type': 'missing_encryption',
                    'details': 'Patient data not encrypted at rest in database storage',
                    'recommendation': 'Implement AES-256 encryption for all stored medical records'
                })
        
        # Compliance checks (always run for compliance or full)
        if audit_type in ['compliance', 'full']:
            # HIPAA audit log check
            if rng.random() < 0.3:
                findings.append({
                    'category': 'compliance',
                    'severity': 'high',
                    'type': 'audit_log_gap',
                    'details': 'Missing audit logs for 12% of EHR accesses in last 7 days',
                    'recommendation': 'Enable audit logging on all EHR modules and ensure logs are tamper-proof'
                })
            # Access control
            if rng.random() < 0.25:
                findings.append({
                    'category': 'compliance',
                    'severity': 'critical',
                    'type': 'unauthorized_access',
                    'details': '3 users with admin privileges have not been reviewed in 18 months',
                    'recommendation': 'Conduct quarterly access reviews and revoke unused accounts'
                })
            # GDPR data retention
            if rng.random() < 0.15:
                findings.append({
                    'category': 'compliance',
                    'severity': 'medium',
                    'type': 'data_retention_violation',
                    'details': 'Patient records retained beyond legal requirement by average of 2.3 years',
                    'recommendation': 'Implement automated data lifecycle management with retention policies'
                })
        
        # Performance checks (always run for performance or full)
        if audit_type in ['performance', 'full']:
            # Check response times
            if rng.random() < 0.2:
                findings.append({
                    'category': 'performance',
                    'severity': 'medium',
                    'type': 'slow_response',
                    'details': 'Average MR image retrieval response time > 15 seconds for 8% of queries',
                    'recommendation': 'Optimize database indexes and consider CDN for medical imaging data'
                })
            # CPU/memory usage
            cpu_usage = rng.uniform(30, 95)
            mem_usage = rng.uniform(40, 90)
            if cpu_usage > 80 or mem_usage > 85:
                findings.append({
                    'category': 'performance',
                    'severity': 'high',
                    'type': 'resource_bottleneck',
                    'details': f'Server resources: CPU {cpu_usage:.1f}%, Memory {mem_usage:.1f}% - near capacity',
                    'recommendation': 'Scale up server capacity or optimize resource-intensive queries'
                })
            # Disk I/O
            if rng.random() < 0.1:
                findings.append({
                    'category': 'performance',
                    'severity': 'low',
                    'type': 'high_disk_io',
                    'details': 'Disk I/O wait times are 4x normal during peak hours (10am-2pm)',
                    'recommendation': 'Consider using SSDs for database storage and increase read replicas'
                })
        
        # Trim findings to max
        if len(findings) > max_findings:
            findings = findings[:max_findings]
        
        # Prepare summary
        severity_counts = {}
        for f in findings:
            sev = f.get('severity', 'unknown')
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
        
        result = {
            'institution_id': institution_id,
            'audit_type': audit_type,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'findings_count': len(findings),
            'severity_counts': severity_counts,
            'findings': findings
        }
        
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "healthcare_system_audit",
    "description": "Analyze healthcare system configuration for security compliance and operational integrity, checking user permissions, audit logs, and data access patterns. Returns a structured report of vulnerabilities, misconfigurations, and recommended remediation steps.",
    "category": "system",
    "domain": "healthcare",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "institution_id": {
            "type": "string",
            "description": "Unique identifier for the healthcare institution (e.g., hospital ID, clinic code)."
        },
        "audit_type": {
            "type": "string",
            "enum": [
                "security",
                "compliance",
                "performance",
                "full"
            ],
            "description": "Scope of the audit: security checks permissions/passwords/encryption, compliance checks HIPAA/GDPR/regional rules, performance checks response times and resource usage, full runs all checks."
        },
        "max_findings": {
            "type": "integer",
            "description": "Optional: maximum number of findings to return (default 50, min 1, max 1000).",
            "minimum": 1,
            "maximum": 1000
        },
        "include_historical": {
            "type": "boolean",
            "description": "Optional: if true, include audit data from past 30 days in the analysis to spot trends.",
            "default": false
        }
    },
    "required": [
        "institution_id",
        "audit_type"
    ]
},
}
