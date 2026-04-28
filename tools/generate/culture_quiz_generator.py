"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a culture quiz question based on input parameters."""
    import json
    import random

    # Pre-defined question bank per region (example demonstrating business logic)
    question_bank = {
        "Japan": [
            {
                "question": "Which traditional Japanese garment is worn by both men and women and is often associated with festivals and ceremonies?",
                "options": ["Kimono", "Yukata", "Hakama", "Fundoshi"],
                "correct": 0,
                "explanation": "The kimono is a versatile garment worn for formal occasions, while yukata is a lighter summer version."
            },
            {
                "question": "What is the main ingredient in the Japanese fermented dish 'Natto'?",
                "options": ["Tofu", "Soybeans", "Rice", "Fish"],
                "correct": 1,
                "explanation": "Natto is made from fermented soybeans, known for its strong flavor and sticky texture."
            }
        ],
        "India": [
            {
                "question": "Which Indian festival is known as the 'Festival of Lights' and involves lighting diyas (lamps)?",
                "options": ["Holi", "Diwali", "Eid", "Pongal"],
                "correct": 1,
                "explanation": "Diwali symbolizes the victory of light over darkness and is celebrated by lighting lamps and bursting crackers."
            },
            {
                "question": "What is the classical dance form originating from the state of Kerala?",
                "options": ["Bharatanatyam", "Kathak", "Kathakali", "Odissi"],
                "correct": 2,
                "explanation": "Kathakali is known for elaborate costumes, makeup, and storytelling through dance-drama."
            }
        ],
        "Brazil": [
            {
                "question": "Which famous Brazilian festival features samba parades, costumes, and street parties?",
                "options": ["Carnival", "Festas Juninas", "Réveillon", "Oktoberfest"],
                "correct": 0,
                "explanation": "Carnival in Brazil is a massive celebration with samba schools competing in the Sambadrome."
            },
            {
                "question": "What is Brazil's most popular sport (often considered a national passion)?",
                "options": ["Volleyball", "Capoeira", "Football (Soccer)", "Surfing"],
                "correct": 2,
                "explanation": "Football is deeply embedded in Brazilian culture with legendary players like Pelé."
            }
        ]
    }

    try:
        data = json.loads(payload)
        region = data.get('region')
        if not region:
            return json.dumps({'error': 'Missing required parameter: region'}, ensure_ascii=False)
        # Normalize region key (capitalize first letter, case-insensitive matching can be added)
        region_key = region.capitalize()
        if region_key not in question_bank:
            # Fallback to a random region if not found
            available = list(question_bank.keys())
            region_key = random.choice(available)
        questions = question_bank[region_key]
        # Filter by category if provided
        category = data.get('category_detail', 'random')
        # For demo, we ignore category filtering (in real system, would have more data)
        # Select random question
        question = random.choice(questions)
        result = {
            'region': region_key,
            'question': question['question'],
            'options': question['options'],
            'correct_index': question['correct'],
            'explanation': question['explanation']
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "culture_quiz_generator",
    "description": "Generate a quiz question about world cultures, covering topics such as traditions, festivals, cuisine, history, and daily life. Returns a question, four multiple-choice options, the correct answer index, and a brief cultural explanation.",
    "category": "generate",
    "domain": "culture",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "region": {
            "type": "string",
            "description": "Geographic region or country to focus the quiz question on (e.g., Japan, India, Brazil, Africa, Europe).",
            "examples": [
                "Japan",
                "India",
                "Brazil"
            ]
        },
        "category_detail": {
            "type": "string",
            "enum": [
                "traditions",
                "festivals",
                "cuisine",
                "history",
                "daily_life",
                "random"
            ],
            "description": "Specific aspect of culture for the question. Default is 'random' if not provided.",
            "default": "random"
        },
        "difficulty": {
            "type": "string",
            "enum": [
                "easy",
                "medium",
                "hard"
            ],
            "description": "Optional: Difficulty level of the question. Default is 'medium'.",
            "default": "medium"
        },
        "interest_tags": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "Optional: List of topics or keywords to include in the question (e.g., 'kimono', 'samba', 'Diwali').",
            "default": []
        }
    },
    "required": [
        "region"
    ]
},
}
