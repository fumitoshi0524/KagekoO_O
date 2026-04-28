"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    from datetime import datetime, date
    try:
        data = json.loads(payload)
        patient_id = data.get('patient_id')
        admission_date = data.get('admission_date')
        discharge_date = data.get('discharge_date')
        diagnoses = data.get('diagnoses')
        discharge_disposition = data.get('discharge_disposition')

        if not patient_id or not admission_date or not discharge_date or not diagnoses or not discharge_disposition:
            return json.dumps({'error': 'Missing required fields: patient_id, admission_date, discharge_date, diagnoses, discharge_disposition'})

        # Validate date formats
        try:
            adm_date = datetime.strptime(admission_date, '%Y-%m-%d').date()
            dis_date = datetime.strptime(discharge_date, '%Y-%m-%d').date()
        except ValueError:
            return json.dumps({'error': 'Dates must be in YYYY-MM-DD format'})

        if dis_date < adm_date:
            return json.dumps({'error': 'Discharge date cannot be before admission date'})

        # Validate at least one primary diagnosis
        primary_diagnoses = [d for d in diagnoses if d.get('type') == 'primary']
        if not primary_diagnoses:
            return json.dumps({'error': 'At least one primary diagnosis is required'})

        length_of_stay = (dis_date - adm_date).days

        # Build structured discharge summary
        summary = {
            'document_type': 'discharge_summary',
            'generated_at': datetime.now().isoformat(),
            'patient_id': patient_id,
            'admission_date': admission_date,
            'discharge_date': discharge_date,
            'length_of_stay_days': length_of_stay,
            'discharge_disposition': discharge_disposition,
            'diagnoses': diagnoses,
            'procedures': data.get('procedures', []),
            'medications': data.get('medications', []),
            'follow_up_instructions': data.get('follow_up_instructions', ''),
            'attending_physician': data.get('attending_physician', 'Not specified')
        }

        # Add admission/discharge time placeholders
        summary['admitting_diagnosis'] = [d for d in diagnoses if d.get('type') == 'primary'][0]['description']
        summary['final_diagnosis'] = [d['description'] for d in diagnoses]

        # Generate discharge summary text block
        discharge_text = f"PATIENT DISCHARGE SUMMARY\n"
        discharge_text += f"Patient ID: {patient_id}\n"
        discharge_text += f"Admission: {admission_date} | Discharge: {discharge_date} (Length of Stay: {length_of_stay} days)\n"
        discharge_text += f"Discharged to: {discharge_disposition.replace('_', ' ').title()}\n"
        discharge_text += f"Attending Physician: {summary['attending_physician']}\n\n"
        discharge_text += "DIAGNOSES:\n"
        for d in diagnoses:
            discharge_text += f"  - {d['code']}: {d['description']} ({d['type']})\n"
        if data.get('procedures'):
            discharge_text += "\nPROCEDURES:\n"
            for p in data['procedures']:
                discharge_text += f"  - {p['code']}: {p['description']} (Date: {p['date']})\n"
        if data.get('medications'):
            discharge_text += "\nMEDICATIONS AT DISCHARGE:\n"
            for m in data['medications']:
                continue_rx = 'Continue' if m.get('is_discharge_medication', True) else 'Discontinue'
                discharge_text += f"  - {m['name']} {m['dosage']} ({m['route']}) - {continue_rx}\n"
        if data.get('follow_up_instructions'):
            discharge_text += f"\nFOLLOW-UP INSTRUCTIONS:\n{data['follow_up_instructions']}\n"

        summary['discharge_text'] = discharge_text

        return json.dumps(summary, ensure_ascii=False, indent=2)

    except json.JSONDecodeError as e:
        return json.dumps({'error': f'Invalid JSON payload: {str(e)}'})
    except Exception as e:
        return json.dumps({'error': f'Unexpected error generating discharge summary: {str(e)}'})


TOOL_SPEC = {
    "name": "discharge_summary",
    "description": "Generate a structured discharge summary for a patient leaving a healthcare facility, compiling admission details, diagnoses, procedures, medications, and follow-up instructions into a standardized clinical document.",
    "category": "operations",
    "domain": "healthcare",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "patient_id": {
            "type": "string",
            "description": "Unique identifier for the patient being discharged, e.g., medical record number (MRN)."
        },
        "admission_date": {
            "type": "string",
            "description": "Date when the patient was admitted to the facility, in ISO 8601 format (YYYY-MM-DD)."
        },
        "discharge_date": {
            "type": "string",
            "description": "Date when the patient is discharged, in ISO 8601 format (YYYY-MM-DD)."
        },
        "diagnoses": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "ICD-10 code for the diagnosis."
                    },
                    "description": {
                        "type": "string",
                        "description": "Textual description of the diagnosis."
                    },
                    "type": {
                        "type": "string",
                        "enum": [
                            "primary",
                            "secondary",
                            "complication"
                        ],
                        "description": "Classification of the diagnosis: primary (main reason for admission), secondary (comorbidities), or complication (issues arising during stay)."
                    }
                },
                "required": [
                    "code",
                    "description",
                    "type"
                ]
            },
            "description": "List of diagnoses associated with this admission, each including an ICD-10 code and type classification."
        },
        "procedures": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "CPT or ICD-10-PCS code for the procedure performed."
                    },
                    "description": {
                        "type": "string",
                        "description": "Textual description of the procedure."
                    },
                    "date": {
                        "type": "string",
                        "description": "Date when the procedure was performed, in ISO 8601 format (YYYY-MM-DD)."
                    }
                },
                "required": [
                    "code",
                    "description",
                    "date"
                ]
            },
            "description": "Optional: List of procedures performed during this admission."
        },
        "medications": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Generic or brand name of the medication."
                    },
                    "dosage": {
                        "type": "string",
                        "description": "Dosage amount and frequency, e.g., '500 mg twice daily'."
                    },
                    "route": {
                        "type": "string",
                        "enum": [
                            "oral",
                            "intravenous",
                            "intramuscular",
                            "topical",
                            "subcutaneous",
                            "inhalation"
                        ],
                        "description": "Route of administration for the medication."
                    },
                    "duration": {
                        "type": "string",
                        "description": "Optional: Duration and course length, e.g., '10 days'."
                    },
                    "is_discharge_medication": {
                        "type": "boolean",
                        "description": "Optional: Whether this medication should continue after discharge (default: true)."
                    }
                },
                "required": [
                    "name",
                    "dosage",
                    "route"
                ]
            },
            "description": "Optional: List of medications prescribed during the stay or at discharge."
        },
        "follow_up_instructions": {
            "type": "string",
            "description": "Optional: Free-text instructions for follow-up care, including appointments, lifestyle changes, or specialist referrals."
        },
        "discharge_disposition": {
            "type": "string",
            "enum": [
                "home",
                "rehabilitation_facility",
                "skilled_nursing_facility",
                "long_term_care",
                "hospice",
                "against_medical_advice",
                "transferred"
            ],
            "description": "Discharge destination of the patient."
        },
        "attending_physician": {
            "type": "string",
            "description": "Optional: Name of the attending physician responsible for discharge."
        }
    },
    "required": [
        "patient_id",
        "admission_date",
        "discharge_date",
        "diagnoses",
        "discharge_disposition"
    ]
},
}
