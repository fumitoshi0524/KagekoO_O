"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a fictional comedian character."""
    import json
    import random

    try:
        data = json.loads(payload)
        required = ["comedy_style", "personality_trait"]
        for r in required:
            if r not in data:
                return json.dumps({"error": f"Missing required field: {r}"}, ensure_ascii=False)

        style = data["comedy_style"]
        trait = data["personality_trait"]
        setting = data.get("setting", None)
        gender = data.get("gender", "random")

        if gender == "random":
            gender = random.choice(["male", "female", "non-binary"])

        # Sample data pools for generation
        first_names = {
            "male": ["Tony", "Mike", "Dave", "Kevin", "Steve"],
            "female": ["Lisa", "Sarah", "Mia", "Jen", "Tina"],
            "non-binary": ["Sam", "Jordan", "Alex", "Riley", "Casey"]
        }
        last_names = ["Gable", "Rivers", "Hart", "Noble", "Stone", "Pierce", "Knox", "Wells"]
        stage_personas = [
            {"name": "The Everyman", "desc": "Relatable, speaks for the common person, finds humor in daily inconveniences."},
            {"name": "The Outsider", "desc": "Observations from a quirky perspective, highlights absurdities others miss."},
            {"name": "The Bombastic", "desc": "Loud, energetic, over-the-top physical comedy and exaggerated stories."},
            {"name": "The Deadpan", "desc": "Dry delivery, ironic statements, rarely smiles, lands punches with silence."},
            {"name": "The Charmer", "desc": "Warm, self-deprecating, uses audience rapport to tell personal stories."}
        ]
        joke_templates = [
            "So I was at the {place} and the {person} said to me, '{punchline}' I just looked at them and thought: {thought}.",
            "You ever notice how {observation}? It's like the universe is saying '{message}'.",
            "My {relative} always told me, '{saying}' But I never listened. Then one day, {consequence}.",
            "I don't trust {thing}. They're always {action}. Case in point: {example}.",
            "{profession} have it easy. They just {easy_thing}. Meanwhile, I'm here {hard_thing}."
        ]
        professions = ["dentist", "plumber", "accountant", "teacher", "barista", "programmer", "driver"]
        relatives = ["grandma", "uncle Bob", "cousin", "dad", "mom"]

        first = random.choice(first_names[gender])
        last = random.choice(last_names)
        full_name = f"{first} {last}"
        persona = random.choice(stage_personas)
        template = random.choice(joke_templates)

        # Assemble joke
        joke = template.format(
            place=random.choice(["grocery store", "airport", "DMV", "coffee shop", "park"]),
            person=random.choice(["a cashier", "my neighbor", "a guy in line", "the barista"]),
            punchline=random.choice(["that'll be $47", "we're out of bagels", "please move your car", "I don't work here"]),
            thought=random.choice(["what a time to be alive", "I should've stayed home", "this is my life now"]),
            observation=random.choice(["how people walk slowly in groups", "how ads read your mind", "the way cats stare at walls"]),
            message=random.choice(["slow down and enjoy", "you're being watched", "it's a mystery"]),
            relative=random.choice(relatives),
            saying=random.choice(["never trust a smiling cat", "always carry a spare sock", "if it's stupid but works, it's not stupid"]),
            consequence=random.choice(["my socks never match", "I got locked out", "now I have three umbrellas"]),
            thing=random.choice(["silence", "happiness", "the internet", "ceilings"]),
            action=random.choice(["up to something", "hiding secrets", "judging you"]),
            example=random.choice(["the quiet before a sneeze", "when your phone is silent but you know it buzzed", "a blank screen"]),
            profession=random.choice(professions),
            easy_thing=random.choice(["fix a pipe", "balance a ledger", "drill a tooth"]),
            hard_thing=random.choice(["trying to fold a fitted sheet", "assembling IKEA furniture", "explaining TikTok to my parents"])
        )

        # Setup backstory snippet
        backstory_pieces = [
            f"Born in a small town, {first} discovered comedy at age {random.randint(8, 14)} after {random.choice(['a family dinner gone wrong', 'a school play mishap', 'a embarrassing moment']) }.",
            f"{first} spent years in {setting if setting else 'a nearby city'} doing open mic nights, developing a {trait} voice.",
            f"Their big break came when {random.choice(['a video went viral', 'a talent scout saw them', 'they won a local contest'])}."
        ]
        backstory = " ".join(random.sample(backstory_pieces, min(2, len(backstory_pieces))))

        # Target audience
        audiences = ["young adults", "office workers", "college students", "families", "nightlife crowd"]

        result = {
            "character_name": full_name,
            "gender": gender,
            "comedy_style": style,
            "personality_trait": trait,
            "stage_persona_name": persona["name"],
            "stage_persona_description": persona["desc"],
            "backstory": backstory,
            "signature_joke": joke,
            "target_audience": random.choice(audiences),
            "setting_influence": setting if setting else "modern generic"
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "comedian_character_generator",
    "description": "Generate a fully fleshed-out fictional comedian character including name, backstory, signature joke, stage persona, and target audience for use in comedy writing, improv, or role-playing games.",
    "category": "generate",
    "domain": "entertainment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "comedy_style": {
            "type": "string",
            "description": "Primary comedy style (e.g., observational, sarcastic, slapstick, absurd, dark).",
            "enum": [
                "observational",
                "sarcastic",
                "slapstick",
                "absurd",
                "dark",
                "clean",
                "improv",
                "musical"
            ]
        },
        "personality_trait": {
            "type": "string",
            "description": "Core personality trait for the character (e.g., sarcastic, energetic, dry, awkward, optimistic)."
        },
        "setting": {
            "type": "string",
            "description": "Optional: Setting or era that influences the character's material (e.g., 1980s New York, modern Silicon Valley, medieval tavern)."
        },
        "gender": {
            "type": "string",
            "description": "Optional: Character gender (male, female, non-binary). Default: random.",
            "enum": [
                "male",
                "female",
                "non-binary",
                "random"
            ]
        }
    },
    "required": [
        "comedy_style",
        "personality_trait"
    ]
},
}
