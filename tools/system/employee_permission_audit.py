"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Analyze employee access permissions and generate compliance audit report."""
    import json
    from datetime import datetime, timedelta
    
    try:
        data = json.loads(payload)
        
        # Validate required fields
        for field in ['department', 'audit_period_days']:
            if field not in data:
                return json.dumps({"error": f"Missing required field: {field}"}, ensure_ascii=False)
        
        department = data['department']
        audit_period_days = int(data['audit_period_days'])
        min_risk = data.get('min_risk_level', 'low')
        include_details = data.get('include_details', False)
        
        # Simulated database of employees and their permissions
        employees = [
            {"id": "EMP001", "name": "Alice Johnson", "department": "Engineering", "active": True, "last_access": (datetime.now() - timedelta(days=2)).isoformat(), "permissions": ["code_repo_write", "deploy_prod", "server_logs"], "risk": "high"},
            {"id": "EMP002", "name": "Bob Smith", "department": "Finance", "active": False, "last_access": (datetime.now() - timedelta(days=120)).isoformat(), "permissions": ["financial_records", "payroll_access"], "risk": "critical"},
            {"id": "EMP003", "name": "Carol Davis", "department": "Sales", "active": True, "last_access": (datetime.now() - timedelta(days=1)).isoformat(), "permissions": ["crm_read", "customer_contact"], "risk": "low"},
            {"id": "EMP004", "name": "David Wilson", "department": "Engineering", "active": True, "last_access": (datetime.now() - timedelta(days=45)).isoformat(), "permissions": ["code_repo_write", "deploy_staging"], "risk": "medium"},
            {"id": "EMP005", "name": "Eve Martinez", "department": "HR", "active": False, "last_access": (datetime.now() - timedelta(days=200)).isoformat(), "permissions": ["employee_records", "salary_data"], "risk": "critical"},
        ]
        
        # Filter by department
        if department:
            employees = [e for e in employees if e['department'] == department]
        
        # Check inactivity and risk levels
        cutoff_date = datetime.now() - timedelta(days=audit_period_days)
        risk_levels = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        min_risk_val = risk_levels.get(min_risk, 1)
        
        flagged = []
        for emp in employees:
            risk_val = risk_levels.get(emp['risk'], 0)
            last_access = datetime.fromisoformat(emp['last_access'])
            inactive = last_access < cutoff_date
            
            if risk_val >= min_risk_val or (inactive and not emp['active']):
                entry = {
                    "employee_id": emp['id'],
                    "employee_name": emp['name'],
                    "department": emp['department'],
                    "status": "inactive" if not emp['active'] else "active",
                    "last_access": emp['last_access'],
                    "risk_level": emp['risk'],
                    "inactive_account": inactive
                }
                if include_details:
                    entry['permissions'] = emp['permissions']
                flagged.append(entry)
        
        # Sort by risk level (critical first)
        flagged.sort(key=lambda x: risk_levels.get(x['risk_level'], 0), reverse=True)
        
        result = {
            "audit_timestamp": datetime.now().isoformat(),
            "department_scoped": department if department else "All",
            "audit_period_days": audit_period_days,
            "total_employees_audited": len(employees),
            "flagged_accounts": len(flagged),
            "accounts": flagged,
            "summary": {
                "critical": len([a for a in flagged if a['risk_level'] == 'critical']),
                "high": len([a for a in flagged if a['risk_level'] == 'high']),
                "medium": len([a for a in flagged if a['risk_level'] == 'medium']),
                "low": len([a for a in flagged if a['risk_level'] == 'low'])
            }
        }
        
        return json.dumps(result, ensure_ascii=False, default=str)
        
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "employee_permission_audit",
    "description": "Analyze and report on employee access permissions across business systems, identifying inactive accounts, privilege escalations, and compliance violations for enterprise security management.",
    "category": "system",
    "domain": "business",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "department": {
            "type": "string",
            "description": "Business department to scope the audit (e.g. Sales, Engineering, Finance). Leave empty for company-wide audit.",
            "enum": [
                "Sales",
                "Engineering",
                "Finance",
                "HR",
                "Operations",
                ""
            ]
        },
        "audit_period_days": {
            "type": "integer",
            "description": "Number of days to look back for access activity analysis (accounts inactive beyond this period are flagged).",
            "minimum": 1,
            "maximum": 365
        },
        "min_risk_level": {
            "type": "string",
            "description": "Optional: Minimum risk level to include in the report. Only violations at or above this threshold are reported.",
            "enum": [
                "low",
                "medium",
                "high",
                "critical"
            ],
            "default": "low"
        },
        "include_details": {
            "type": "boolean",
            "description": "Optional: If True, includes detailed permission history and last access timestamps for each flagged account.",
            "default": False
        }
    },
    "required": [
        "department",
        "audit_period_days"
    ]
},
}
