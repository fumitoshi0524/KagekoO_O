"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        theme = data.get('theme')
        if not theme:
            return json.dumps({'error': 'Missing required parameter: theme'}, ensure_ascii=False)
        content_type = data.get('content_type', 'slogan')
        language = data.get('language', 'en')
        tone = data.get('tone', 'inspirational')
        # Simple content generation logic based on theme and type
        templates = {
            'slogan': {
                'inspirational': f'"{theme.title()} - Every small step counts towards a greener planet!"',
                'educational': f'"Did you know? {theme.title()} can significantly reduce your ecological footprint."',
                'urgent': f'"Act now! {theme.title()} is critical for our survival."',
                'humorous': f'"{theme.title()}: Because the Earth is our ride, and we don\'t want it to break down."'
            },
            'tip': {
                'inspirational': f'Tip: Start {theme} today and inspire others to join the movement!',
                'educational': f'Tip: Learn one new fact about {theme} each week to build sustainable habits.',
                'urgent': f'Tip: Immediately implement {theme} in your daily routine to avert climate crisis.',
                'humorous': f'Tip: Pretend {theme} is a game - every bottle recycled earns you 10 eco-points!' 
            },
            'social_post': {
                'inspirational': f'"Let\'s make {theme} a lifestyle. Together we can heal our planet. 🌍 #EcoWarrior"',
                'educational': f'"{theme.title()} explained: Here\'s how it helps reduce carbon emissions. Share to spread awareness!"',
                'urgent': f'"Emergency: We need to embrace {theme} now. Climate change won\'t wait. #ActOnClimate"',
                'humorous': f'"{theme.title()} - because there is no Planet B. Well, not one with pizza delivery anyway. 😉"'
            },
            'poem': {
                'inspirational': f'"In fields of green and skies so blue,\n{theme.title()} brings us hope anew.\nWith every action, small and true,\nWe heal the earth for me and you."',
                'educational': f'"Learn the way of {theme} light,\nReduce your carbon footprint right.\nRecycle, reuse, and plant a tree,\nFor a sustainable legacy."',
                'urgent': f'"The clock is ticking, hear the cry,\n{theme.title()} - we must apply.\nNo more time to wait or stall,\nTogether we must save it all."',
                'humorous': f'"{theme.title()} is the trend,\nWon\'t you join, my friend?\nDon\'t let the planet frown,\nTurn that plastic bottle upside down!"'
            }
        }
        if content_type not in templates:
            return json.dumps({'error': f'Invalid content_type: {content_type}. Options: slogan, tip, social_post, poem'}, ensure_ascii=False)
        if tone not in templates[content_type]:
            return json.dumps({'error': f'Invalid tone: {tone}. Options: inspirational, educational, urgent, humorous'}, ensure_ascii=False)
        result = {
            'theme': theme,
            'content_type': content_type,
            'language': language,
            'tone': tone,
            'generated_content': templates[content_type][tone]
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "eco_friendly_content_generator",
    "description": "Generate eco-friendly content such as slogans, tips, and social media posts about environmental conservation and sustainable living based on user-specified themes.",
    "category": "generate",
    "domain": "environment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "theme": {
            "type": "string",
            "description": "The environmental theme for content generation (e.g., 'reduce plastic', 'save water', 'green energy', 'recycling')",
            "examples": [
                "reduce plastic",
                "save water"
            ]
        },
        "content_type": {
            "type": "string",
            "description": "Optional: Type of content to generate. Default: 'slogan'. Options: 'slogan', 'tip', 'social_post', 'poem'",
            "enum": [
                "slogan",
                "tip",
                "social_post",
                "poem"
            ]
        },
        "language": {
            "type": "string",
            "description": "Optional: Language for the generated content (e.g., 'en', 'es', 'fr', 'de'). Default is 'en'.",
            "default": "en"
        },
        "tone": {
            "type": "string",
            "description": "Optional: Tone of the content. Options: 'inspirational', 'educational', 'urgent', 'humorous'. Default: 'inspirational'.",
            "enum": [
                "inspirational",
                "educational",
                "urgent",
                "humorous"
            ]
        }
    },
    "required": [
        "theme"
    ]
},
}
