"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    from datetime import datetime, timedelta
    import random

    try:
        data = json.loads(payload)
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        outcome = data.get('outcome', 'all')
        resource_type = data.get('resource_type', 'all')
        max_results = data.get('max_results', 100)

        if not start_date or not end_date:
            return json.dumps({'error': 'start_date and end_date are required'})

        try:
            datetime.strptime(start_date, '%Y-%m-%d')
            datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            return json.dumps({'error': 'Dates must be in YYYY-MM-DD format'})

        if not isinstance(max_results, int) or max_results < 1 or max_results > 1000:
            max_results = 100

        users = ['dr.smith', 'nurse.johnson', 'admin.williams', 'technician.lee', 'dr.patel', 'nurse.garcia', 'system.backup', 'api.gateway']
        resources = ['patient_record', 'prescription_system', 'imaging_system', 'lab_results', 'admin_panel']
        devices = ['workstation-01', 'workstation-02', 'tablet-03', 'pharmacy-kiosk-01', 'mri-scanner-01', 'lab-analyzer-02']
        actions = ['view', 'update', 'create', 'delete', 'export', 'print']

        records = []
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')

        current = start
        while current <= end and len(records) < max_results:
            for _ in range(random.randint(1, 5)):
                if len(records) >= max_results:
                    break
                timestamp = current + timedelta(hours=random.randint(0, 23), minutes=random.randint(0, 59))
                rec_outcome = random.choice(['granted', 'denied'])
                rec_resource = random.choice(resources)
                rec_user = random.choice(users)
                rec_device = random.choice(devices)
                rec_action = random.choice(actions)

                if outcome != 'all' and rec_outcome != outcome:
                    continue
                if resource_type != 'all' and rec_resource != resource_type:
                    continue

                records.append({
                    'timestamp': timestamp.isoformat(),
                    'user': rec_user,
                    'device': rec_device,
                    'resource': rec_resource,
                    'action': rec_action,
                    'outcome': rec_outcome,
                    'reason': 'Invalid credentials' if rec_outcome == 'denied' else 'Authenticated OK'
                })
            current += timedelta(days=1)

        result = {
            'total_records': len(records),
            'start_date': start_date,
            'end_date': end_date,
            'filters_applied': {
                'outcome': outcome,
                'resource_type': resource_type
            },
            'records': records[:max_results]
        }
        return json.dumps(result, ensure_ascii=False, default=str)

    except json.JSONDecodeError:
        return json.dumps({'error': 'Invalid JSON payload'})
    except Exception as e:
        return json.dumps({'error': f'Unexpected error: {str(e)}'})


TOOL_SPEC = {
    "name": "audit_healthcare_access",
    "description": "Retrieve and filter system access audit logs for healthcare personnel and devices. Returns a list of access events with timestamps, user/device identifiers, resource accessed, and outcome (granted/denied). Used for HIPAA compliance review and security incident investigations.",
    "category": "system",
    "domain": "healthcare",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "start_date": {
            "type": "string",
            "description": "Start date for the audit window in YYYY-MM-DD format"
        },
        "end_date": {
            "type": "string",
            "description": "End date for the audit window in YYYY-MM-DD format"
        },
        "outcome": {
            "type": "string",
            "description": "Optional: Filter by access outcome. Allowed values: 'granted', 'denied', 'all'",
            "enum": [
                "granted",
                "denied",
                "all"
            ]
        },
        "resource_type": {
            "type": "string",
            "description": "Optional: Filter by type of resource accessed. Allowed values: 'patient_record', 'prescription_system', 'imaging_system', 'lab_results', 'admin_panel', 'all'",
            "enum": [
                "patient_record",
                "prescription_system",
                "imaging_system",
                "lab_results",
                "admin_panel",
                "all"
            ]
        },
        "max_results": {
            "type": "integer",
            "description": "Optional: Maximum number of audit records to return (1-1000). Default is 100.",
            "minimum": 1,
            "maximum": 1000,
            "default": 100
        }
    },
    "required": [
        "start_date",
        "end_date"
    ]
},
}
