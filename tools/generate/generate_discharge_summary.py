"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a discharge summary from structured clinical data."""
    import json
    from datetime import datetime

    try:
        data = json.loads(payload)

        # Validate required inputs
        required_fields = ["patient_id", "admission_reason", "diagnosis", "treatment_summary", "medications", "follow_up_plan"]
        missing = [f for f in required_fields if f not in data]
        if missing:
            return json.dumps({"error": f"Missing required fields: {', '.join(missing)}"}, ensure_ascii=False)

        patient_id = data["patient_id"]
        admission_reason = data["admission_reason"]
        diagnosis = data["diagnosis"]
        treatment_summary = data["treatment_summary"]
        medications = data["medications"]
        follow_up_plan = data["follow_up_plan"]
        allergies = data.get("allergies", "None reported")
        clinical_notes = data.get("clinical_notes", "")

        # Build medications table as bullet list
        medication_lines = []
        for med in medications:
            med_line = f"- {med['drug_name']} ({med['dosage']}, {med['frequency']}, {med['route']})"
            medication_lines.append(med_line)
        medications_text = "\n".join(medication_lines) if medication_lines else "None"

        # Get current date for summary generation
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Build the discharge summary
        summary = f"""DISCHARGE SUMMARY
====================
Generated: {current_date}
Patient ID: {patient_id}

REASON FOR ADMISSION:
{admission_reason}

DIAGNOSIS AT DISCHARGE:
{diagnosis}

ALLERGIES:
{allergies}

TREATMENT SUMMARY:
{treatment_summary}

DISCHARGE MEDICATIONS:
{medications_text}

FOLLOW-UP PLAN:
{follow_up_plan}
"""

        if clinical_notes:
            summary += f"\nCLINICAL NOTES:\n{clinical_notes}\n"

        # Add footer
        summary += "\n--- End of Discharge Summary ---"

        result = {
            "summary": summary,
            "generated_at": current_date,
            "patient_id": patient_id,
            "word_count": len(summary.split()),
            "status": "generated"
        }

        return json.dumps(result, ensure_ascii=False, indent=2)

    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON payload"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Unexpected error: {str(e)}"}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "generate_discharge_summary",
    "description": "Generate a comprehensive discharge summary for a patient based on structured clinical data including reason for admission, diagnosis, treatment summary, medications, and follow-up plan. Returns a formatted discharge summary document suitable for clinical records and care continuity.",
    "category": "generate",
    "domain": "healthcare",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "patient_id": {
            "type": "string",
            "description": "Unique identifier for the patient (e.g., MRN or hospital ID)"
        },
        "admission_reason": {
            "type": "string",
            "description": "Primary reason for hospitalization as documented on admission"
        },
        "diagnosis": {
            "type": "string",
            "description": "Final diagnosis or diagnoses at discharge, including ICD codes if applicable"
        },
        "treatment_summary": {
            "type": "string",
            "description": "Summary of treatments, procedures, therapies, and interventions during the hospital stay"
        },
        "medications": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "drug_name": {
                        "type": "string",
                        "description": "Name of the medication"
                    },
                    "dosage": {
                        "type": "string",
                        "description": "Dosage (e.g., 500 mg, 1 tablet)"
                    },
                    "frequency": {
                        "type": "string",
                        "description": "Frequency (e.g., twice daily, once daily at bedtime)"
                    },
                    "route": {
                        "type": "string",
                        "description": "Route of administration (e.g., oral, IV, topical)"
                    }
                },
                "required": [
                    "drug_name",
                    "dosage",
                    "frequency",
                    "route"
                ]
            },
            "description": "List of discharge medications including drug name, dose, frequency, and route"
        },
        "follow_up_plan": {
            "type": "string",
            "description": "Instructions for follow-up care, referrals, follow-up appointments, and lifestyle recommendations"
        },
        "allergies": {
            "type": "string",
            "description": "Optional: Known allergies (e.g., drug, food, environmental allergies)"
        },
        "clinical_notes": {
            "type": "string",
            "description": "Optional: Additional clinical notes, observations, or discharge instructions"
        }
    },
    "required": [
        "patient_id",
        "admission_reason",
        "diagnosis",
        "treatment_summary",
        "medications",
        "follow_up_plan"
    ]
},
}
