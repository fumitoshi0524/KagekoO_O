"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a creative movie synopsis based on genre, theme, and character archetypes."""
    import json
    try:
        data = json.loads(payload)
        genre = data.get("genre")
        theme = data.get("theme")
        prot_arche = data.get("protagonist_archetype", None)
        ant_arche = data.get("antagonist_archetype", None)

        if not genre or not theme:
            return json.dumps({"error": "Missing required fields: genre, theme"})

        # Templates for each genre
        templates = {
            "action": "In a world where {theme}, a {prot} must {ant_conflict} before time runs out.",
            "comedy": "When {theme}, a {prot} finds themselves in a hilarious situation involving {ant_conflict}.",
            "drama": "A {prot} confronts {theme} and must face {ant_conflict} to find redemption.",
            "horror": "Deep in {theme}, a {prot} discovers that {ant_conflict} is more terrifying than imagined.",
            "sci-fi": "In the future, {theme} threatens humanity. A {prot} must solve {ant_conflict}.",
            "romance": "Amidst {theme}, a {prot} falls for someone unexpectedly tied to {ant_conflict}.",
            "thriller": "When {theme}, a {prot} uncovers a deadly conspiracy involving {ant_conflict}."
        }

        prot_choice = prot_arche if prot_arche else "hero"
        ant_choice = ant_arche if ant_arche else "a powerful enemy"

        template = templates.get(genre, "A story about {theme} featuring a {prot} who deals with {ant_conflict}.")

        synopsis = template.format(
            theme=theme,
            prot=prot_choice.replace("_", " "),
            ant_conflict=ant_choice.replace("_", " ")
        )

        # More natural phrasing
        if genre == "comedy":
            synopsis = synopsis.replace("find themselves", "finds themselves")
        
        result = {
            "synopsis": synopsis,
            "genre": genre,
            "theme": theme,
            "protagonist_archetype": prot_arche,
            "antagonist_archetype": ant_arche
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


TOOL_SPEC = {
    "name": "movie_synopsis_generator",
    "description": "Generate a creative movie synopsis based on a genre, a central theme or conflict, and up to two main character archetypes. Returns a short, engaging plot summary suitable for pitching or brainstorming.",
    "category": "generate",
    "domain": "entertainment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "genre": {
            "type": "string",
            "enum": [
                "action",
                "comedy",
                "drama",
                "horror",
                "sci-fi",
                "romance",
                "thriller"
            ],
            "description": "The primary genre of the movie."
        },
        "theme": {
            "type": "string",
            "description": "The central theme, conflict, or high-concept idea (e.g., 'a detective who can see ghosts', 'time-loop on a spaceship')."
        },
        "protagonist_archetype": {
            "type": "string",
            "enum": [
                "reluctant_hero",
                "chosen_one",
                "detective",
                "lone_wolf",
                "fish_out_of_water",
                "mastermind"
            ],
            "description": "Optional: Archetype for the main protagonist."
        },
        "antagonist_archetype": {
            "type": "string",
            "enum": [
                "dark_reflection",
                "mastermind",
                "force_of_nature",
                "corrupt_institution",
                "personal_rival"
            ],
            "description": "Optional: Archetype for the main antagonist."
        }
    },
    "required": [
        "genre",
        "theme"
    ]
},
}
