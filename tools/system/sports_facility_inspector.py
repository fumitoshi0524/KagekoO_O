"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    import datetime
    try:
        data = json.loads(payload)
        facility_name = data.get('facility_name')
        facility_type = data.get('facility_type')
        inspector_name = data.get('inspector_name')
        checklist_items = data.get('checklist_items')
        if not all([facility_name, facility_type, inspector_name, checklist_items]):
            return json.dumps({'error': 'Missing required fields: facility_name, facility_type, inspector_name, checklist_items'})
        if not isinstance(checklist_items, list) or len(checklist_items) == 0:
            return json.dumps({'error': 'checklist_items must be a non-empty array'})
        
        total_items = len(checklist_items)
        pass_count = 0
        fail_count = 0
        na_count = 0
        failures = []
        
        severity_weights = {'low': 1, 'medium': 2, 'high': 3}
        total_severity_score = 0
        
        for item in checklist_items:
            status = item.get('status')
            if status == 'pass':
                pass_count += 1
            elif status == 'fail':
                fail_count += 1
                severity = item.get('severity', 'medium')
                if severity not in severity_weights:
                    severity = 'medium'
                total_severity_score += severity_weights[severity]
                failures.append({
                    'item_id': item.get('item_id'),
                    'description': item.get('description'),
                    'severity': severity,
                    'notes': item.get('notes', '')
                })
            elif status == 'not_applicable':
                na_count += 1
        
        # Calculate overall condition score: 0-100, starting at 100, subtract based on failures
        max_penalty = total_items * 3  # worst case all high severity
        if total_items > 0:
            raw_score = 100 - (total_severity_score / max_penalty) * 100
            overall_score = round(max(0, min(100, raw_score)), 1)
        else:
            overall_score = 100.0
        
        # Determine overall rating
        if overall_score >= 90:
            rating = 'excellent'
        elif overall_score >= 70:
            rating = 'good'
        elif overall_score >= 50:
            rating = 'fair'
        else:
            rating = 'poor'
        
        result = {
            'inspection_report': {
                'facility_name': facility_name,
                'facility_type': facility_type,
                'inspector_name': inspector_name,
                'inspection_date': datetime.datetime.now().isoformat(),
                'summary': {
                    'total_items_checked': total_items,
                    'passed': pass_count,
                    'failed': fail_count,
                    'not_applicable': na_count,
                    'failure_details': failures,
                    'overall_condition_score': overall_score,
                    'overall_rating': rating
                }
            }
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': f'Unexpected error: {str(e)}'})


TOOL_SPEC = {
    "name": "sports_facility_inspector",
    "description": "Perform a structured inspection of a sports facility (e.g., gym, stadium, field) based on a checklist of safety and maintenance criteria, then generate a detailed inspection report with pass/fail status for each item, severity ratings for failures, and an overall facility condition score.",
    "category": "system",
    "domain": "sports",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "facility_name": {
            "type": "string",
            "description": "Official name of the sports facility to inspect (e.g., 'City Sports Complex', 'Downtown Fitness Center')",
            "examples": [
                "Oakwood Community Gym",
                "Westside Stadium"
            ]
        },
        "facility_type": {
            "type": "string",
            "description": "Type of sports facility",
            "enum": [
                "indoor_gym",
                "outdoor_field",
                "swimming_pool",
                "ice_rink",
                "tennis_court",
                "stadium",
                "multi_purpose"
            ],
            "examples": [
                "indoor_gym",
                "stadium"
            ]
        },
        "inspector_name": {
            "type": "string",
            "description": "Full name of the inspector performing the check",
            "examples": [
                "Jane Doe",
                "John Smith"
            ]
        },
        "checklist_items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "string",
                        "description": "Unique identifier for the checklist item (e.g., 'FLR-001', 'EQP-002')",
                        "examples": [
                            "FLR-001",
                            "EQP-002"
                        ]
                    },
                    "description": {
                        "type": "string",
                        "description": "Description of the inspection criterion",
                        "examples": [
                            "Floor surface is free of cracks and tripping hazards",
                            "Emergency exit signs are illuminated"
                        ]
                    },
                    "status": {
                        "type": "string",
                        "enum": [
                            "pass",
                            "fail",
                            "not_applicable"
                        ],
                        "description": "Inspection outcome for this item"
                    },
                    "severity": {
                        "type": "string",
                        "enum": [
                            "low",
                            "medium",
                            "high"
                        ],
                        "description": "Optional: severity if status is 'fail' (default: 'medium')"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Optional: additional inspector comments or observations"
                    }
                },
                "required": [
                    "item_id",
                    "description",
                    "status"
                ]
            },
            "description": "List of checklist items with inspection results",
            "minItems": 1
        }
    },
    "required": [
        "facility_name",
        "facility_type",
        "inspector_name",
        "checklist_items"
    ]
},
}
