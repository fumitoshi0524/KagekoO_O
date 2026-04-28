"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Check for potential drug-drug interactions between two or more medications."""
    import json
    try:
        data = json.loads(payload)
        medications = data.get('medications')
        if not medications or len(medications) < 2:
            return json.dumps({'error': 'At least two medications required'}, ensure_ascii=False)
        
        include_otc = data.get('include_over_the_counter', True)
        max_results = min(data.get('max_results', 20), 100)

        # Knowledge base of drug interactions (simplified example)
        interaction_db = [
            {
                'drug_a': 'Warfarin',
                'drug_b': 'Aspirin',
                'severity': 'major',
                'description': 'Increased risk of bleeding. Avoid concurrent use if possible.',
                'recommendation': 'Monitor INR closely; consider alternative analgesic.'
            },
            {
                'drug_a': 'Warfarin',
                'drug_b': 'Ibuprofen',
                'severity': 'major',
                'description': 'Increased bleeding risk due to antiplatelet effects.',
                'recommendation': 'Use alternative pain reliever (e.g., acetaminophen).'
            },
            {
                'drug_a': 'Lisinopril',
                'drug_b': 'Potassium supplements',
                'severity': 'major',
                'description': 'Risk of hyperkalemia (elevated potassium).',
                'recommendation': 'Monitor potassium levels; avoid potassium supplements.'
            },
            {
                'drug_a': 'Metformin',
                'drug_b': 'Contrast dye',
                'severity': 'major',
                'description': 'Risk of lactic acidosis in patients with renal impairment.',
                'recommendation': 'Discontinue metformin 48 hours before contrast procedure.'
            },
            {
                'drug_a': 'Simvastatin',
                'drug_b': 'Grapefruit juice',
                'severity': 'moderate',
                'description': 'Increased statin exposure, risk of myopathy.',
                'recommendation': 'Avoid large quantities of grapefruit juice; consider alternative statin.'
            }
        ]

        # Extract drug names
        drug_names = [m.get('name', '').lower() for m in medications]
        
        # Find interactions
        found_interactions = []
        for interaction in interaction_db:
            drug_a = interaction['drug_a'].lower()
            drug_b = interaction['drug_b'].lower()
            if drug_a in drug_names and drug_b in drug_names:
                found_interactions.append(interaction)
            elif drug_b in drug_names and drug_a in drug_names:
                # Swap to keep consistent order
                swapped = {
                    'drug_a': interaction['drug_b'],
                    'drug_b': interaction['drug_a'],
                    'severity': interaction['severity'],
                    'description': interaction['description'],
                    'recommendation': interaction['recommendation']
                }
                found_interactions.append(swapped)

        # Limit results
        if len(found_interactions) > max_results:
            found_interactions = found_interactions[:max_results]

        # Count severity levels
        severity_counts = {'contraindicated': 0, 'major': 0, 'moderate': 0, 'minor': 0}
        for interaction in found_interactions:
            sev = interaction['severity']
            if sev in severity_counts:
                severity_counts[sev] += 1

        result = {
            'interactions': found_interactions,
            'total_interactions': len(found_interactions),
            'severity_summary': severity_counts
        }
        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "check_drug_interaction",
    "description": "Check for potential drug-drug interactions between two or more medications using a knowledge base of known interaction rules and severity levels, returning a list of interactions, their severity (contraindicated, major, moderate, minor), and recommended clinical actions.",
    "category": "operations",
    "domain": "healthcare",
    "risk_level": "medium",
    "schema": {
    "type": "object",
    "properties": {
        "medications": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Medication name (generic or brand name), e.g., 'Warfarin', 'Aspirin'."
                    },
                    "rxnorm_id": {
                        "type": "string",
                        "description": "Optional RxNorm identifier for precise matching."
                    }
                },
                "required": [
                    "name"
                ]
            },
            "description": "List of medications to check for interactions. Minimum 2 medications required."
        },
        "include_over_the_counter": {
            "type": "boolean",
            "description": "Optional: Whether to include interactions with over-the-counter medications. Default True."
        },
        "max_results": {
            "type": "integer",
            "description": "Optional: Maximum number of interactions to return. Default 20, max 100."
        }
    },
    "required": [
        "medications"
    ]
},
}
