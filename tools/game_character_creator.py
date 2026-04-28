"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    import random
    from typing import Dict, Any

    try:
        data = json.loads(payload)
        genre = data.get("genre")
        if not genre:
            return json.dumps({"error": "Missing required parameter: genre"}, ensure_ascii=False)

        preferred_class = data.get("preferred_class")
        tone = data.get("tone", "heroic")
        power_level = data.get("power_level", 1)

        genre_races = {
            "high_fantasy": ["Human", "Elf", "Dwarf", "Halfling", "Gnome"],
            "dark_fantasy": ["Human", "Half-Orc", "Dark Elf", "Tiefling", "Aasimar"],
            "cyberpunk": ["Human (cyber-augmented)", "Android", "Cyborg", "Genetically Modified"],
            "space_opera": ["Human", "Krill", "Zarkonian", "Synthezoid", "Xenomorph Hybrid"],
            "steampunk": ["Human", "Automaton", "Clockwork Elf", "Gas-Folk"],
            "post_apocalyptic": ["Human", "Mutant", "Synth", "Ghoul", "Robotic Survivor"]
        }

        genre_classes = {
            "high_fantasy": ["Fighter", "Wizard", "Rogue", "Cleric", "Ranger", "Paladin"],
            "dark_fantasy": ["Blood Mage", "Shadow Knight", "Necromancer", "Barbarian", "Warlock"],
            "cyberpunk": ["Netrunner", "Street Samurai", "Fixer", "Techie"],
            "space_opera": ["Pilot", "Engineer", "Diplomat", "Soldier", "Medic"],
            "steampunk": ["Engineer", "Aeronaut", "Infiltrator", "Alchemist"],
            "post_apocalyptic": ["Scavenger", "Survivor", "Tech Wizard", "Mutant Hunter"]
        }

        races = genre_races.get(genre, ["Human"])
        classes = genre_classes.get(genre, ["Adventurer"])

        if preferred_class and preferred_class in classes:
            char_class = preferred_class
        else:
            char_class = random.choice(classes)

        char_race = random.choice(races)

        tone_backstories = {
            "heroic": f"A {char_race} {char_class} who {random.choice(['saved their village from destruction', 'discovered an ancient artifact', 'was blessed by a divine being', 'overcame a great personal tragedy'])} and now fights for justice.",
            "tragic": f"A {char_race} {char_class} who {random.choice(['lost their family to a plague', 'was betrayed by a trusted ally', 'cursed by a forgotten sorcerer', 'survived the fall of their homeland'])} and carries a heavy burden.",
            "mysterious": f"A {char_race} {char_class} with no memory of their past, only a {random.choice(['strange tattoo', 'cryptic note', 'powerful relic', 'mysterious scar'])} that hints at a forgotten destiny.",
            "comic": f"A {char_race} {char_class} who {random.choice(['accidentally became a hero while looking for their lost cat', 'is the worst of their kind but tries very hard', 'started adventuring because of a bad breakup', 'believes they are a character in a story'])} and has terrible luck."
        }

        backstory = tone_backstories[tone]

        stat_names = ["Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Charisma"]
        base = power_level + 3
        stats = {}
        for stat in stat_names:
            stats[stat] = random.randint(base - 2, base + 5)

        equipment_pool = [
            "Rusty shortsword", "Wooden shield", "Leather armor", "Healing potion (1 use)",
            "Torch (3 remaining)", "Rope (50ft)", "Backpack with rations (5 days)",
            "Lucky charm (just for show)", "Old map of unknown location", "20 gold pieces"
        ]
        equipment = random.sample(equipment_pool, min(3, len(equipment_pool)))

        character = {
            "name": f"{random.choice(['Aelar', 'Borin', 'Caelia', 'Drog', 'Elara', 'Finn', 'Grom', 'Halia', 'Ithil', 'Jorak', 'Kaelen', 'Lira'])} {random.choice(['Stormborn', 'Ironfist', 'Shadowwalker', 'Lightbringer', 'Nightshade', 'Thornwood', 'Fireheart'])}",
            "race": char_race,
            "class": char_class,
            "genre": genre,
            "power_level": power_level,
            "backstory": backstory,
            "stats": stats,
            "equipment": equipment,
            "special_ability": random.choice([
                "Can speak with animals (once per day)",
                "Minor telekinesis (up to 5 lbs)",
                "Night vision (up to 60ft)",
                "Resistance to fire damage",
                "Eidetic memory",
                "Increased running speed (+10ft per round)"
            ])
        }

        return json.dumps(character, ensure_ascii=False, indent=2)

    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON payload"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "game_character_creator",
    "description": "Generate a unique RPG character with a name, class, race, backstory, stats, and starting equipment based on player preferences and game genre, returning a complete character sheet suitable for tabletop or digital RPGs.",
    "category": "generate",
    "domain": "entertainment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "genre": {
            "type": "string",
            "description": "The fantasy or sci-fi genre for character creation, such as high fantasy, dark fantasy, cyberpunk, or space opera.",
            "enum": [
                "high_fantasy",
                "dark_fantasy",
                "cyberpunk",
                "space_opera",
                "steampunk",
                "post_apocalyptic"
            ]
        },
        "preferred_class": {
            "type": "string",
            "description": "Optional: Preferred character class (e.g., warrior, mage, rogue, ranger). If omitted, one is randomly assigned.",
            "default": null
        },
        "tone": {
            "type": "string",
            "description": "Optional: Narrative tone for the character's backstory and personality. Options: heroic, tragic, mysterious, comic.",
            "enum": [
                "heroic",
                "tragic",
                "mysterious",
                "comic"
            ],
            "default": "heroic"
        },
        "power_level": {
            "type": "integer",
            "description": "Optional: Initial power level from 1 to 20 (1 = novice, 20 = legendary). Default is 1.",
            "minimum": 1,
            "maximum": 20,
            "default": 1
        }
    },
    "required": [
        "genre"
    ]
},
}
