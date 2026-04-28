"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        retention_days = data.get('retention_days')
        action = data.get('action')
        audit_type = data.get('audit_type')
        dry_run = data.get('dry_run', False)

        if not retention_days or retention_days < 1:
            return json.dumps({'error': 'retention_days must be >= 1'})
        if action not in ('archive', 'delete'):
            return json.dumps({'error': 'action must be archive or delete'})

        # Simulate database metadata lookup
        # In a real implementation, this would query the audit log database
        total_logs = 123456
        size_per_log = 0.002  # MB
        oldest_date = '2023-01-15'
        
        # Calculate approximate affected records
        days_old = 180  # simulated age of oldest log
        approximate_records = int(total_logs * (days_old / 365.0))
        reclaimed_size_mb = round(approximate_records * size_per_log, 2)
        
        if dry_run:
            result = {
                'dry_run': True,
                'estimated_records_affected': approximate_records,
                'estimated_reclaimed_size_mb': reclaimed_size_mb,
                'action': action,
                'retention_days': retention_days,
                'audit_type': audit_type or 'all'
            }
        else:
            # Simulate actual cleanup
            result = {
                'success': True,
                'records_cleaned': approximate_records,
                'reclaimed_size_mb': reclaimed_size_mb,
                'action': action,
                'audit_type': audit_type or 'all',
                'oldest_kept_date': '2024-10-01'  # simulated
            }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)})


TOOL_SPEC = {
    "name": "financial_audit_trail_cleaner",
    "description": "Remove or archive outdated financial audit log entries based on retention policies, returning the count of records affected and total reclaimed storage size.",
    "category": "system",
    "domain": "finance",
    "risk_level": "high",
    "schema": {
    "type": "object",
    "properties": {
        "retention_days": {
            "type": "integer",
            "description": "Number of days of audit logs to keep; entries older than this are eligible for cleanup. Must be >= 1."
        },
        "action": {
            "type": "string",
            "description": "Cleanup action to perform: 'archive' moves logs to cold storage, 'delete' permanently removes them.",
            "enum": [
                "archive",
                "delete"
            ]
        },
        "audit_type": {
            "type": "string",
            "description": "Optional: Filter by audit log category (e.g., 'payment', 'fraud', 'compliance', 'access'). If not provided, applies to all types."
        },
        "dry_run": {
            "type": "boolean",
            "description": "Optional: If true, simulate the cleanup without making changes and return estimated results."
        }
    },
    "required": [
        "retention_days",
        "action"
    ]
},
}
