"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    import random

    try:
        data = json.loads(payload)
        primary = data.get("primary_mythology", "").lower().strip()
        if not primary:
            return json.dumps({"error": "primary_mythology is required"}, ensure_ascii=False)
        if primary not in ["greek","norse","egyptian","hindu","chinese","japanese","mesoamerican"]:
            return json.dumps({"error": f"Unknown mythology: {primary}"}, ensure_ascii=False)

        secondary = data.get("secondary_theme", "").strip() or None
        creature_type = data.get("creature_type", "beast").strip()
        complexity = data.get("complexity", "standard").strip()

        # Mythological motifs per culture
        motif_pools = {
            "greek": {
                "creatures": {"dragon":"Lernaean Hydra","spirit":"Eidolon","beast":"Chimera","deity":"Titan"},
                "settings": ["Mount Olympus","the Labyrinth of Crete","the River Styx","the Underworld"],
                "symbols": ["ambition","fate","hubris","heroism","transformation"]
            },
            "norse": {
                "creatures": {"dragon":"Lindwyrm","spirit":"Draugr","beast":"Fenrir-wolf","deity":"Vættir"},
                "settings": ["Yggdrasil","Valhalla","Jotunheim","Niflheim"],
                "symbols": ["fate","endurance","wisdom","strength","sacrifice"]
            },
            "egyptian": {
                "creatures": {"dragon":"Apep","spirit":"Ba","beast":"Sphinx","deity":"Aker"},
                "settings": ["the Duat","the Nile","the Pyramids","the Field of Reeds"],
                "symbols": ["rebirth","ma'at","immortality","protection","knowledge"]
            },
            "hindu": {
                "creatures": {"dragon":"Naga","spirit":"Bhoot","beast":"Makara","deity":"Deva"},
                "settings": ["Mount Meru","the Ganges","the Cosmic Ocean","Vrindavan"],
                "symbols": ["dharma","karma","maya","devotion","cosmic order"]
            },
            "chinese": {
                "creatures": {"dragon":"Tianlong","spirit":"Gui","beast":"Qilin","deity":"Xian"},
                "settings": ["the Celestial Palace","the Pearl River","the Jade Mountain","the Eastern Sea"],
                "symbols": ["balance","prosperity","wisdom","harmony","longevity"]
            },
            "japanese": {
                "creatures": {"dragon":"Ryu","spirit":"Yokai","beast":"Kitsune","deity":"Kami"},
                "settings": ["Mount Fuji","the Inland Sea","the Bamboo Forest","Yomi"],
                "symbols": ["impermanence","ancestry","nature","honor","transience"]
            },
            "mesoamerican": {
                "creatures": {"dragon":"Feathered Serpent","spirit":"Nagual","beast":"Jaguar","deity":"Tlaloc"},
                "settings": ["Xibalba","the Underworld","the Jungle Temple","the Pyramid of the Sun"],
                "symbols": ["sacrifice","rebirth","rain","corn","war"]
            }
        }

        motif = motif_pools[primary]
        base_creature = motif["creatures"].get(creature_type, motif["creatures"]["beast"])
        setting = random.choice(motif["settings"])

        # Merge secondary theme if provided, else pick random from motif symbols
        if secondary:
            theme = secondary
        else:
            theme = random.choice(motif["symbols"])

        # Generate creature name by blending culture prefix + creature type
        name_prefix = {"greek":"Therion","norse":"Aldrnari","egyptian":"Shezmu","hindu":"Asura","chinese":"Shen","japanese":"Kami","mesoamerican":"Tonatiuh"}
        prefix = name_prefix[primary]
        creature_name = f"{prefix}-{base_creature.split()[0]}"

        # Generate story based on complexity
        if complexity == "short":
            story = f"The {creature_name} was born from the heart of {setting}, a {creature_type} of {theme}."
        elif complexity == "epic":
            story = f"In the age when {setting} echoed with the first footsteps of creation, the {creature_name} awakened. Forged from {theme} and wrapped in the shadows of the {primary} cosmos, this {creature_type} stalked the edge of reality. It was said that those who gazed upon the {creature_name} would forever dream of {setting}. The {creature_type} guarded a secret so profound that even the gods spoke of it in hushed tones—a secret that held the balance of {theme} itself."
        else:  # standard
            story = f"Legends tell of the {creature_name}, a {creature_type} born in {setting} when the first star of {theme} fell to earth. Its appearance signaled a great change, and the wise ones built shrines to honor the {creature_type}. To this day, the {creature_name} roams the boundary between the seen and unseen, a living emblem of {theme}."

        # Symbolic meaning
        meanings = {
            "greek": {"ambition":"drive for greatness","fate":"inescapable destiny","hubris":"danger of pride","heroism":"courage against odds","transformation":"change as growth"},
            "norse": {"fate":"woven destiny","endurance":"strength through hardship","wisdom":"knowledge from sacrifice","strength":"physical and moral power","sacrifice":"giving for greater good"},
            "egyptian": {"rebirth":"new life after death","ma'at":"balance and truth","immortality":"eternal existence","protection":"safeguarding the soul","knowledge":"divine understanding"},
            "hindu": {"dharma":"righteous duty","karma":"cause and effect","maya":"illusion of reality","devotion":"love for the divine","cosmic order":"universal rhythm"},
            "chinese": {"balance":"harmony of opposites","prosperity":"wealth and luck","wisdom":"deep understanding","harmony":"peaceful unity","longevity":"long life and health"},
            "japanese": {"impermanence":"transient beauty","ancestry":"respect for lineage","nature":"connection to the natural","honor":"integrity and duty","transience":"fleeting moments"},
            "mesoamerican": {"sacrifice":"offering for creation","rebirth":"cyclical renewal","rain":"life-giving waters","corn":"sustenance and civilization","war":"conflict and transformation"}
        }
        meaning = meanings.get(primary, {}).get(theme, f"a symbol of {theme}")

        result = {
            "creature_name": creature_name,
            "mythology": primary,
            "theme": theme,
            "creature_type": creature_type,
            "appearance": f"A majestic {base_creature.lower()} with {theme}-infused scales, eyes that glow like the stars above {setting}, and a presence that hums with ancient power.",
            "origin_legend": story,
            "symbolic_meaning": f"The {creature_name} represents {meaning}."
        }

        return json.dumps(result, ensure_ascii=False, indent=2)

    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON payload"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "myth_factory",
    "description": "Generate original mythological stories and creatures by blending cultural motifs from user-selected mythologies (Greek, Norse, Egyptian, Hindu, Chinese, Japanese, or Mesoamerican), returning a structured narrative with a creature name, appearance, origin legend, and symbolic meaning.",
    "category": "generate",
    "domain": "culture",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "primary_mythology": {
            "type": "string",
            "description": "Primary cultural mythology to base the creature and story on",
            "enum": [
                "greek",
                "norse",
                "egyptian",
                "hindu",
                "chinese",
                "japanese",
                "mesoamerican"
            ]
        },
        "secondary_theme": {
            "type": "string",
            "description": "Optional: Secondary theme or emotion to weave into the myth (e.g., 'betrayal', 'rebirth', 'thunder', 'moonlight')"
        },
        "creature_type": {
            "type": "string",
            "description": "Optional: Type of creature to generate (e.g., 'dragon', 'spirit', 'beast', 'deity')",
            "default": "beast"
        },
        "complexity": {
            "type": "string",
            "description": "Optional: Level of detail in the generated myth",
            "enum": [
                "short",
                "standard",
                "epic"
            ],
            "default": "standard"
        }
    },
    "required": [
        "primary_mythology"
    ]
},
}
