"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate original comedy sketch scripts."""
    import json
    import random

    try:
        data = json.loads(payload)

        # Validate required inputs
        required = ['premise', 'characters', 'comedy_style']
        for field in required:
            if field not in data:
                return json.dumps({'error': f'Missing required field: {field}'})

        premise = data['premise'].strip()
        characters = data['characters']
        style = data['comedy_style']
        duration = min(max(data.get('duration_minutes', 3), 1), 10)
        rating = data.get('age_rating', 'general')

        if len(premise) < 10 or len(premise) > 500:
            return json.dumps({'error': 'Premise must be between 10-500 characters'})

        # Character personality mapping
        personality_traits = {
            'straight_man': 'logical, exasperated, reacts to absurdity',
            'goofball': 'energetic, oblivious, does the unexpected',
            'sarcastic_observer': 'dry wit, comments on the ridiculous',
            'clueless_innocent': 'naive, asks obvious questions, creates misunderstanding',
            'authority_figure': 'pompous, takes things too seriously',
            'overreactor': 'dramatic, panics at small issues',
            'deadpan_delivery': 'emotionless, says absurd things seriously',
            'improv_surreal': 'creates reality-bending scenarios',
            'slapstick_physical': 'pratfalls, props, physical humor',
            'character_actor': 'over-the-top accents, exaggerated mannerisms'
        }

        # Comedy style templates
        style_templates = {
            'absurdist': 'escalating irrationality where characters accept strange events as normal',
            'situational': 'everyday scenarios pushed to extreme through character misunderstandings',
            'dark_humor': 'morbid or taboo topics handled with clever wordplay',
            'parody': 'mimics genre conventions (film noir, sci-fi, etc.) with comedic twists',
            'physical_slapstick': 'exaggerated movements, pratfalls, and object-based humor',
            'wordplay': 'puns, double entendres, and linguistic trickery as the punchline engine',
            'observational': 'characters comment on relatable human experiences turned surreal',
            'satire': 'critiques social/cultural norms through exaggerated representation'
        }

        # Generate sketch structure
        num_characters = len(characters)
        character_profiles = {}
        for i, char in enumerate(characters):
            profile = personality_traits.get(char, 'versatile comic performer')
            character_profiles[f'character_{i+1}'] = {
                'archetype': char,
                'personality': profile,
                'name': f'Character {i+1}'
            }

        # Build scene count based on duration (~1 scene per 2 minutes)
        num_scenes = max(1, round(duration / 2))

        # Generate humorous dialogue lines
        def generate_dialogue(char_name, char_trait, scene_context):
            responses = [
                f"{char_name} ({char_trait}): \"Wait, so you're telling me this is normal?\"",
                f"{char_name} ({char_trait}): \"I've seen worse. Last Tuesday was worse.\"",
                f"{char_name} ({char_trait}): \"That explains the smell. And the existential dread.\"",
                f"{char_name} ({char_trait}): \"In my defense, nobody told me the ketchup was sentient.\"",
                f"{char_name} ({char_trait}): \"I think we need a new plan. And maybe a therapist.\"",
                f"{char_name} ({char_trait}): \"This is fine. Everything's fine. (screams internally)\"",
                f"{char_name} ({char_trait}): \"That's not how physics works. But okay.\"",
                f"{char_name} ({char_trait}): \"I'm not paid enough for this. Wait, I'm not paid at all.\""
            ]
            return random.choice(responses)

        # Stage direction templates
        stage_directions = [
            "Enter scene: [SETTING]",
            "Character crosses stage left, looking confused.",
            "Pause for effect. A beat of awkward silence.",
            "Physical bit: Character slips on a banana peel, recovers with dignity.",
            "Turn to audience for a quick aside.",
            "Sound effect: dramatic sting.",
            "Frozen tableau. Hold for laughter.",
            "Characters swap positions, continuing conversation as if nothing changed."
        ]

        # Build sketch script
        scenes = []
        for scene_num in range(1, num_scenes + 1):
            scene_lines = [
                f"{'='*50}",
                f"SCENE {scene_num}",
                f"{'='*50}",
                f"Setting: {premise} (continued from previous scene)",
                f"Style: {style_templates.get(style, 'comedic interplay')}",
                f"Rating: {rating}",
                ""
            ]

            # Add stage direction
            scene_lines.append(f"[{random.choice(stage_directions).replace('[SETTING]', premise[:30] + '...')}]")
            scene_lines.append(f"")

            # Generate dialogue for each character
            for i, char in enumerate(characters):
                char_key = f'character_{i+1}'
                profile = character_profiles[char_key]
                dialogue = generate_dialogue(profile['name'], profile['personality'], f"scene_{scene_num}")
                scene_lines.append(dialogue)
                scene_lines.append("")

            # Add punchline timing
            scene_lines.append(f"[COMEDIC BEAT: Pause for audience reaction - 2 seconds]")
            scene_lines.append(f"")

            # Add final punchline for the scene
            punchlines = [
                "Character 1: \"Well, that escalated like a squirrel on espresso.\"",
                "Character 2: \"I'm starting to think our premise was poorly researched.\"",
                "Character 1: \"Let's never speak of this again. Starting now.\"",
                "Character 2: \"This is going in my memoir. Chapter 'Bad Ideas'."
            ]
            scene_lines.append(random.choice(punchlines))
            scene_lines.append("")
            scene_lines.append("[LIGHTS FADE]")
            scene_lines.append("")

            scenes.append('\n'.join(scene_lines))

        # Build final result
        sketch = '\n'.join(scenes)

        result = {
            'title': f"Comedy Sketch: {premise[:50]}{'...' if len(premise) > 50 else ''}",
            'sketch_type': style,
            'rating': rating,
            'estimated_runtime_minutes': duration,
            'character_profiles': character_profiles,
            'script': sketch,
            'total_characters': num_characters,
            'total_scenes': num_scenes
        }

        return json.dumps(result, indent=2, ensure_ascii=False)

    except json.JSONDecodeError:
        return json.dumps({'error': 'Invalid JSON payload'})
    except Exception as e:
        return json.dumps({'error': str(e)})


TOOL_SPEC = {
    "name": "comedy_sketch_writer",
    "description": "Generate original comedy sketches based on a premise, character types, and comedic style. Returns a structured script with scene descriptions, dialogue, and punchline timing for entertainment production use.",
    "category": "generate",
    "domain": "entertainment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "premise": {
            "type": "string",
            "description": "Short description of the sketch scenario or setting (e.g., 'A job interview at a pet store run by cats')",
            "minLength": 10,
            "maxLength": 500
        },
        "characters": {
            "type": "array",
            "description": "List of 1-5 character archetypes to include in the sketch (e.g., 'straight_man', 'goofball', 'sarcastic_observer')",
            "items": {
                "type": "string",
                "enum": [
                    "straight_man",
                    "goofball",
                    "sarcastic_observer",
                    "clueless_innocent",
                    "authority_figure",
                    "overreactor",
                    "deadpan_delivery",
                    "improv_surreal",
                    "slapstick_physical",
                    "character_actor"
                ]
            },
            "minItems": 1,
            "maxItems": 5
        },
        "comedy_style": {
            "type": "string",
            "description": "Comedic tone for the piece",
            "enum": [
                "absurdist",
                "situational",
                "dark_humor",
                "parody",
                "physical_slapstick",
                "wordplay",
                "observational",
                "satire"
            ]
        },
        "duration_minutes": {
            "type": "number",
            "description": "Optional: Target runtime in minutes (1-10). Default 3 minutes",
            "minimum": 1,
            "maximum": 10,
            "default": 3
        },
        "age_rating": {
            "type": "string",
            "description": "Optional: Audience suitability level. Default 'general'",
            "enum": [
                "general",
                "teen",
                "mature",
                "adult"
            ],
            "default": "general"
        }
    },
    "required": [
        "premise",
        "characters",
        "comedy_style"
    ]
},
}
