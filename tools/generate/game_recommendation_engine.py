"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Suggests video games based on user preferences."""
    import json
    try:
        data = json.loads(payload)
        # Validate required inputs
        required = ["genres", "platform", "player_count", "maturity_rating"]
        for field in required:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        if not data["genres"] or len(data["genres"]) > 3:
            raise ValueError("genres must be a non-empty list with up to 3 items")
        # Internal game catalog (simplified)
        catalog = [
            {"title": "The Legend of Zelda: Breath of the Wild", "genre": "Adventure", "platform": "Nintendo Switch", "players": "Single-player", "rating": "E10+", "score": 97},
            {"title": "Elden Ring", "genre": "RPG", "platform": "PC", "players": "Single-player", "rating": "M", "score": 96},
            {"title": "Minecraft", "genre": "Simulation", "platform": "Any", "players": "Multiplayer", "rating": "E10+", "score": 93},
            {"title": "Fortnite", "genre": "Action", "platform": "Any", "players": "Multiplayer", "rating": "T", "score": 90},
            {"title": "Stardew Valley", "genre": "Simulation", "platform": "Any", "players": "Co-op", "rating": "E", "score": 89},
            {"title": "Hades", "genre": "Action", "platform": "PC", "players": "Single-player", "rating": "T", "score": 93},
            {"title": "It Takes Two", "genre": "Adventure", "platform": "Any", "players": "Co-op", "rating": "T", "score": 88},
            {"title": "Super Mario Odyssey", "genre": "Adventure", "platform": "Nintendo Switch", "players": "Single-player", "rating": "E", "score": 97},
            {"title": "Portal 2", "genre": "Puzzle", "platform": "PC", "players": "Co-op", "rating": "E10+", "score": 95},
            {"title": "Grand Theft Auto V", "genre": "Action", "platform": "PC", "players": "Multiplayer", "rating": "M", "score": 96},
            {"title": "Animal Crossing: New Horizons", "genre": "Simulation", "platform": "Nintendo Switch", "players": "Single-player", "rating": "E", "score": 90},
            {"title": "Overcooked! 2", "genre": "Simulation", "platform": "Any", "players": "Co-op", "rating": "E", "score": 84},
            {"title": "God of War (2018)", "genre": "Action", "platform": "PlayStation 5", "players": "Single-player", "rating": "M", "score": 94},
            {"title": "Rocket League", "genre": "Sports", "platform": "Any", "players": "Multiplayer", "rating": "E10+", "score": 89},
            {"title": "Among Us", "genre": "Puzzle", "platform": "Mobile", "players": "Multiplayer", "rating": "E10+", "score": 85},
            {"title": "Hollow Knight", "genre": "Adventure", "platform": "PC", "players": "Single-player", "rating": "E10+", "score": 91},
            {"title": "FIFA 23", "genre": "Sports", "platform": "Any", "players": "Multiplayer", "rating": "E", "score": 88},
            {"title": "Civilization VI", "genre": "Strategy", "platform": "PC", "players": "Single-player", "rating": "E10+", "score": 92},
            {"title": "Dark Souls III", "genre": "RPG", "platform": "PC", "players": "Single-player", "rating": "M", "score": 89},
            {"title": "Celeste", "genre": "Puzzle", "platform": "Any", "players": "Single-player", "rating": "E10+", "score": 92}
        ]
        # Filtering logic
        genres = [g.lower() for g in data["genres"]]
        platform = data["platform"]
        player_count = data["player_count"]
        max_rating_str = data["maturity_rating"]
        max_results = data.get("max_results", 5)
        rating_order = {"E": 0, "E10+": 1, "T": 2, "M": 3, "Any": 3}
        max_rating = rating_order.get(max_rating_str, 3)
        filtered = []
        for game in catalog:
            g_genre = game["genre"].lower()
            if g_genre not in genres:
                continue
            if platform != "Any" and game["platform"] != platform and game["platform"] != "Any":
                continue
            if player_count != "Any" and game["players"] != player_count:
                continue
            game_rating_level = rating_order.get(game["rating"], 3)
            if game_rating_level > max_rating:
                continue
            filtered.append(game)
        # Sort by score descending, limit
        filtered.sort(key=lambda x: x["score"], reverse=True)
        filtered = filtered[:max_results]
        if not filtered:
            return json.dumps({"recommendations": [], "message": "No games match your criteria. Try broadening your preferences."}, ensure_ascii=False)
        result = {"recommendations": filtered}
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f"error: {e}"


TOOL_SPEC = {
    "name": "game_recommendation_engine",
    "description": "Suggests video games from a curated catalog based on user preferences for genre, platform, player count, and maturity rating, returning a ranked list of up to 10 titles with key metadata for discovery and selection.",
    "category": "generate",
    "domain": "entertainment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "genres": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [
                    "Action",
                    "Adventure",
                    "RPG",
                    "Simulation",
                    "Strategy",
                    "Sports",
                    "Puzzle",
                    "Horror",
                    "Fighting",
                    "Racing",
                    "Educational"
                ]
            },
            "description": "Preferred game genres (list of up to 3)."
        },
        "platform": {
            "type": "string",
            "enum": [
                "PC",
                "PlayStation 5",
                "Xbox Series X",
                "Nintendo Switch",
                "Mobile",
                "Any"
            ],
            "description": "Target gaming platform."
        },
        "player_count": {
            "type": "string",
            "enum": [
                "Single-player",
                "Multiplayer",
                "Co-op",
                "Any"
            ],
            "description": "Preferred play style."
        },
        "maturity_rating": {
            "type": "string",
            "enum": [
                "E",
                "E10+",
                "T",
                "M",
                "Any"
            ],
            "description": "Maximum acceptable ESRB rating."
        },
        "max_results": {
            "type": "integer",
            "minimum": 1,
            "maximum": 10,
            "description": "Optional: Maximum number of recommendations to return (default 5)."
        }
    },
    "required": [
        "genres",
        "platform",
        "player_count",
        "maturity_rating"
    ]
},
}
