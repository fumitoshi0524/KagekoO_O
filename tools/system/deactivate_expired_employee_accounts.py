"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Deactivate expired employee accounts and return audit summary."""
    import json
    from datetime import datetime, timezone

    try:
        data = json.loads(payload)
        dry_run = data.get('dry_run', True)
        employee_ids = data.get('employee_ids', [])
        notify_manager = data.get('notify_manager', False)

        # Simulate database of active employees with contract end dates
        # In production, this would query an HR system or LDAP
        employee_db = {
            'EMP-001': {'name': 'Alice Johnson', 'end_date': '2024-11-15', 'manager_email': 'mgr1@company.com'},
            'EMP-002': {'name': 'Bob Smith', 'end_date': '2025-06-01', 'manager_email': 'mgr2@company.com'},
            'EMP-003': {'name': 'Carol Lee', 'end_date': '2024-12-31', 'manager_email': 'mgr3@company.com'},
            'EMP-004': {'name': 'David Chen', 'end_date': '2025-01-20', 'manager_email': 'mgr1@company.com'},
            'EMP-005': {'name': 'Eva Martinez', 'end_date': '2024-10-01', 'manager_email': 'mgr4@company.com'}
        }

        filter_ids = employee_ids if employee_ids else list(employee_db.keys())
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        today_dt = datetime.now(timezone.utc)

        deactivated = []
        skipped = []
        errors = []

        for emp_id in filter_ids:
            if emp_id not in employee_db:
                skipped.append({'employee_id': emp_id, 'reason': 'Employee not found in system'})
                continue

            record = employee_db[emp_id]
            try:
                end_date = datetime.strptime(record['end_date'], '%Y-%m-%d').replace(tzinfo=timezone.utc)
            except ValueError:
                errors.append({'employee_id': emp_id, 'reason': 'Invalid end date format'})
                continue

            if end_date < today_dt:
                if not dry_run:
                    # In production: call HR API deactivate endpoint, revoke access tokens, log action
                    pass
                action = 'Would deactivate' if dry_run else 'Deactivated'
                deactivated.append({
                    'employee_id': emp_id,
                    'name': record['name'],
                    'end_date': record['end_date'],
                    'action': f'{action} (manager notified: {notify_manager})' if (notify_manager and not dry_run) else action
                })
            else:
                days_remaining = (end_date - today_dt).days
                skipped.append({
                    'employee_id': emp_id,
                    'name': record['name'],
                    'end_date': record['end_date'],
                    'reason': f'Contract still active ({days_remaining} days remaining)'
                })

        result = {
            'executed_at': today,
            'dry_run': dry_run,
            'total_checked': len(filter_ids),
            'total_deactivated': len(deactivated),
            'total_skipped': len(skipped),
            'total_errors': len(errors),
            'deactivated_accounts': deactivated,
            'skipped_accounts': skipped,
            'error_list': errors if errors else None
        }

        return json.dumps(result, ensure_ascii=False, indent=2)

    except json.JSONDecodeError as e:
        return json.dumps({'error': f'Invalid JSON payload: {str(e)}'}, ensure_ascii=False)
    except KeyError as e:
        return json.dumps({'error': f'Missing required field: {str(e)}'}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': f'Unexpected error: {str(e)}'}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "deactivate_expired_employee_accounts",
    "description": "Performs automated deactivation of employee accounts whose contract end date has passed the current system date, logs each account action, and returns a summary report with total processed, deactivated, and skipped counts used for access compliance audits.",
    "category": "system",
    "domain": "business",
    "risk_level": "high",
    "schema": {
    "type": "object",
    "properties": {
        "dry_run": {
            "type": "boolean",
            "description": "Optional: When True, simulates the deactivation run without making actual changes, returning which accounts would be affected."
        },
        "employee_ids": {
            "type": "array",
            "description": "Optional: List of specific employee IDs to restrict the deactivation check to, leaving empty to scan all active accounts.",
            "items": {
                "type": "string",
                "description": "Employee account identifier in the HR system (e.g., EMP-XXXXX format)."
            }
        },
        "notify_manager": {
            "type": "boolean",
            "description": "Optional: When True, triggers an email notification to the account manager about the deactivation."
        }
    },
    "required": [
        "dry_run"
    ]
},
}
