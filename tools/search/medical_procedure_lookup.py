"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        search_term = data.get('search_term', '').strip()
        if not search_term or len(search_term) < 2:
            return json.dumps({'error': 'search_term must be at least 2 characters'}, ensure_ascii=False)
        max_results = min(max(data.get('max_results', 10), 1), 20)
        code_type = data.get('code_type')
        
        # Simulated procedure database (real implementation would query a medical API)
        database = [
            {"name": "Appendectomy", "cpt": "44970", "icd10pcs": "0DTJ4ZZ", "description": "Surgical removal of the appendix", "duration_minutes": 60, "anesthesia": "General", "cost_range": "$10,000-$35,000"},
            {"name": "Total Knee Replacement", "cpt": "27447", "icd10pcs": "0SRD0J9", "description": "Replacement of knee joint with prosthesis", "duration_minutes": 120, "anesthesia": "Spinal or General", "cost_range": "$20,000-$50,000"},
            {"name": "Cataract Surgery", "cpt": "66984", "icd10pcs": "08BJ3ZZ", "description": "Removal of cataract and lens replacement", "duration_minutes": 30, "anesthesia": "Local with sedation", "cost_range": "$3,000-$6,000 per eye"},
            {"name": "Coronary Artery Bypass Graft (CABG)", "cpt": "33533", "icd10pcs": "021209W", "description": "Bypass blocked coronary arteries using grafts", "duration_minutes": 180, "anesthesia": "General", "cost_range": "$50,000-$150,000"},
            {"name": "Cesarean Section", "cpt": "59510", "icd10pcs": "10D00Z0", "description": "Delivery of baby through surgical incision in abdomen", "duration_minutes": 45, "anesthesia": "Regional (epidural/spinal)", "cost_range": "$15,000-$25,000"},
            {"name": "Magnetic Resonance Imaging (MRI) Brain", "cpt": "70551", "icd10pcs": "B0300ZZ", "description": "Non-invasive imaging of brain structures", "duration_minutes": 45, "anesthesia": "None", "cost_range": "$1,000-$3,500"},
            {"name": "Colonoscopy", "cpt": "45378", "icd10pcs": "0DJD8ZZ", "description": "Endoscopic examination of the colon", "duration_minutes": 30, "anesthesia": "Conscious sedation", "cost_range": "$1,500-$4,000"},
            {"name": "Hip Replacement", "cpt": "27130", "icd10pcs": "0SRB0J9", "description": "Replacement of hip joint with prosthesis", "duration_minutes": 120, "anesthesia": "General or Spinal", "cost_range": "$25,000-$60,000"},
            {"name": "Laparoscopic Cholecystectomy", "cpt": "47562", "icd10pcs": "0FT44ZZ", "description": "Minimally invasive removal of gallbladder", "duration_minutes": 60, "anesthesia": "General", "cost_range": "$10,000-$25,000"},
            {"name": "Spinal Fusion (Lumbar)", "cpt": "22533", "icd10pcs": "0RG1070", "description": "Fusion of two or more lumbar vertebrae", "duration_minutes": 180, "anesthesia": "General", "cost_range": "$40,000-$100,000"},
            {"name": "Mastectomy (Simple)", "cpt": "19303", "icd10pcs": "0HBT0ZZ", "description": "Surgical removal of entire breast tissue", "duration_minutes": 120, "anesthesia": "General", "cost_range": "$15,000-$40,000"},
            {"name": "Tonsillectomy", "cpt": "42825", "icd10pcs": "0CTP0ZZ", "description": "Surgical removal of the tonsils", "duration_minutes": 30, "anesthesia": "General", "cost_range": "$4,000-$8,000"}
        ]
        
        # Filter by code_type if provided
        if code_type:
            if code_type == 'cpt':
                database = [p for p in database if p.get('cpt')]
            elif code_type == 'icd10pcs':
                database = [p for p in database if p.get('icd10pcs')]
        
        # Search by term (case-insensitive partial match on name)
        lower_search = search_term.lower()
        results = [p for p in database if lower_search in p['name'].lower()]
        
        # Limit results
        results = results[:max_results]
        
        if not results:
            return json.dumps({'message': 'No procedures found matching your search term. Try a different search term.', 'results': []}, ensure_ascii=False)
        
        output = {
            'count': len(results),
            'results': []
        }
        for p in results:
            entry = {
                'name': p['name'],
                'description': p['description'],
                'duration_minutes': p['duration_minutes'],
                'anesthesia': p['anesthesia'],
                'cost_range': p['cost_range']
            }
            if code_type is None or code_type == 'cpt':
                entry['cpt'] = p.get('cpt')
            if code_type is None or code_type == 'icd10pcs':
                entry['icd10pcs'] = p.get('icd10pcs')
            output['results'].append(entry)
        
        return json.dumps(output, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "medical_procedure_lookup",
    "description": "Search for medical procedures by name or code (CPT/ICD-10-PCS) and return procedure description, typical duration, common anesthesia type, and average cost range.",
    "category": "search",
    "domain": "healthcare",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "search_term": {
            "type": "string",
            "description": "Procedure name or partial name to search (e.g., 'appendectomy', 'knee replacement'). Minimum 2 characters."
        },
        "code_type": {
            "type": "string",
            "description": "Optional: Filter by coding system: 'cpt' for CPT codes, 'icd10pcs' for ICD-10-PCS procedure codes. If omitted, both are searched.",
            "enum": [
                "cpt",
                "icd10pcs"
            ]
        },
        "max_results": {
            "type": "integer",
            "description": "Optional: Maximum number of procedures to return (1-20, default 10)."
        }
    },
    "required": [
        "search_term"
    ]
},
}
