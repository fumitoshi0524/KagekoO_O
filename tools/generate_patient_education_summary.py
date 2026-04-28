"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a patient-friendly education summary from a medical diagnosis."""
    import json
    try:
        data = json.loads(payload)
        diagnosis = data.get("diagnosis")
        language = data.get("language")
        reading_level = data.get("reading_level", "general_public")
        include_medication = data.get("include_medication_info", True)
        
        if not diagnosis or not language:
            return json.dumps({"error": "Missing required fields: diagnosis and language."})
        
        # Simulated knowledge base lookup for common conditions
        condition_db = {
            "type 2 diabetes": {
                "symptoms": ["increased thirst", "frequent urination", "blurred vision"],
                "causes": ["insulin resistance", "genetic factors", "obesity"],
                "treatments": ["blood sugar monitoring", "metformin", "insulin therapy"],
                "lifestyle_tips": ["balanced diet low in sugar", "regular exercise 30 min/day", "maintain healthy weight"]
            },
            "hypertension": {
                "symptoms": ["often no symptoms", "headaches", "shortness of breath"],
                "causes": ["high sodium intake", "stress", "genetics"],
                "treatments": ["ACE inhibitors", "calcium channel blockers", "diuretics"],
                "lifestyle_tips": ["reduce salt intake", "manage stress", "regular blood pressure monitoring"]
            }
        }
        
        info = condition_db.get(diagnosis.lower(), {
            "symptoms": ["consult your healthcare provider for specific symptoms"],
            "causes": ["various factors including genetics and environment"],
            "treatments": ["as prescribed by your doctor"],
            "lifestyle_tips": ["follow medical advice", "maintain regular check-ups"]
        })
        
        # Generate reading-level-appropriate text
        level_adjectives = {
            "elementary": "simple and easy to understand",
            "middle_school": "clear with some medical terms explained",
            "general_public": "comprehensive but accessible"
        }
        
        summary = {
            "diagnosis": diagnosis,
            "language": language,
            "reading_level": reading_level,
            "summary": f"This is a {level_adjectives.get(reading_level, 'general')} summary about {diagnosis}.",
            "symptoms": info["symptoms"],
            "causes": info["causes"],
            "treatment_options": info["treatments"] if include_medication else info["treatments"][:1],
            "lifestyle_recommendations": info["lifestyle_tips"],
            "disclaimer": "This information is for educational purposes only. Always consult a healthcare professional."
        }
        
        return json.dumps(summary, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "generate_patient_education_summary",
    "description": "Generate a patient-friendly education summary from a complex medical diagnosis or treatment plan, returning a structured summary with symptoms, causes, treatment options, and lifestyle recommendations.",
    "category": "generate",
    "domain": "healthcare",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "diagnosis": {
            "type": "string",
            "description": "The medical diagnosis or condition name (e.g., type 2 diabetes, hypertension). Should be a recognized ICD-10 or common medical term."
        },
        "language": {
            "type": "string",
            "description": "The language for the generated summary (e.g., en, es, fr, de, zh).",
            "enum": [
                "en",
                "es",
                "fr",
                "de",
                "zh",
                "ar",
                "pt",
                "hi",
                "ja",
                "ko"
            ]
        },
        "reading_level": {
            "type": "string",
            "description": "Optional: Target reading complexity level for the summary (elementary, middle_school, general_public). Defaults to general_public.",
            "enum": [
                "elementary",
                "middle_school",
                "general_public"
            ]
        },
        "include_medication_info": {
            "type": "boolean",
            "description": "Optional: Whether to include common medication classes and their purposes. Defaults to true."
        }
    },
    "required": [
        "diagnosis",
        "language"
    ]
},
}
