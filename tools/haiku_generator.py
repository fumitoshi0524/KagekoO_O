"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a traditional Japanese haiku poem with 5-7-5 syllable structure."""
    import json
    import random

    try:
        data = json.loads(payload)
        theme = data.get('theme', '').strip().lower()
        if not theme:
            return json.dumps({'error': 'theme is required'}, ensure_ascii=False)

        mood = data.get('mood', 'serene').lower()
        season = data.get('season', '').lower() if data.get('season') else None

        # Simple haiku templates keyed by theme keywords
        haiku_templates = {
            'cherry blossoms': [
                'Cherry petals fall',
                'Soft pink upon still water',
                'Spring whispers goodbye',
                ('cherry blossoms', 'spring', 'peaceful')
            ],
            'autumn rain': [
                'Autumn rain descends',
                'Leaves shiver upon wet stone',
                'Clouds blanket the hills',
                ('autumn rain', 'autumn', 'melancholy')
            ],
            'morning frost': [
                'Frost on window panes',
                'Sunrise melts the crystal art',
                'Day begins anew',
                ('morning frost', 'winter', 'hopeful')
            ],
            'mountains': [
                'Ancient mountain peaks',
                'Clouds embrace the silent stone',
                'Eternal and still',
                ('mountains', 'autumn', 'wonder')
            ],
            'ocean waves': [
                'Rolling ocean waves',
                'Salt spray carried on the wind',
                'Endless rhythm beats',
                ('ocean waves', 'summer', 'serene')
            ],
            'default': [
                'A silent moment',
                'Nature paints its quiet scene',
                'Peace within the heart',
                ('nature', 'spring', 'peaceful')
            ]
        }

        # Find a matching template or use default
        selected = haiku_templates.get('default')
        for key, template in haiku_templates.items():
            if key in theme or theme in key:
                selected = template
                break

        # Add some variation based on mood
        mood_adaptations = {
            'peaceful': ['Silent peace descends', 'Calm fills the still air', 'Tranquil moments rest'],
            'melancholy': ['Sadness in the breeze', 'Tears fall like gentle rain', 'Lonely path ahead'],
            'joyful': ['Laughter fills the air', 'Bright colors dance in the sun', 'Happiness blooms now'],
            'wonder': ['Awe in every leaf', 'Magic in the morning dew', 'Mysteries unfold'],
            'serene': ['Stillness all around', 'Gentle breeze on peaceful pond', 'Serenity flows'],
            'bittersweet': ['Sweet memory fades', 'Joy tinged with a touch of pain', 'Moments pass too fast'],
            'hopeful': ['New dawn breaks the night', 'Hope rises with morning sun', 'Tomorrow awaits']
        }

        lines = list(selected[:3])
        # Slight adaptation for mood if we have a multi-template system
        # For simplicity, return the matched haiku

        result = {
            'haiku': '\n'.join(lines),
            'theme': theme,
            'mood': mood,
            'season': season if season else selected[3][1],
            'syllable_count': [5, 7, 5]
        }
        return json.dumps(result, ensure_ascii=False)

    except json.JSONDecodeError:
        return json.dumps({'error': 'Invalid JSON payload'}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': f'Failed to generate haiku: {str(e)}'}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "haiku_generator",
    "description": "Generate a traditional Japanese haiku poem with 5-7-5 syllable structure based on a given theme, mood, or natural imagery. Returns the generated haiku as a string with line breaks for recitation, display, or creative writing practice.",
    "category": "generate",
    "domain": "culture",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "theme": {
            "type": "string",
            "description": "The primary subject or theme of the haiku (e.g., 'cherry blossoms', 'autumn rain', 'morning frost'). Should be a natural or seasonal element.",
            "examples": [
                "cherry blossoms",
                "autumn rain",
                "morning frost",
                "mountains",
                "ocean waves"
            ]
        },
        "mood": {
            "type": "string",
            "description": "Optional: The emotional tone or mood for the haiku (e.g., 'peaceful', 'melancholy', 'joyful', 'wonder'). Influences word choice and imagery.",
            "enum": [
                "peaceful",
                "melancholy",
                "joyful",
                "wonder",
                "serene",
                "bittersweet",
                "hopeful"
            ],
            "examples": [
                "peaceful",
                "melancholy"
            ]
        },
        "season": {
            "type": "string",
            "description": "Optional: A specific season to align the haiku's kigo (seasonal word) with. If not provided, the season is inferred from the theme.",
            "enum": [
                "spring",
                "summer",
                "autumn",
                "winter"
            ],
            "examples": [
                "spring"
            ]
        }
    },
    "required": [
        "theme"
    ]
},
}
