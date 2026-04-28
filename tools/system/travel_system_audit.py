"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Audit travel system configurations."""
    import json
    try:
        data = json.loads(payload)
        report = data.get('system_report')
        version = data.get('compliance_version')
        if not report or not version:
            return json.dumps({'error': 'Missing required fields'}, ensure_ascii=False)
        
        passed = 0
        failed = 0
        warnings = 0
        details = []
        
        # Check user roles (basic)
        roles = report.get('user_roles', [])
        if not isinstance(roles, list):
            details.append({'check': 'User roles is a list', 'status': 'FAILED', 'message': 'user_roles must be a list'})
            failed += 1
        else:
            for r in roles:
                if 'role' not in r or 'permissions' not in r:
                    details.append({'check': 'Role structure', 'status': 'FAILED', 'message': f'Role missing required keys: {r}'})
                    failed += 1
                else:
                    if 'admin' in r.get('role', '').lower() and 'book' in r.get('permissions', []):
                        details.append({'check': 'Admin booking permission', 'status': 'WARNING', 'message': 'Admin role should not have direct booking permission (v1.0 rule)'})
                        warnings += 1
                    elif 'user' in r.get('role', '').lower() and 'admin_panel' in r.get('permissions', []):
                        details.append({'check': 'User restricted', 'status': 'FAILED', 'message': 'User role has admin_panel permission'})
                        failed += 1
                    else:
                        details.append({'check': f'Role {r["role"]}', 'status': 'PASSED', 'message': 'Permissions acceptable'})
                        passed += 1
        
        # Check booking rules
        rules = report.get('booking_rules', {})
        if not isinstance(rules, dict):
            details.append({'check': 'Booking rules is dict', 'status': 'FAILED', 'message': 'booking_rules must be an object'})
            failed += 1
        else:
            if 'max_days_ahead' in rules:
                if isinstance(rules['max_days_ahead'], (int, float)) and rules['max_days_ahead'] > 365:
                    details.append({'check': 'Max days ahead', 'status': 'WARNING', 'message': 'max_days_ahead > 365 may cause resource conflicts'})
                    warnings += 1
                else:
                    details.append({'check': 'Max days ahead', 'status': 'PASSED', 'message': f'Value {rules.get("max_days_ahead")}'})
                    passed += 1
            else:
                details.append({'check': 'Max days ahead present', 'status': 'FAILED', 'message': 'Missing required key'})
                failed += 1
            if 'allow_international' in rules:
                if not isinstance(rules['allow_international'], bool):
                    details.append({'check': 'Allow international', 'status': 'FAILED', 'message': 'Must be boolean'})
                    failed += 1
                else:
                    if version == 'v2.0' and rules['allow_international']:
                        details.append({'check': 'International booking (v2.0)', 'status': 'WARNING', 'message': 'v2.0 requires approval for international bookings'})
                        warnings += 1
                    else:
                        details.append({'check': 'Allow international', 'status': 'PASSED', 'message': str(rules['allow_international'])})
                        passed += 1
            else:
                details.append({'check': 'Allow international present', 'status': 'FAILED', 'message': 'Missing required key'})
                failed += 1
            if 'booking_tiers' in rules:
                if isinstance(rules['booking_tiers'], list) and len(rules['booking_tiers']) > 0:
                    details.append({'check': 'Booking tiers', 'status': 'PASSED', 'message': f'Found {len(rules["booking_tiers"])} tiers'})
                    passed += 1
                else:
                    details.append({'check': 'Booking tiers', 'status': 'WARNING', 'message': 'Empty or invalid tiers'})
                    warnings += 1
            else:
                details.append({'check': 'Booking tiers present', 'status': 'FAILED', 'message': 'Missing required key'})
                failed += 1
        
        # Check retention policies
        retention = report.get('retention_policies', {})
        if not isinstance(retention, dict):
            details.append({'check': 'Retention policies is dict', 'status': 'FAILED', 'message': 'retention_policies must be an object'})
            failed += 1
        else:
            if 'retention_days' in retention:
                val = retention['retention_days']
                if isinstance(val, (int, float)) and val > 0:
                    if val > 730 and version == 'v2.0':
                        details.append({'check': 'Retention days (v2.0)', 'status': 'FAILED', 'message': 'v2.0 limits retention to 730 days'})
                        failed += 1
                    else:
                        details.append({'check': 'Retention days', 'status': 'PASSED', 'message': f'{val} days'})
                        passed += 1
                else:
                    details.append({'check': 'Retention days', 'status': 'FAILED', 'message': 'Must be positive number'})
                    failed += 1
            else:
                details.append({'check': 'Retention days present', 'status': 'FAILED', 'message': 'Missing required key'})
                failed += 1
            if 'archive_enabled' in retention:
                if isinstance(retention['archive_enabled'], bool):
                    if version == 'v2.0' and not retention['archive_enabled']:
                        details.append({'check': 'Archive enabled (v2.0)', 'status': 'FAILED', 'message': 'v2.0 requires archive_enabled to be true'})
                        failed += 1
                    else:
                        details.append({'check': 'Archive enabled', 'status': 'PASSED', 'message': str(retention['archive_enabled'])})
                        passed += 1
                else:
                    details.append({'check': 'Archive enabled', 'status': 'FAILED', 'message': 'Must be boolean'})
                    failed += 1
            else:
                details.append({'check': 'Archive enabled present', 'status': 'FAILED', 'message': 'Missing required key'})
                failed += 1
        
        result = {
            'compliance_version': version,
            'summary': {
                'passed': passed,
                'failed': failed,
                'warnings': warnings
            },
            'details': details
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "travel_system_audit",
    "description": "Audit travel system configurations by parsing a JSON report of current system settings and comparing them against a set of compliance rules for travel booking, user roles, and data retention. Returns a structured audit report with passed, failed, and warning checks, used for system maintenance and compliance verification.",
    "category": "system",
    "domain": "travel",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "system_report": {
            "type": "object",
            "description": "JSON object containing current system settings: user roles (list of objects with 'role' and 'permissions'), booking rules (object with fields like 'max_days_ahead', 'allow_international', 'booking_tiers'), and retention policies (object with fields like 'retention_days', 'archive_enabled')."
        },
        "compliance_version": {
            "type": "string",
            "enum": [
                "v1.0",
                "v2.0"
            ],
            "description": "Version of compliance rules to use for comparison. v1.0 is basic, v2.0 adds stricter data privacy checks."
        }
    },
    "required": [
        "system_report",
        "compliance_version"
    ]
},
}
