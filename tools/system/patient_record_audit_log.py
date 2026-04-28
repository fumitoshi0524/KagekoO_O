"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    from datetime import datetime, timedelta

    try:
        data = json.loads(payload)
        patient_id = data.get('patient_id')
        if not patient_id:
            return json.dumps({'status': 'error', 'message': 'patient_id is required'}, ensure_ascii=False)

        today = datetime.now()
        default_start = today - timedelta(days=90)

        start_str = data.get('start_date', default_start.strftime('%Y-%m-%d'))
        end_str = data.get('end_date', today.strftime('%Y-%m-%d'))

        try:
            start_dt = datetime.strptime(start_str, '%Y-%m-%d')
            end_dt = datetime.strptime(end_str, '%Y-%m-%d')
        except ValueError:
            return json.dumps({'status': 'error', 'message': 'Invalid date format. Use YYYY-MM-DD.'}, ensure_ascii=False)

        if start_dt > end_dt:
            return json.dumps({'status': 'error', 'message': 'start_date must be before end_date.'}, ensure_ascii=False)

        user_filter = data.get('user_id', None)

        # Simulating an audit log database query (real implementation would query a secure audit store)
        # For demonstration, we generate sample entries based on filters
        audit_entries = []

        sample_entries = [
            {
                'timestamp': '2025-04-01T10:30:00Z',
                'user_id': 'dr_jones',
                'field_changed': 'allergies',
                'old_value': 'Penicillin',
                'new_value': 'Penicillin, Sulfa',
                'change_type': 'update'
            },
            {
                'timestamp': '2025-04-02T14:15:00Z',
                'user_id': 'nurse_smith',
                'field_changed': 'vital_signs.blood_pressure',
                'old_value': '120/80',
                'new_value': '130/85',
                'change_type': 'update'
            },
            {
                'timestamp': '2025-04-03T09:00:00Z',
                'user_id': 'admin_baker',
                'field_changed': 'demographics.address',
                'old_value': '123 Main St',
                'new_value': '456 Oak Ave',
                'change_type': 'update'
            }
        ]

        # Apply date filter
        for entry in sample_entries:
            entry_dt = datetime.strptime(entry['timestamp'].replace('Z', '+00:00')[:19], '%Y-%m-%dT%H:%M:%S')
            if start_dt <= entry_dt <= end_dt:
                if user_filter is None or entry['user_id'] == user_filter:
                    audit_entries.append(entry)

        result = {
            'status': 'success',
            'patient_id': patient_id,
            'total_entries': len(audit_entries),
            'entries': audit_entries
        }
        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "patient_record_audit_log",
    "description": "Query and retrieve the audit history of modifications made to a patient's electronic health record, returning a list of changes with timestamps, user identifiers, and field-level diffs for compliance monitoring and security review.",
    "category": "system",
    "domain": "healthcare",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "patient_id": {
            "type": "string",
            "description": "Unique identifier of the patient whose record audit log is requested (e.g., medical record number or UUID)."
        },
        "start_date": {
            "type": "string",
            "format": "date",
            "description": "Optional: Start date for filtering audit log entries (inclusive, format YYYY-MM-DD). If omitted, defaults to 90 days before current date."
        },
        "end_date": {
            "type": "string",
            "format": "date",
            "description": "Optional: End date for filtering audit log entries (inclusive, format YYYY-MM-DD). If omitted, defaults to current date."
        },
        "user_id": {
            "type": "string",
            "description": "Optional: Filter audit entries by the user identifier who performed the modification (e.g., doctor ID, nurse ID)."
        }
    },
    "required": [
        "patient_id"
    ]
},
}
