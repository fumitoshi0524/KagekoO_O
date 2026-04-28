"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        condition = data.get('condition')
        intervention = data.get('intervention', '')
        location = data.get('location', '')
        status = data.get('status', 'all')
        max_results = data.get('max_results', 10)

        if not condition:
            return json.dumps({'error': 'condition parameter is required'}, ensure_ascii=False)

        # Simulated realistic search logic using a mock dataset
        # In production, this would query ClinicalTrials.gov API or similar
        mock_trials = [
            {'nct_id': 'NCT04280705', 'title': 'Remdesivir for Treatment of COVID-19', 'status': 'completed', 'phase': 'Phase 3', 'condition': 'COVID-19', 'intervention': 'Remdesivir', 'location': 'USA'},
            {'nct_id': 'NCT04381936', 'title': 'Hydroxychloroquine for COVID-19 Prophylaxis', 'status': 'terminated', 'phase': 'Phase 2', 'condition': 'COVID-19', 'intervention': 'Hydroxychloroquine', 'location': 'France'},
            {'nct_id': 'NCT02573259', 'title': 'Metformin in Gestational Diabetes', 'status': 'completed', 'phase': 'Phase 4', 'condition': 'gestational diabetes', 'intervention': 'Metformin', 'location': 'USA'},
            {'nct_id': 'NCT01891331', 'title': 'Radiation Therapy for Breast Cancer', 'status': 'active', 'phase': 'Phase 3', 'condition': 'breast cancer', 'intervention': 'radiation therapy', 'location': 'Canada'},
        ]

        results = []
        for trial in mock_trials:
            if condition.lower() not in trial['condition'].lower():
                continue
            if intervention and intervention.lower() not in trial['intervention'].lower():
                continue
            if location and location.lower() not in trial['location'].lower():
                continue
            if status != 'all' and trial['status'] != status:
                continue
            results.append(trial)

        # Sort by relevance (exact match first) and limit
        results.sort(key=lambda x: (x['condition'].lower() == condition.lower()), reverse=True)
        results = results[:max_results]

        return json.dumps({'trials': results, 'total_found': len(results)}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "clinical_trial_search",
    "description": "Search for active or completed clinical trials by condition, drug, or location, returning matching trial identifiers, titles, status, phase, and recruitment status for patient recruitment or research analysis.",
    "category": "search",
    "domain": "healthcare",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "condition": {
            "type": "string",
            "description": "Medical condition or disease name (e.g., diabetes, breast cancer). Use standard terminology for better results."
        },
        "intervention": {
            "type": "string",
            "description": "Optional: Drug name, device, or procedure used in the trial (e.g., metformin, radiation therapy)."
        },
        "location": {
            "type": "string",
            "description": "Optional: City, state, or country to narrow trials by geographic site."
        },
        "status": {
            "type": "string",
            "enum": [
                "active",
                "completed",
                "recruiting",
                "terminated",
                "all"
            ],
            "description": "Optional: Recruitment or overall trial status. Default is 'all'."
        },
        "max_results": {
            "type": "integer",
            "minimum": 1,
            "maximum": 100,
            "description": "Optional: Maximum number of trial records to return (1-100). Default is 10."
        }
    },
    "required": [
        "condition"
    ]
},
}
