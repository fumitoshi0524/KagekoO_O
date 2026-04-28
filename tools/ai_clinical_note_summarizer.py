"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        patient_id = data.get('patient_id')
        symptoms = data.get('symptoms', [])
        diagnoses = data.get('diagnoses', [])
        medications = data.get('medications', [])
        lab_results = data.get('lab_results', [])
        encounter_type = data.get('encounter_type', 'follow-up')
        include_recommendations = data.get('include_recommendations', False)
        if not patient_id:
            return json.dumps({'error': 'patient_id is required'}, ensure_ascii=False)
        if not symptoms:
            return json.dumps({'error': 'symptoms list is required and cannot be empty'}, ensure_ascii=False)
        if not diagnoses:
            return json.dumps({'error': 'diagnoses list is required and cannot be empty'}, ensure_ascii=False)
        subjective = 'Patient reports: ' + '; '.join(symptoms) if symptoms else 'No subjective symptoms reported.'
        objective = ''
        if lab_results:
            objective += 'Lab results: '
            labs_entries = []
            for lab in lab_results:
                val = lab.get('value', 'N/A')
                ref = lab.get('reference_range', '')
                summary = f"{lab['test_name']}: {val}"
                if ref:
                    summary += f' (ref: {ref})'
                labs_entries.append(summary)
            objective += '; '.join(labs_entries) + '. '
        if medications:
            objective += 'Medications: '
            med_entries = []
            for med in medications:
                dose = med.get('dosage', '')
                route = med.get('route', '')
                entry = med['name']
                if dose:
                    entry += f' {dose}'
                if route:
                    entry += f' ({route})'
                med_entries.append(entry)
            objective += '; '.join(med_entries) + '.'
        if not lab_results and not medications:
            objective = 'No objective findings provided.'
        assessment = 'Assessment: ' + '; '.join(diagnoses) + '.'
        plan = ''
        if include_recommendations:
            recs = []
            if medications:
                recs.append('Continue current medications as prescribed.')
            if lab_results:
                recs.append('Review lab results at next visit.')
            if symptoms:
                recs.append('Follow up if symptoms persist or worsen.')
            if recs:
                plan = 'Plan: ' + ' '.join(recs)
            else:
                plan = 'Plan: No specific recommendations at this time.'
        note_type_label = encounter_type.capitalize() if encounter_type else 'Follow-up'
        note = f"""{note_type_label} Clinical Note
Patient ID: {patient_id}
---
**Subjective:**
{subjective}

**Objective:**
{objective}

**Assessment:**
{assessment}
"""
        if plan:
            note += f'\n**Plan:**\n{plan}\n'
        result = {
            'success': True,
            'summary_note': note.strip(),
            'note_sections': {
                'subjective': subjective,
                'objective': objective.strip(),
                'assessment': assessment,
                'plan': plan
            }
        }
        return json.dumps(result, ensure_ascii=False)
    except json.JSONDecodeError as e:
        return json.dumps({'error': f'Invalid JSON input: {str(e)}'}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': f'Unexpected error: {str(e)}'}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "ai_clinical_note_summarizer",
    "description": "Generate a concise clinical summary from a patient's structured encounter data, including symptoms, diagnoses, medications, and lab results, returning a formatted SOAP note for EMR integration.",
    "category": "generate",
    "domain": "healthcare",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "patient_id": {
            "type": "string",
            "description": "Unique patient identifier (e.g., MRN or UUID)"
        },
        "symptoms": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "List of patient-reported symptoms with duration and severity"
        },
        "diagnoses": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "List of confirmed or suspected diagnoses (ICD-10 codes recommended)"
        },
        "medications": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Medication generic or brand name"
                    },
                    "dosage": {
                        "type": "string",
                        "description": "Dosage and frequency (e.g., 500mg twice daily)"
                    },
                    "route": {
                        "type": "string",
                        "description": "Administration route (oral, IV, topical, etc.)"
                    }
                },
                "required": [
                    "name",
                    "dosage"
                ]
            },
            "description": "Current medications with dosage and route"
        },
        "lab_results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "test_name": {
                        "type": "string",
                        "description": "Name of lab test (e.g., HbA1c, LDL)"
                    },
                    "value": {
                        "type": "string",
                        "description": "Test result value with units"
                    },
                    "reference_range": {
                        "type": "string",
                        "description": "Normal reference range, if available"
                    }
                },
                "required": [
                    "test_name",
                    "value"
                ]
            },
            "description": "List of relevant lab test results with values and reference ranges"
        },
        "encounter_type": {
            "type": "string",
            "enum": [
                "initial",
                "follow-up",
                "telehealth",
                "emergency"
            ],
            "description": "Type of clinical encounter for note customization"
        },
        "include_recommendations": {
            "type": "boolean",
            "description": "Optional: if true, generates a plan section with basic recommendations based on the data provided"
        }
    },
    "required": [
        "patient_id",
        "symptoms",
        "diagnoses"
    ]
},
}
