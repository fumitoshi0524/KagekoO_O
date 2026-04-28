"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Register a new scientific experiment in the system."""
    import json
    try:
        data = json.loads(payload)
        title = data.get('title')
        pi = data.get('principal_investigator')
        dept = data.get('department')
        status = data.get('status')
        if not title or not pi or not dept or not status:
            return json.dumps({'error': 'Missing required fields: title, principal_investigator, department, status'}, ensure_ascii=False)
        valid_statuses = ['planned', 'in_progress', 'completed', 'cancelled']
        if status not in valid_statuses:
            return json.dumps({'error': f'Invalid status: {status}. Must be one of {valid_statuses}'}, ensure_ascii=False)
        # Simulate registration logic: generate a unique experiment ID
        import hashlib, time
        raw = f'{title}{pi}{dept}{time.time()}'
        exp_id = hashlib.sha256(raw.encode()).hexdigest()[:12]
        result = {
            'experiment_id': exp_id,
            'title': title,
            'principal_investigator': pi,
            'department': dept,
            'funding_source': data.get('funding_source', ''),
            'status': status,
            'message': 'Experiment registered successfully.'
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "register_scientific_experiment",
    "description": "Register a new scientific experiment in the system database, capturing key metadata such as title, principal investigator, department, funding source, and status, and return the generated experiment ID with a success confirmation for tracking and audit purposes.",
    "category": "system",
    "domain": "science",
    "risk_level": "moderate",
    "schema": {
    "type": "object",
    "properties": {
        "title": {
            "type": "string",
            "description": "The full title of the scientific experiment or research study."
        },
        "principal_investigator": {
            "type": "string",
            "description": "Full name of the principal investigator leading the experiment."
        },
        "department": {
            "type": "string",
            "description": "Department or research group under which the experiment is conducted."
        },
        "funding_source": {
            "type": "string",
            "description": "Optional: Name of the funding agency or grant that supports the experiment."
        },
        "status": {
            "type": "string",
            "enum": [
                "planned",
                "in_progress",
                "completed",
                "cancelled"
            ],
            "description": "Current lifecycle status of the experiment."
        }
    },
    "required": [
        "title",
        "principal_investigator",
        "department",
        "status"
    ]
},
}
