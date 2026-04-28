"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    from datetime import datetime, timedelta

    try:
        data = json.loads(payload)
        department_id = data['department_id']
        include_deactivated = data.get('include_deactivated_users', False)
        threshold_days = data.get('threshold_days', 90)

        # Simulate role templates and user access records
        role_templates = {
            'sales': ['crm_read', 'crm_write', 'report_read'],
            'engineering': ['code_read', 'code_write', 'deploy'],
            'finance': ['invoice_read', 'invoice_write', 'payment_process']
        }
        # Mock user database (in reality, query LDAP/AD/database)
        users = {
            'user1': {'department': 'sales', 'roles': ['crm_read', 'crm_write'], 'active': True, 'last_change': (datetime.now() - timedelta(days=30)).isoformat()},
            'user2': {'department': 'sales', 'roles': ['crm_read', 'crm_write', 'admin'], 'active': True, 'last_change': (datetime.now() - timedelta(days=5)).isoformat()},
            'user3': {'department': 'engineering', 'roles': ['code_read'], 'active': True, 'last_change': (datetime.now() - timedelta(days=200)).isoformat()},
            'user4': {'department': 'engineering', 'roles': ['code_read', 'code_write', 'deploy', 'admin'], 'active': True, 'last_change': (datetime.now() - timedelta(days=10)).isoformat()},
            'user5': {'department': 'finance', 'roles': ['invoice_read'], 'active': False, 'last_change': (datetime.now() - timedelta(days=60)).isoformat()},
            'user6': {'department': 'finance', 'roles': ['invoice_read', 'invoice_write'], 'active': True, 'last_change': (datetime.now() - timedelta(days=20)).isoformat()}
        }

        if department_id not in role_templates:
            return json.dumps({'error': f'Unknown department_id: {department_id}'})

        template_roles = set(role_templates[department_id])
        threshold_date = datetime.now() - timedelta(days=threshold_days)
        audit_results = []
        policy_violations = []
        discrepancies = []

        for user_id, user_info in users.items():
            if user_info['department'] != department_id:
                continue
            if not include_deactivated and not user_info['active']:
                continue

            user_roles = set(user_info['roles'])
            missing_roles = template_roles - user_roles
            extra_roles = user_roles - template_roles

            last_change_dt = datetime.fromisoformat(user_info['last_change'])
            recent_change = last_change_dt >= threshold_date

            # Discrepancy: roles that are missing
            if missing_roles:
                for role in missing_roles:
                    discrepancies.append({
                        'user_id': user_id,
                        'issue': 'missing_role',
                        'role': role,
                        'active': user_info['active']
                    })

            # Violation: extra roles assigned recently
            if extra_roles and recent_change:
                for role in extra_roles:
                    policy_violations.append({
                        'user_id': user_id,
                        'issue': 'unauthorized_role_assignment',
                        'role': role,
                        'assigned_days_ago': (datetime.now() - last_change_dt).days
                    })

            # If roles exceed template by more than 2 (suspicious admin-like access)
            if len(extra_roles) > 2:
                policy_violations.append({
                    'user_id': user_id,
                    'issue': 'excessive_privileges',
                    'extra_role_count': len(extra_roles),
                    'assigned_days_ago': (datetime.now() - last_change_dt).days
                })

            # Summary for user
            audit_results.append({
                'user_id': user_id,
                'active': user_info['active'],
                'assigned_roles': user_info['roles'],
                'template_roles': list(template_roles),
                'missing_roles': list(missing_roles),
                'extra_roles': list(extra_roles),
                'last_role_change': user_info['last_change']
            })

        result = {
            'department': department_id,
            'audit_timestamp': datetime.now().isoformat(),
            'assessment_period_days': threshold_days,
            'included_deactivated': include_deactivated,
            'user_count': len(audit_results),
            'report': audit_results,
            'policy_violations': policy_violations,
            'role_discrepancies': discrepancies,
            'summary': {
                'total_users': len(audit_results),
                'users_with_discrepancies': len(discrepancies),
                'violations_found': len(policy_violations)
            }
        }
        return json.dumps(result, ensure_ascii=False)
    except KeyError as e:
        return json.dumps({'error': f'Missing required parameter: {e}'})
    except Exception as e:
        return json.dumps({'error': str(e)})


TOOL_SPEC = {
    "name": "department_access_auditor",
    "description": "Audit user access permissions across departments, comparing granted access levels against defined role templates, and returning a compliance report with discrepancies and policy violations for security review.",
    "category": "system",
    "domain": "business",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "department_id": {
            "type": "string",
            "description": "Unique identifier for the business department to audit (e.g., 'sales', 'engineering', 'finance')."
        },
        "include_deactivated_users": {
            "type": "boolean",
            "description": "Optional: Whether to include users whose accounts are currently deactivated in the audit report.",
            "default": false
        },
        "threshold_days": {
            "type": "integer",
            "description": "Optional: Number of days to look back for access changes; only consider changes within this period for violation detection (minimum 1, maximum 365).",
            "minimum": 1,
            "maximum": 365,
            "default": 90
        }
    },
    "required": [
        "department_id"
    ]
},
}
