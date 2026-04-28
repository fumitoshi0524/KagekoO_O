"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        genre = data.get('genre')
        protagonist = data.get('protagonist_archetype')
        antagonist = data.get('antagonist_type')
        if not genre or not protagonist or not antagonist:
            return json.dumps({'error': 'Missing required fields: genre, protagonist_archetype, antagonist_type'})
        seeds = data.get('plot_seeds', [])
        levels = data.get('branching_levels', 3)
        if not (1 <= levels <= 5):
            levels = 3
        # Seed-based narrative generation
        import random
        random.seed(hash(f'{genre}:{protagonist}:{antagonist}:{"|".join(seeds)}'))
        story_arcs = {
            'fantasy': {'hero': 'rise', 'antihero': 'fall', 'rogue': 'heist', 'scholar': 'discovery', 'warrior': 'quest', 'mage': 'prophecy', 'detective': 'enigma', 'survivor': 'exodus'},
            'sci-fi': {'hero': 'rebellion', 'antihero': 'redemption', 'rogue': 'smuggle', 'scholar': 'experiment', 'warrior': 'invasion', 'mage': 'techmage', 'detective': 'cyber', 'survivor': 'colony'},
            'noir': {'hero': 'investigation', 'antihero': 'corruption', 'rogue': 'con', 'scholar': 'archive', 'warrior': 'vigilante', 'mage': 'occult', 'detective': 'case', 'survivor': 'underground'},
            'romance': {'hero': 'meet-cute', 'antihero': 'dangerous', 'rogue': 'mistaken', 'scholar': 'epistolary', 'warrior': 'forbidden', 'mage': 'enchantment', 'detective': 'mystery', 'survivor': 'second-chance'},
            'adventure': {'hero': 'treasure', 'antihero': 'rival', 'rogue': 'escape', 'scholar': 'expedition', 'warrior': 'safari', 'mage': 'cursed', 'detective': 'clue', 'survivor': 'stranded'},
            'horror': {'hero': 'survival', 'antihero': 'curse', 'rogue': 'haunt', 'scholar': 'ritual', 'warrior': 'hunt', 'mage': 'summon', 'detective': 'paranormal', 'survivor': 'isolation'},
            'comedy': {'hero': 'misunderstanding', 'antihero': 'satire', 'rogue': 'slapstick', 'scholar': 'absurd', 'warrior': 'fish-out-water', 'mage': 'mistake', 'detective': 'farce', 'survivor': 'misfit'},
            'historical': {'hero': 'revolt', 'antihero': 'intrigue', 'rogue': 'heist', 'scholar': 'discovery', 'warrior': 'battle', 'mage': 'heretic', 'detective': 'conspiracy', 'survivor': 'exile'}
        }
        arc_key = story_arcs.get(genre, {}).get(protagonist, 'default')
        # Generate story
        act_templates = {
            'act1': [
                f'A {protagonist} in a {genre} world discovers a hidden {arc_key} involving a {antagonist}.',
                f'The {antagonist} reveals a devastating truth that forces the {protagonist} to act.'
            ],
            'act2': [
                f'The {protagonist} assembles a motley crew while facing the {antagonist}\'s minions.',
                f'A betrayal within the ranks leads the {protagonist} to question their own motives.'
            ],
            'act3': [
                f'In a climactic showdown, the {protagonist} confronts the {antagonist} with unexpected allies.',
                f'A choice appears: sacrifice everything for victory or find a third path?',
                f'The aftermath reshapes the world, leaving the {protagonist} forever changed.'
            ]
        }
        # Add seeds as subplots
        subplots = []
        for i, seed in enumerate(seeds[:3]):
            subplots.append(f'Subplot: {seed} unfolds during the {["first","second","third"][i]} act.')
        # Generate branching choices
        branches = []
        for i in range(1, levels + 1):
            branch = {
                'decision_point': i,
                'question': f'At the {i}th crossroads, the {protagonist} must decide:',
                'option_a': random.choice(['Trust the mysterious stranger', 'Flee from the looming danger', 'Seek an ancient artifact', 'Forge an uneasy alliance', 'Sacrifice a personal treasure']),
                'option_b': random.choice(['Betray a close friend', 'Confront the enemy directly', 'Destroy the artifact', 'Negotiate for peace', 'Accept a dark pact']),
                'consequence': f'This choice will reshape the {["mid-game","late-game","final"][min(i-1,2)]} narrative.'
            }
            branches.append(branch)
        result = {
            'title': f'The {arc_key.title()} of the {protagonist.title()}',
            'genre': genre,
            'protagonist': protagonist,
            'antagonist': antagonist,
            'acts': [
                {'act': 'Act 1', 'scenes': act_templates['act1']},
                {'act': 'Act 2', 'scenes': act_templates['act2']},
                {'act': 'Act 3', 'scenes': act_templates['act3']}
            ],
            'subplots': subplots if subplots else ['No subplots provided. Focus on main narrative.'],
            'branching_choices': branches,
            'recommended_next': 'Continue the story by selecting a branching option or generating more details.'
        }
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "game_narrative_generator",
    "description": "Generate a branching narrative storyline for a role-playing game by specifying genre, character archetypes, and key plot points, returning a structured JSON with story beats, dialogue snippets, and branching choices.",
    "category": "generate",
    "domain": "entertainment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "genre": {
            "type": "string",
            "description": "The narrative genre for the story, e.g., fantasy, sci-fi, noir, romance, adventure.",
            "enum": [
                "fantasy",
                "sci-fi",
                "noir",
                "romance",
                "adventure",
                "horror",
                "comedy",
                "historical"
            ]
        },
        "protagonist_archetype": {
            "type": "string",
            "description": "The core archetype for the main character, e.g., hero, antihero, rogue, scholar, warrior.",
            "enum": [
                "hero",
                "antihero",
                "rogue",
                "scholar",
                "warrior",
                "mage",
                "detective",
                "survivor"
            ]
        },
        "antagonist_type": {
            "type": "string",
            "description": "The type of antagonist driving the conflict, e.g., villain, rival, monster, system, nature.",
            "enum": [
                "villain",
                "rival",
                "monster",
                "system",
                "nature",
                "betrayal",
                "corporate",
                "unknown"
            ]
        },
        "plot_seeds": {
            "type": "array",
            "items": {
                "type": "string",
                "maxLength": 100
            },
            "description": "Optional: List of specific plot ideas, key events, or themes to incorporate into the narrative. Each item up to 100 characters.",
            "maxItems": 5
        },
        "branching_levels": {
            "type": "integer",
            "description": "Optional: Number of branching decision points to include in the narrative (1-5). Default is 3.",
            "minimum": 1,
            "maximum": 5
        }
    },
    "required": [
        "genre",
        "protagonist_archetype",
        "antagonist_type"
    ]
},
}
