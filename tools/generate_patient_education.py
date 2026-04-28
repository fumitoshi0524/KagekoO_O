"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        topic = data.get('topic')
        age_group = data.get('patient_age_group')
        lang = data.get('language', 'en')
        include_meds = data.get('include_medication_info', True)

        if not topic or not age_group:
            return json.dumps({'error': 'Missing required fields: topic, patient_age_group'}, ensure_ascii=False)

        # Simple demo template generation - in production would call LLM or knowledge base
        age_phrases = {
            'adult': 'adults and adolescents',
            'pediatric': 'children and infants',
            'geriatric': 'older adults'
        }
        age_label = age_phrases.get(age_group, 'patients')

        doc = {
            'document_type': 'Patient Education Material',
            'topic': topic,
            'language': lang,
            'target_audience': age_label,
            'sections': [
                {
                    'heading': 'What is ' + topic + '?',
                    'content': [
                        f'{topic} is a medical condition/procedure that affects {age_label}.',
                        'This section explains the condition in plain language using simple analogies.',
                        'Key anatomical or physiological concepts are described using everyday comparisons.'
                    ]
                },
                {
                    'heading': 'Self-Care Instructions',
                    'content': [
                        'Follow your healthcare provider\'s instructions carefully.',
                        'Maintain a balanced diet and stay hydrated as appropriate.',
                        'Get adequate rest and avoid strenuous activities until cleared by your doctor.',
                        'Monitor your symptoms daily and keep a log to share at follow-up appointments.'
                    ]
                },
                {
                    'heading': 'Warning Signs - When to Call Your Doctor',
                    'content': [
                        'Severe pain that does not improve with rest or medication.',
                        'Fever above 100.4°F (38°C) that persists for more than 24 hours.',
                        'Shortness of breath, chest pain, or difficulty breathing.',
                        'Sudden changes in vision, speech, or motor function.',
                        'Unusual bleeding or bruising that does not stop with gentle pressure.'
                    ]
                },
                {
                    'heading': 'Follow-Up Plan',
                    'content': [
                        'Schedule a follow-up appointment within 2-4 weeks or as directed.',
                        'Complete any recommended diagnostic tests or lab work before the visit.',
                        'Bring your symptom log and a list of all current medications to each appointment.',
                        'Contact your care coordinator if you need help scheduling transportation or interpreting services.'
                    ]
                }
            ]
        }

        if include_meds:
            doc['sections'].append({
                'heading': 'Common Medications',
                'content': [
                    'Always take medications exactly as prescribed by your healthcare provider.',
                    'Common medications for this condition may include pain relievers, anti-inflammatories, or antibiotics.',
                    'Side effects can include nausea, drowsiness, or digestive upset. Report persistent side effects to your doctor.',
                    'Keep an updated medication list including dosage and frequency.'
                ]
            })

        return json.dumps(doc, ensure_ascii=False, indent=2)

    except json.JSONDecodeError as e:
        return f'error: Invalid JSON payload - {e}'
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "generate_patient_education",
    "description": "Generate a structured patient education document for a given medical condition, treatment, or procedure, including plain-language explanation, self-care instructions, warning signs, and follow-up guidelines, formatted as sections with bullet points.",
    "category": "generate",
    "domain": "healthcare",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "topic": {
            "type": "string",
            "description": "Medical condition, treatment, or procedure name (e.g., 'Type 2 diabetes', 'knee replacement surgery', 'influenza vaccination')"
        },
        "patient_age_group": {
            "type": "string",
            "enum": [
                "adult",
                "pediatric",
                "geriatric"
            ],
            "description": "Age group the education material should be tailored for. Affects language complexity and considerations."
        },
        "language": {
            "type": "string",
            "enum": [
                "en",
                "es",
                "fr",
                "de",
                "zh",
                "ar"
            ],
            "description": "ISO 639-1 two-letter language code for the output document. Defaults to 'en' if not provided."
        },
        "include_medication_info": {
            "type": "boolean",
            "description": "Optional: Whether to include a section on common medications related to the topic (names, purpose, common side effects). Default true."
        }
    },
    "required": [
        "topic",
        "patient_age_group"
    ]
},
}
