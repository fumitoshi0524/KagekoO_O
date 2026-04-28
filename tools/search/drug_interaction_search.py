"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        drugs = data.get('drugs', [])
        if not isinstance(drugs, list) or len(drugs) < 2:
            return json.dumps({'error': 'At least two drugs are required.'})
        severity_filter = data.get('severity_filter', None)
        valid_severities = ['major', 'moderate', 'minor', None]
        if severity_filter not in valid_severities:
            return json.dumps({'error': 'Invalid severity_filter. Must be one of: major, moderate, minor or null.'})
        # Simulated interaction knowledge base (in production, would query a real DB/API)
        knowledge_base = {
            ("warfarin", "aspirin"): {
                "severity": "major",
                "mechanism": "Additive anticoagulant effect",
                "recommendation": "Avoid concurrent use; monitor INR closely if unavoidable."
            },
            ("lisinopril", "spironolactone"): {
                "severity": "moderate",
                "mechanism": "Increased risk of hyperkalemia",
                "recommendation": "Monitor serum potassium and renal function."
            },
            ("metformin", "atorvastatin"): {
                "severity": "minor",
                "mechanism": "Possible minor decrease in metformin elimination",
                "recommendation": "No action usually required."
            },
            ("metformin", "lisinopril"): {
                "severity": "moderate",
                "mechanism": "May enhance hypoglycemic effect",
                "recommendation": "Monitor blood glucose levels."
            },
            ("aspirin", "ibuprofen"): {
                "severity": "major",
                "mechanism": "Increased risk of gastrointestinal bleeding",
                "recommendation": "Avoid combination; consider alternative analgesics."
            }
        }
        # Normalize drug names to lowercase and strip whitespace
        normalized_drugs = [drug.strip().lower() for drug in drugs]
        results = []
        for i in range(len(normalized_drugs)):
            for j in range(i+1, len(normalized_drugs)):
                pair = (normalized_drugs[i], normalized_drugs[j])
                reverse_pair = (normalized_drugs[j], normalized_drugs[i])
                interaction = knowledge_base.get(pair) or knowledge_base.get(reverse_pair)
                if interaction:
                    if severity_filter is None or interaction['severity'] == severity_filter:
                        results.append({
                            "drug_a": drugs[i],
                            "drug_b": drugs[j],
                            "severity": interaction['severity'],
                            "mechanism": interaction['mechanism'],
                            "recommendation": interaction['recommendation']
                        })
        # Sort results by severity (major first, then moderate, then minor)
        severity_order = {'major': 0, 'moderate': 1, 'minor': 2}
        results.sort(key=lambda x: severity_order.get(x['severity'], 3))
        return json.dumps({"interactions": results, "total": len(results)}, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "drug_interaction_search",
    "description": "Search for potential drug-drug interactions by querying a healthcare knowledge base with one or more drug names, returning interaction severity, mechanism, and clinical recommendation.",
    "category": "search",
    "domain": "healthcare",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "drugs": {
            "type": "array",
            "items": {
                "type": "string",
                "description": "Name of a single drug (generic or brand name)."
            },
            "description": "List of drug names to check for interactions (minimum 2)."
        },
        "severity_filter": {
            "type": "string",
            "enum": [
                "major",
                "moderate",
                "minor",
                None
            ],
            "description": "Optional: Filter results by interaction severity level."
        }
    },
    "required": [
        "drugs"
    ]
},
}
