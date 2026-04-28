"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        patient_id = data.get('patient_id')
        if not patient_id:
            return json.dumps({'error': 'patient_id is required'}, ensure_ascii=False)
        auto_merge = data.get('auto_merge', False)
        match_threshold = data.get('match_threshold', 0.85)
        # Simulate database lookup (in real system, query FHIR or SQL DB)
        # Mock patient record for demonstration
        mock_patient = {
            'id': patient_id,
            'name': 'John Doe',
            'dob': '1980-01-15',
            'phone': '555-1234',
            'last_updated': '2024-01-10'
        }
        # Simulate finding duplicates (real logic would query DB)
        duplicates = []  # In real implementation, search for records with same name+DOB+phone
        if auto_merge:
            # Simulate merge: keep latest record
            merged = mock_patient
            result = {
                'status': 'merged',
                'primary_patient_id': patient_id,
                'duplicates_removed': len(duplicates),
                'message': f'Merged {len(duplicates)} duplicate(s) into patient {patient_id}'
            }
        else:
            result = {
                'status': 'analyzed',
                'primary_patient_id': patient_id,
                'duplicates_found': len(duplicates),
                'message': f'Found {len(duplicates)} potential duplicate(s) for patient {patient_id}. Use auto_merge=true to remove them.'
            }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "patient_record_cleanup",
    "description": "Identify and remove duplicate patient records from a healthcare database system by matching on name, date of birth, and phone number. Returns a summary of duplicates found and removed, used for maintaining data hygiene and compliance.",
    "category": "system",
    "domain": "healthcare",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "patient_id": {
            "type": "string",
            "description": "Unique identifier of the patient record to be checked or deduplicated"
        },
        "auto_merge": {
            "type": "boolean",
            "description": "Optional: If True, automatically merge duplicates and keep the most recently updated record; if False, only report duplicates without merging"
        },
        "match_threshold": {
            "type": "number",
            "description": "Optional: Similarity score threshold (0.0 to 1.0) above which records are considered duplicates; default 0.85"
        }
    },
    "required": [
        "patient_id"
    ]
},
}
