"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate creative story ideas for social media posts based on a theme."""
    import json
    import random

    try:
        data = json.loads(payload)
        theme = data.get('theme', '').strip()
        if not theme or len(theme) < 2:
            return json.dumps({'error': 'Theme must be at least 2 characters long'}, ensure_ascii=False)

        audience = data.get('audience', 'general').strip() or 'general'
        tone = data.get('tone', 'inspirational')
        count = min(max(int(data.get('number_of_ideas', 3)), 1), 10)

        # Template-based story idea generation
        story_templates = {
            'inspirational': [
                f"How {theme} taught me the power of persistence — a personal journey that will resonate with {audience}",
                f"The day everything changed: A {theme} story that proves small actions create big ripples",
                f"From struggle to strength: How embracing {theme} transformed my life and can transform yours"
            ],
            'humorous': [
                f"5 times {theme} went hilariously wrong (and what I learned the hard way)",
                f"When {theme} meets reality: A comedy of errors every {audience} will relate to",
                f"The universe's funniest joke: How {theme} keeps surprising me in the best ways"
            ],
            'dramatic': [
                f"The impossible choice: A {theme} story with consequences that changed everything",
                f"Behind the scenes: The untold drama of how {theme} almost destroyed everything I built",
                f"All or nothing: When {theme} pushed me to the edge and I had to reinvent myself"
            ],
            'educational': [
                f"The science of {theme}: Understanding the hidden mechanics that {audience} need to know",
                f"Masterclass in {theme}: Step-by-step guide to achieving what most people miss",
                f"Debunking myths: What {theme} actually looks like versus what everyone believes"
            ],
            'mysterious': [
                f"The strange case of the vanishing {theme}: A mystery that has {audience} talking",
                f"What they don't tell you about {theme}: Hidden truths and unexplained phenomena",
                f"The secret society of {theme}: Unveiling the untold connections that shape our world"
            ],
            'heartwarming': [
                f"The unexpected gift of {theme}: A story of kindness that restored my faith in humanity",
                f"Finding home: How {theme} brought a community of {audience} together in the most beautiful way",
                f"The last conversation: A {theme} story about love, loss, and the moments that matter"
            ]
        }

        # Generate ideas
        selected_templates = story_templates.get(tone, story_templates['inspirational'])
        ideas = random.sample(selected_templates, min(count, len(selected_templates)))
        
        # If we need more than templates available, cycle and modify
        while len(ideas) < count:
            base = random.choice(selected_templates)
            modified = base.replace('the ', 'a ').replace('how ', 'what ').replace('my ', 'our ')
            if modified not in ideas:
                ideas.append(modified)

        # Build result with hooks and emotional tones
        hooks = [
            "Grab attention with a surprising opening line",
            "Start with a provocative question that resonates",
            "Open with a vivid sensory detail to immerse readers",
            "Lead with a relatable struggle or challenge",
            "Start in the middle of the action to create urgency"
        ]

        result = {
            'theme': theme,
            'audience': audience,
            'tone': tone,
            'generated_ideas': [
                {
                    'title': idea,
                    'suggested_hook': random.choice(hooks),
                    'emotional_tone': tone,
                    'key_elements': [
                        f"Focus on {random.choice(['authenticity', 'vulnerability', 'growth', 'connection', 'transformation'])}",
                        f"Include a {random.choice(['personal anecdote', 'surprising statistic', 'visual metaphor', 'dialogue snippet', 'contrast'])}"
                    ]
                }
                for idea in ideas
            ],
            'total_ideas': len(ideas)
        }

        return json.dumps(result, ensure_ascii=False)

    except json.JSONDecodeError:
        return json.dumps({'error': 'Invalid JSON input'}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': f'Unexpected error: {str(e)}'}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "story_idea_generator",
    "description": "Generate creative story ideas for social media posts, blogs, or community discussions based on a given theme or keyword, returning a list of engaging concepts with suggested hooks and emotional tones.",
    "category": "generate",
    "domain": "social",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "theme": {
            "type": "string",
            "description": "Core theme or keyword for the story ideas (e.g., 'friendship', 'overcoming challenge', 'travel adventure'). Minimum 2 characters.",
            "minLength": 2,
            "maxLength": 100
        },
        "audience": {
            "type": "string",
            "description": "Optional: Target audience for the story (e.g., 'young professionals', 'parents', 'gamers'). If not provided, defaults to 'general'.",
            "default": "general",
            "maxLength": 50
        },
        "tone": {
            "type": "string",
            "description": "Optional: Preferred emotional tone for the story ideas.",
            "enum": [
                "inspirational",
                "humorous",
                "dramatic",
                "educational",
                "mysterious",
                "heartwarming"
            ],
            "default": "inspirational"
        },
        "number_of_ideas": {
            "type": "integer",
            "description": "Optional: Number of story ideas to generate (1-10). Default is 3.",
            "minimum": 1,
            "maximum": 10,
            "default": 3
        }
    },
    "required": [
        "theme"
    ]
},
}
