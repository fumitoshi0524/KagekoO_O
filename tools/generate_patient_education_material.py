"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a patient-friendly educational handout explaining a medical condition or procedure."""
    import json
    try:
        data = json.loads(payload)
        condition = data.get('condition', '').strip()
        if not condition:
            return json.dumps({'error': 'condition is required'}, ensure_ascii=False)
        language = data.get('language', 'en')
        if language not in ['en', 'es', 'fr', 'de', 'zh', 'ar']:
            return json.dumps({'error': f'Unsupported language: {language}'}, ensure_ascii=False)
        reading_level = data.get('reading_level', 'intermediate')
        include_causes = data.get('include_causes', True)
        include_symptoms = data.get('include_symptoms', True)
        include_treatments = data.get('include_treatments', True)
        
        # Simulate generative content based on a knowledge base
        knowledge_base = {
            'hypertension': {
                'name': 'Hypertension (High Blood Pressure)',
                'causes': 'Factors include high salt intake, obesity, lack of exercise, stress, genetics, and age.',
                'symptoms': 'Often no symptoms until severe. May include headaches, shortness of breath, nosebleeds, or flushing.',
                'treatments': 'Lifestyle changes (diet, exercise, weight loss), medications (ACE inhibitors, beta-blockers, diuretics), and regular monitoring.'
            },
            'diabetes': {
                'name': 'Diabetes Mellitus',
                'causes': 'Type 1: autoimmune destruction of insulin-producing cells. Type 2: insulin resistance due to genetics, obesity, and inactivity.',
                'symptoms': 'Increased thirst, frequent urination, fatigue, blurred vision, slow-healing wounds.',
                'treatments': 'Insulin therapy (Type 1), oral medications (metformin), diet management, exercise, blood sugar monitoring.'
            },
            'knee replacement surgery': {
                'name': 'Knee Replacement Surgery (Total Knee Arthroplasty)',
                'causes': 'Severe arthritis (osteoarthritis, rheumatoid arthritis), injury, or knee deformity causing chronic pain and limited mobility.',
                'symptoms': 'Persistent knee pain, stiffness, swelling, difficulty walking, bending, or climbing stairs.',
                'treatments': 'Surgical replacement of damaged knee surfaces with metal and plastic components, followed by physical therapy for 6-12 weeks.'
            }
        }
        
        # Fallback for unknown conditions - use a generic template
        condition_key = condition.lower().strip()
        if condition_key in knowledge_base:
            info = knowledge_base[condition_key]
        else:
            info = {
                'name': condition.title(),
                'causes': 'Please consult your healthcare provider for information about causes specific to your condition.',
                'symptoms': 'Common symptoms may include pain, discomfort, or functional changes. Talk to your doctor for a personalized assessment.',
                'treatments': 'Treatment options vary. Your healthcare provider will recommend a plan based on your specific diagnosis and health status.'
            }
        
        # Build handout
        sections = []
        sections.append(f"# Patient Education: {info['name']}")
        sections.append('')
        lang_names = {'en': 'This handout is for informational purposes only. Always consult your healthcare provider for medical advice.',
                     'es': 'Este folleto es solo para fines informativos. Siempre consulte a su proveedor de atenci\u00f3n m\u00e9dica para obtener asesoramiento m\u00e9dico.',
                     'fr': 'Ce document est fourni \u00e0 titre informatif uniquement. Consultez toujours votre professionnel de sant\u00e9 pour des conseils m\u00e9dicaux.',
                     'de': 'Dieses Merkblatt dient nur zu Informationszwecken. Bei medizinischen Fragen konsultieren Sie bitte immer Ihren Arzt.',
                     'zh': '\u672c\u624b\u518c\u4ec5\u4f9b\u53c2\u8003\u3002\u8bf7\u59cb\u7ec8\u54a8\u8be2\u60a8\u7684\u533b\u7597\u4fdd\u5065\u63d0\u4f9b\u8005\u83b7\u53d6\u533b\u5b66\u5efa\u8bae\u3002',
                     'ar': '\u0647\u0630\u0647 \u0627\u0644\u0646\u0634\u0631\u0629 \u0644\u0623\u063a\u0631\u0627\u0636 \u0627\u0644\u0625\u0639\u0644\u0627\u0645 \u0641\u0642\u0637. \u0627\u0633\u062a\u0634\u0631 \u062f\u0627\u0626\u0645\u0627\u064b \u0645\u0642\u062f\u0645 \u0627\u0644\u0631\u0639\u0627\u064a\u0629 \u0627\u0644\u0635\u062d\u064a\u0629 \u0644\u0644\u062d\u0635\u0648\u0644 \u0639\u0644\u0649 \u0646\u0635\u0627\u0626\u062d \u0637\u0628\u064a\u0629.'}
        disclaimer = lang_names.get(language, lang_names['en'])
        sections.append(disclaimer)
        sections.append('')
        sections.append('---')
        
        if include_causes:
            sections.append('## What Causes This Condition?')
            sections.append(info['causes'])
            sections.append('')
        if include_symptoms:
            sections.append('## Common Symptoms')
            sections.append(info['symptoms'])
            sections.append('')
        if include_treatments:
            sections.append('## Treatment Options')
            sections.append(info['treatments'])
            sections.append('')
        
        sections.append('## Self-Care Tips')
        sections.append('* Follow your treatment plan as prescribed by your healthcare provider.')
        sections.append('* Attend all follow-up appointments.')
        sections.append('* Maintain a healthy diet and stay physically active as able.')
        sections.append('* Report any new or worsening symptoms immediately.')
        sections.append('* Keep a list of your medications and share it with all your healthcare providers.')
        
        # Add reading level modifications (simulated)
        if reading_level == 'basic':
            result_text = '\\n'.join(sections)
            result_text = result_text.replace('healthcare provider', 'doctor')
            result_text = result_text.replace('consult', 'talk to')
            result_text = result_text.replace('inflammatory', 'swelling')
        elif reading_level == 'detailed':
            result_text = '\\n'.join(sections)
            result_text += '\\n\\n## References\\n* ICD-10 coding and medical guidelines.\\n* PubMed Health resources.\\n* American Medical Association patient education standards.'
        else:
            result_text = '\\n'.join(sections)
        
        result = {
            'handout_text': result_text,
            'condition': condition,
            'language': language,
            'reading_level': reading_level,
            'word_count': len(result_text.split()),
            'sections_included': {
                'causes': include_causes,
                'symptoms': include_symptoms,
                'treatments': include_treatments
            }
        }
        return json.dumps(result, ensure_ascii=False)
    except json.JSONDecodeError as e:
        return json.dumps({'error': f'Invalid JSON payload: {str(e)}'}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': f'Unexpected error: {str(e)}'}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "generate_patient_education_material",
    "description": "Generate a patient-friendly educational handout explaining a medical condition or procedure, including cause, symptoms, treatment options, and self-care tips, returning structured text suitable for printing or electronic delivery.",
    "category": "generate",
    "domain": "healthcare",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "condition": {
            "type": "string",
            "description": "Medical condition or procedure name (e.g., hypertension, diabetes, knee replacement surgery). Must be a recognized ICD-10 or common medical term."
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
            "description": "ISO 639-1 language code for the generated content."
        },
        "reading_level": {
            "type": "string",
            "enum": [
                "basic",
                "intermediate",
                "detailed"
            ],
            "description": "Optional: Target reading complexity. 'basic' uses simple words and short sentences (5th grade level), 'intermediate' for general adult, 'detailed' includes medical terminology. Default: 'intermediate'."
        },
        "include_causes": {
            "type": "boolean",
            "description": "Optional: Whether to include a section on common causes and risk factors. Default: true."
        },
        "include_symptoms": {
            "type": "boolean",
            "description": "Optional: Whether to include a symptom checklist. Default: true."
        },
        "include_treatments": {
            "type": "boolean",
            "description": "Optional: Whether to include standard treatment options (medications, procedures, lifestyle changes). Default: true."
        }
    },
    "required": [
        "condition",
        "language"
    ]
},
}
