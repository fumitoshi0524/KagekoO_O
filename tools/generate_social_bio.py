"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    import random
    try:
        data = json.loads(payload)
        name = data.get('name', '').strip()
        interests = data.get('interests', [])
        tone = data.get('tone', 'professional')
        platform = data.get('platform', 'all')
        include_emoji = data.get('include_emoji', True)
        max_length = data.get('max_length', 160)
        role = data.get('role', '')

        if not name:
            return json.dumps({'error': 'Name is required'})
        if not interests:
            return json.dumps({'error': 'At least one interest is required'})
        if tone not in ['professional', 'casual', 'humorous', 'inspirational', 'minimalist']:
            return json.dumps({'error': 'Invalid tone option'})
        if platform not in ['linkedin', 'twitter', 'instagram', 'all']:
            return json.dumps({'error': 'Invalid platform option'})

        # Template structures for different tones
        tone_templates = {
            'professional': [
                lambda: f"{name} | {role if role else 'Professional'} | Focused on {interests[0].lower() if interests else 'growth'} | Building solutions that matter",
                lambda: f"{role if role else 'Specialist'} at the intersection of {interests[0].lower() if interests else 'innovation'} and impact | {name}",
                lambda: f"{name} — {role if role else 'Expert'} in {', '.join(interests[:2]).lower() if len(interests)>=2 else interests[0].lower() if interests else 'my field'} | Driving results through strategy"
            ],
            'casual': [
                lambda: f"{name} | {interests[0].lower() if interests else 'living life'} enthusiast | {interests[1].lower() if len(interests)>1 else 'coffee'} lover | {role if role else 'just a person with big dreams'}",
                lambda: f"Making {interests[0].lower() if interests else 'stuff'} and {interests[1].lower() if len(interests)>1 else 'memes'} | {name} | {role if role else 'Human'}",
                lambda: f"{name} | {', '.join(interests[:3]).lower() if len(interests)>=3 else interests[0].lower() if interests else 'exploring life'} | Probably {interests[0].lower() if interests else 'thinking about things'}"
            ],
            'humorous': [
                lambda: f"{name} | Professional {interests[0].lower() if interests else 'procrastinator'} | {role if role else 'Doing my best'} | My {interests[1].lower() if len(interests)>1 else 'coffee'} intake is a full-time job",
                lambda: f"{name} — {', '.join(interests[:2]).lower() if len(interests)>=2 else interests[0].lower() if interests else 'alive'} by default | {role if role else 'Under construction'} | Send {interests[0].lower() if interests else 'help'}",
                lambda: f"{name} | I turn {interests[0].lower() if interests else 'random thoughts'} into {interests[1].lower() if len(interests)>1 else 'chaos'} | {role if role else 'Professional beginner'}"
            ],
            'inspirational': [
                lambda: f"{name} | {role if role else 'Dreamer'} | {interests[0].lower() if interests else 'Creating'} my own path | Every day is a chance to {interests[1].lower() if len(interests)>1 else 'grow'}",
                lambda: f"Turning {interests[0].lower() if interests else 'dreams'} into reality | {name} | {role if role else 'Chasing excellence'}",
                lambda: f"{name} | {role if role else 'Believer'} in {', '.join(interests[:2]).lower() if len(interests)>=2 else interests[0].lower() if interests else 'the impossible'} | Together we rise"
            ],
            'minimalist': [
                lambda: f"{name} | {interests[0].lower() if interests else 'simple'} & {interests[1].lower() if len(interests)>1 else 'focused'} | {role if role else 'Less is more'}",
                lambda: f"{name} — {interests[0].lower() if interests else 'minimal'} | {interests[1].lower() if len(interests)>1 else 'intentional'} | {role if role else 'quality over quantity'}",
                lambda: f"{name} | {', '.join(interests[:2]).lower() if len(interests)>=2 else interests[0].lower() if interests else 'keep it simple'} | {role if role else 'Live deliberately'}"
            ]
        }

        # Emoji collections per platform
        platform_emojis = {
            'linkedin': ['🚀', '💼', '📊', '🔗', '✨', '🎯', '💡'],
            'twitter': ['🐦', '🔥', '💬', '⚡', '🎮', '📱', '💭'],
            'instagram': ['📸', '🎨', '🌟', '🌈', '🎵', '✈️', '🌸']
        }

        # Generate bios
        platforms = ['linkedin', 'twitter', 'instagram'] if platform == 'all' else [platform]
        result = {'name': name, 'tone': tone, 'platforms': []}

        for plat in platforms:
            templates = tone_templates.get(tone, tone_templates['professional'])
            variants = []
            for i in range(3):  # Generate 3 variants per tone
                template = random.choice(templates)
                bio = template()
                if include_emoji:
                    emoji_list = platform_emojis.get(plat, ['✨', '🌟'])
                    emoji_count = random.randint(1, 3)
                    selected_emojis = random.sample(emoji_list, min(emoji_count, len(emoji_list)))
                    bio = f"{bio} {' '.join(selected_emojis)}"
                if len(bio) > max_length:
                    bio = bio[:max_length-3] + '...'
                variants.append(bio.strip())
            result['platforms'].append({
                'platform': plat,
                'variants': variants[:3]
            })

        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        return json.dumps({'error': str(e)})


TOOL_SPEC = {
    "name": "generate_social_bio",
    "description": "Generate a personalized social media bio based on user interests, personality traits, and tone preference, returning multiple bio variants suitable for platforms like LinkedIn, Twitter, or Instagram, optimized for engagement.",
    "category": "generate",
    "domain": "social",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "name": {
            "type": "string",
            "description": "Full name of the user for the bio"
        },
        "interests": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "List of interests, hobbies, or professional focus areas (e.g., 'technology', 'writing', 'fitness')"
        },
        "tone": {
            "type": "string",
            "enum": [
                "professional",
                "casual",
                "humorous",
                "inspirational",
                "minimalist"
            ],
            "description": "Desired tone for the generated bios"
        },
        "platform": {
            "type": "string",
            "enum": [
                "linkedin",
                "twitter",
                "instagram",
                "all"
            ],
            "description": "Target social media platform for bio optimization"
        },
        "include_emoji": {
            "type": "boolean",
            "description": "Optional: Whether to include emoji in the bio. Defaults to true"
        },
        "max_length": {
            "type": "integer",
            "minimum": 80,
            "maximum": 500,
            "description": "Optional: Maximum character length for each bio variant"
        },
        "role": {
            "type": "string",
            "description": "Optional: Job title or role description to include in the bio"
        }
    },
    "required": [
        "name",
        "interests",
        "tone",
        "platform"
    ]
},
}
