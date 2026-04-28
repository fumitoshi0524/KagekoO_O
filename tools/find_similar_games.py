"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Search for games similar to a given game by matching genre, platform, and player rating criteria."""
    import json
    try:
        data = json.loads(payload)
        
        # Validate required inputs
        if 'game_name' not in data or 'max_results' not in data:
            raise ValueError("Missing required parameters: game_name, max_results")
        
        game_name = data['game_name'].strip()
        max_results = int(data['max_results'])
        if max_results < 1 or max_results > 50:
            raise ValueError("max_results must be between 1 and 50")
        
        # Simulated database of games (in production, this would query an external API or database)
        games_db = [
            {"name": "The Legend of Zelda: Breath of the Wild", "genre": "adventure", "platform": "Nintendo Switch", "rating": 9.7, "year": 2017, "publisher": "Nintendo"},
            {"name": "Elden Ring", "genre": "rpg", "platform": "PC", "rating": 9.8, "year": 2022, "publisher": "Bandai Namco"},
            {"name": "God of War (2018)", "genre": "action", "platform": "PlayStation", "rating": 9.4, "year": 2018, "publisher": "Sony"},
            {"name": "Red Dead Redemption 2", "genre": "action", "platform": "Xbox", "rating": 9.7, "year": 2018, "publisher": "Rockstar Games"},
            {"name": "Minecraft", "genre": "adventure", "platform": "PC", "rating": 9.1, "year": 2011, "publisher": "Mojang"},
            {"name": "Fortnite", "genre": "shooter", "platform": "PC", "rating": 7.8, "year": 2017, "publisher": "Epic Games"},
            {"name": "Animal Crossing: New Horizons", "genre": "simulation", "platform": "Nintendo Switch", "rating": 8.8, "year": 2020, "publisher": "Nintendo"},
            {"name": "Cyberpunk 2077", "genre": "rpg", "platform": "PC", "rating": 7.5, "year": 2020, "publisher": "CD Projekt"},
            {"name": "Super Mario Odyssey", "genre": "platformer", "platform": "Nintendo Switch", "rating": 9.4, "year": 2017, "publisher": "Nintendo"},
            {"name": "The Witcher 3: Wild Hunt", "genre": "rpg", "platform": "PC", "rating": 9.6, "year": 2015, "publisher": "CD Projekt"},
            {"name": "Spider-Man (2018)", "genre": "action", "platform": "PlayStation", "rating": 9.0, "year": 2018, "publisher": "Sony"},
            {"name": "Call of Duty: Modern Warfare (2019)", "genre": "shooter", "platform": "Xbox", "rating": 8.2, "year": 2019, "publisher": "Activision"},
            {"name": "Stardew Valley", "genre": "simulation", "platform": "PC", "rating": 9.3, "year": 2016, "publisher": "ConcernedApe"},
            {"name": "Hades", "genre": "action", "platform": "PC", "rating": 9.5, "year": 2020, "publisher": "Supergiant Games"},
            {"name": "Among Us", "genre": "party", "platform": "mobile", "rating": 8.0, "year": 2018, "publisher": "Innersloth"}
        ]
        
        # Find reference game
        ref_game = None
        for game in games_db:
            if game_name.lower() in game['name'].lower():
                ref_game = game
                break
        
        if ref_game is None:
            return json.dumps({"error": f"Game '{game_name}' not found in database", "similar_games": []}, ensure_ascii=False)
        
        # Calculate similarity scores
        results = []
        for game in games_db:
            if game['name'] == ref_game['name']:
                continue
            
            score = 0.0
            # Genre match: +3 points
            if game['genre'] == ref_game['genre']:
                score += 3
            # Platform match: +2 points
            if game['platform'] == ref_game['platform']:
                score += 2
            # Rating proximity: up to +3 points (1 - |rating_diff|/10)
            rating_diff = abs(game['rating'] - ref_game['rating'])
            score += 3 * (1 - rating_diff / 10)
            # Year proximity: up to +2 points (1 - |year_diff|/20)
            year_diff = abs(game['year'] - ref_game['year'])
            score += 2 * (1 - min(year_diff / 20, 1.0))
            
            # Apply filters
            if 'min_rating' in data and data['min_rating'] is not None:
                if game['rating'] < float(data['min_rating']):
                    continue
            if 'platform' in data and data['platform'] is not None:
                if game['platform'] != data['platform']:
                    continue
            if 'genre' in data and data['genre'] is not None:
                if game['genre'] != data['genre']:
                    continue
            
            # Normalize score to 0-10
            normalized_score = round(score * 2.5, 1)  # Scale to 0-10 range for aesthetics
            normalized_score = min(normalized_score, 10.0)
            
            results.append({
                "name": game['name'],
                "genre": game['genre'],
                "platform": game['platform'],
                "rating": game['rating'],
                "year": game['year'],
                "publisher": game['publisher'],
                "similarity_score": normalized_score,
                "match_reason": f"{'genre' if game['genre'] == ref_game['genre'] else ''}{' and ' if game['genre'] == ref_game['genre'] and game['platform'] == ref_game['platform'] else ''}{'platform' if game['platform'] == ref_game['platform'] else ''} matches"
            })
        
        # Sort by similarity score descending
        results.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        # Return top results
        top_results = results[:max_results]
        
        result = {
            "reference_game": ref_game['name'],
            "similar_games": top_results,
            "total_found": len(results),
            "returned": len(top_results)
        }
        return json.dumps(result, ensure_ascii=False)
    except ValueError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Unexpected error: {e}"}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "find_similar_games",
    "description": "Search for games similar to a given game by matching genre, platform, and player rating criteria, returning ranked results with similarity scores and metadata.",
    "category": "search",
    "domain": "entertainment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "game_name": {
            "type": "string",
            "description": "Name of the reference game to find similar titles for"
        },
        "max_results": {
            "type": "integer",
            "description": "Maximum number of similar games to return (1-50)",
            "minimum": 1,
            "maximum": 50
        },
        "min_rating": {
            "type": "number",
            "description": "Optional: Minimum average player rating (0.0 to 10.0) to filter results",
            "minimum": 0.0,
            "maximum": 10.0
        },
        "platform": {
            "type": "string",
            "description": "Optional: Filter by platform (PC, PlayStation, Xbox, Nintendo Switch, mobile)",
            "enum": [
                "PC",
                "PlayStation",
                "Xbox",
                "Nintendo Switch",
                "mobile"
            ]
        },
        "genre": {
            "type": "string",
            "description": "Optional: Filter by genre (action, adventure, rpg, strategy, simulation, sports, puzzle, horror, fighting, racing, platformer, shooter, music, party)",
            "enum": [
                "action",
                "adventure",
                "rpg",
                "strategy",
                "simulation",
                "sports",
                "puzzle",
                "horror",
                "fighting",
                "racing",
                "platformer",
                "shooter",
                "music",
                "party"
            ]
        }
    },
    "required": [
        "game_name",
        "max_results"
    ]
},
}
