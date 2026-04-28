"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    import random

    try:
        data = json.loads(payload)
        theme = data.get('theme', '').strip()
        target_audience = data.get('target_audience', '').strip()
        duration = data.get('duration_seconds', 30)
        tone = data.get('tone', 'casual')
        key_elements = data.get('key_elements', '').strip()

        if not theme:
            return json.dumps({'error': 'theme is required and must be non-empty'}, ensure_ascii=False)
        if not target_audience:
            return json.dumps({'error': 'target_audience is required and must be non-empty'}, ensure_ascii=False)
        if not isinstance(duration, int) or duration < 15 or duration > 60:
            return json.dumps({'error': 'duration_seconds must be an integer between 15 and 60'}, ensure_ascii=False)

        # Simple deterministic but varied script generation based on inputs
        hooks = {
            'humorous': ["You won't believe what happened next...", "This is why I can't have nice things.", "I tried something dumb so you don't have to."],
            'inspirational': ["This one tip changed everything for me.", "You are capable of more than you know.", "The journey starts with one small step."],
            'dramatic': ["I never expected this to happen.", "What if I told you everything you knew was wrong?", "The moment that changed my life."],
            'educational': ["Here's something your teacher never told you.", "The science behind this will blow your mind.", "3 facts that will change how you see the world."],
            'casual': ["So I woke up and decided to...", "Let me show you something cool.", "Quick tip for your day."],
            'sarcastic': ["Oh great, another day…", "Because obviously that's how it works.", "Let me explain why that's a terrible idea."],
            'energetic': ["Let's GOOOO!", "This is absolutely insane!", "You need to see this right now!"]
        }
        tone_hooks = hooks.get(tone, hooks['casual'])
        hook = random.choice(tone_hooks)

        # Estimate scenes based on duration (roughly 3-6 seconds per scene)
        num_scenes = max(2, min(5, duration // 10))
        scenes = []
        for i in range(num_scenes):
            scene_label = f"Scene {i+1}:"
            if i == 0:
                scene_text = f"{hook}\n[Visual: Establishing shot related to {theme}. Fast cuts.]"
            elif i == num_scenes - 1:
                cta = "Like and follow for more!" if tone in ['casual', 'humorous', 'sarcastic'] else "Don't forget to subscribe and share!"
                if 'cta' in key_elements.lower():
                    cta = key_elements.split(',')[0] + ' - ' + cta
                scene_text = f"[Resolution/Climax]\n{cta}"
            else:
                scene_text = f"[Action: Intermediate step, building tension or delivering info related to {theme}. Audience reacts with {target_audience} in mind.]"
            if key_elements and i == 1:
                elems = key_elements.split(',')
                if len(elems) > 0:
                    scene_text += f"\n[User-specific element: {random.choice(elems).strip()} appears here.]"
            scenes.append({"scene": scene_label, "description": scene_text})

        # Brief dialogue (one-liner)
        dialogue_lines = [
            f"Did you know that {theme} is more popular than ever?",
            f"Let me break down {theme} in under {duration} seconds.",
            f"Here's a {tone} take on {theme}."
        ]
        dialogue = random.choice(dialogue_lines)

        result = {
            "title": f"{tone.capitalize()} {theme} Video",
            "target_audience": target_audience,
            "duration_seconds": duration,
            "tone": tone,
            "hook": hook,
            "dialogue_suggestion": dialogue,
            "scenes": scenes,
            "estimated_scene_count": num_scenes
        }
        return json.dumps(result, ensure_ascii=False)
    except json.JSONDecodeError as e:
        return json.dumps({'error': f'Invalid JSON payload: {str(e)}'}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': f'Unexpected error: {str(e)}'}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "short_video_script_generator",
    "description": "Generates a complete short-form video script including hook, scene descriptions, dialogue, and call-to-action based on a given theme, target audience, and desired video duration, returning structured script segments optimized for engagement on platforms like TikTok, Instagram Reels, or YouTube Shorts.",
    "category": "generate",
    "domain": "entertainment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "theme": {
            "type": "string",
            "description": "The central topic or concept of the video (e.g., 'funny pet fails', 'quick makeup tutorial', 'day in the life of a programmer')"
        },
        "target_audience": {
            "type": "string",
            "description": "The primary audience demographic or interest group (e.g., 'Gen Z humor', 'fitness enthusiasts', 'beauty beginners')"
        },
        "duration_seconds": {
            "type": "integer",
            "description": "Total target duration of the video in seconds (15-60)",
            "minimum": 15,
            "maximum": 60
        },
        "tone": {
            "type": "string",
            "description": "Optional: Desired emotional tone for the script (e.g., 'humorous', 'inspirational', 'dramatic', 'educational'). Defaults to 'casual'.",
            "enum": [
                "humorous",
                "inspirational",
                "dramatic",
                "educational",
                "casual",
                "sarcastic",
                "energetic"
            ]
        },
        "key_elements": {
            "type": "string",
            "description": "Optional: Comma-separated list of specific props, lines, or visual elements the user wants included"
        }
    },
    "required": [
        "theme",
        "target_audience",
        "duration_seconds"
    ]
},
}
