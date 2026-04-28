"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        query = data.get('query')
        if not query:
            return json.dumps({'error': 'Missing required query parameter'}, ensure_ascii=False)
        max_results = min(data.get('max_results', 10), 50)
        icd_prefix = data.get('icd_code_prefix', '')
        # Simulated medical knowledge base
        conditions_db = [
            {'name': 'Type 2 Diabetes Mellitus', 'icd10': 'E11', 'symptoms': ['increased thirst', 'frequent urination', 'blurred vision'], 'treatments': ['insulin', 'metformin', 'dietary management']},
            {'name': 'Hypertension', 'icd10': 'I10', 'symptoms': ['headache', 'shortness of breath', 'nosebleeds'], 'treatments': ['ACE inhibitors', 'diuretics', 'lifestyle changes']},
            {'name': 'Asthma', 'icd10': 'J45', 'symptoms': ['wheezing', 'coughing', 'chest tightness'], 'treatments': ['inhalers', 'corticosteroids']},
            {'name': 'Major Depressive Disorder', 'icd10': 'F33', 'symptoms': ['sadness', 'loss of interest', 'fatigue'], 'treatments': ['SSRIs', 'cognitive behavioral therapy']},
            {'name': 'Acute Myocardial Infarction', 'icd10': 'I21', 'symptoms': ['chest pain', 'shortness of breath', 'sweating'], 'treatments': ['thrombolysis', 'angioplasty', 'stenting']},
            {'name': 'Covid-19', 'icd10': 'U07.1', 'symptoms': ['fever', 'cough', 'loss of taste or smell'], 'treatments': ['supportive care', 'antivirals', 'oxygen therapy']},
            {'name': 'Migraine', 'icd10': 'G43', 'symptoms': ['severe headache', 'nausea', 'sensitivity to light'], 'treatments': ['triptans', 'NSAIDS', 'lifestyle modifications']},
            {'name': 'Rheumatoid Arthritis', 'icd10': 'M06', 'symptoms': ['joint pain', 'swelling', 'morning stiffness'], 'treatments': ['DMARDs', 'biologics', 'physical therapy']}
        ]
        query_lower = query.lower().strip()
        results = []
        for cond in conditions_db:
            name_lower = cond['name'].lower()
            sym_lower = ' '.join(cond['symptoms']).lower()
            if query_lower in name_lower or query_lower in sym_lower:
                if icd_prefix and not cond['icd10'].startswith(icd_prefix):
                    continue
                results.append(cond)
        # Sort by relevance: exact name match first, then partial
        def sort_key(x):
            # Exact name match gets highest priority
            if x['name'].lower() == query_lower:
                return (0, 0)
            elif query_lower in x['name'].lower():
                return (1, x['name'].lower().index(query_lower))
            else:
                return (2, 0)
        results.sort(key=sort_key)
        results = results[:max_results]
        output = {
            'query': query,
            'total_found': len(results),
            'results': [
                {
                    'name': r['name'],
                    'icd10': r['icd10'],
                    'symptoms': r['symptoms'][:5],
                    'treatments': r['treatments'][:3]
                } for r in results
            ]
        }
        return json.dumps(output, ensure_ascii=False)
    except json.JSONDecodeError as e:
        return json.dumps({'error': f'Invalid JSON: {str(e)}'}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': f'Processing error: {str(e)}'}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "medical_condition_search",
    "description": "Search for medical conditions and diseases by name or symptom keywords, returning matching conditions with associated ICD-10 codes, common symptoms, and typical treatment categories.",
    "category": "search",
    "domain": "healthcare",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Free text search string for condition name or symptom (e.g., 'diabetes', 'chest pain')"
        },
        "max_results": {
            "type": "integer",
            "description": "Optional: maximum number of results to return (default 10, max 50)"
        },
        "icd_code_prefix": {
            "type": "string",
            "description": "Optional: filter results by ICD-10 chapter prefix (e.g., 'E' for endocrine, 'I' for circulatory)"
        }
    },
    "required": [
        "query"
    ]
},
}
