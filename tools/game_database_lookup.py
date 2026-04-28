"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Search a video game database by title, genre, or platform to retrieve game metadata."""
    import json
    try:
        data = json.loads(payload)
        title = data.get('title', '').strip()
        if not title:
            return json.dumps({'error': 'Missing required parameter: title'}, ensure_ascii=False)
        genre = data.get('genre', '').strip()
        platform = data.get('platform', '').strip()
        min_score = data.get('min_score')
        max_results = data.get('max_results', 10)
        if not isinstance(max_results, int) or max_results < 1:
            max_results = 10
        if max_results > 50:
            max_results = 50

        # Simulated game database (in production would be a real search engine)
        games_db = [
            {'id': 1, 'title': 'The Legend of Zelda: Breath of the Wild', 'genre': 'Action-Adventure', 'platform': 'Nintendo Switch', 'release_year': 2017, 'publisher': 'Nintendo', 'developer': 'Nintendo EPD', 'esrb': 'E10+', 'score': 97},
            {'id': 2, 'title': 'Elden Ring', 'genre': 'RPG', 'platform': 'PC', 'release_year': 2022, 'publisher': 'Bandai Namco', 'developer': 'FromSoftware', 'esrb': 'M', 'score': 96},
            {'id': 3, 'title': 'God of War (2018)', 'genre': 'Action-Adventure', 'platform': 'PlayStation 4', 'release_year': 2018, 'publisher': 'Sony Interactive Entertainment', 'developer': 'Santa Monica Studio', 'esrb': 'M', 'score': 94},
            {'id': 4, 'title': 'Red Dead Redemption 2', 'genre': 'Action-Adventure', 'platform': 'PC', 'release_year': 2019, 'publisher': 'Rockstar Games', 'developer': 'Rockstar Studios', 'esrb': 'M', 'score': 97},
            {'id': 5, 'title': 'Super Mario Odyssey', 'genre': 'Platformer', 'platform': 'Nintendo Switch', 'release_year': 2017, 'publisher': 'Nintendo', 'developer': 'Nintendo EPD', 'esrb': 'E', 'score': 97},
            {'id': 6, 'title': 'The Witcher 3: Wild Hunt', 'genre': 'RPG', 'platform': 'PC', 'release_year': 2015, 'publisher': 'CD Projekt', 'developer': 'CD Projekt Red', 'esrb': 'M', 'score': 93},
            {'id': 7, 'title': 'Horizon Zero Dawn', 'genre': 'Action-RPG', 'platform': 'PlayStation 4', 'release_year': 2017, 'publisher': 'Sony Interactive Entertainment', 'developer': 'Guerrilla Games', 'esrb': 'T', 'score': 89},
            {'id': 8, 'title': 'Minecraft', 'genre': 'Sandbox', 'platform': 'PC', 'release_year': 2011, 'publisher': 'Mojang', 'developer': 'Mojang AB', 'esrb': 'E10+', 'score': 93},
            {'id': 9, 'title': 'Fortnite', 'genre': 'Battle Royale', 'platform': 'PC', 'release_year': 2017, 'publisher': 'Epic Games', 'developer': 'Epic Games', 'esrb': 'T', 'score': 81},
            {'id': 10, 'title': 'Cyberpunk 2077', 'genre': 'RPG', 'platform': 'PC', 'release_year': 2020, 'publisher': 'CD Projekt', 'developer': 'CD Projekt Red', 'esrb': 'M', 'score': 86},
            {'id': 11, 'title': 'Animal Crossing: New Horizons', 'genre': 'Simulation', 'platform': 'Nintendo Switch', 'release_year': 2020, 'publisher': 'Nintendo', 'developer': 'Nintendo EPD', 'esrb': 'E', 'score': 90},
            {'id': 12, 'title': 'Grand Theft Auto V', 'genre': 'Action-Adventure', 'platform': 'PlayStation 5', 'release_year': 2013, 'publisher': 'Rockstar Games', 'developer': 'Rockstar North', 'esrb': 'M', 'score': 96},
            {'id': 13, 'title': 'Overwatch 2', 'genre': 'First-Person Shooter', 'platform': 'PC', 'release_year': 2022, 'publisher': 'Blizzard Entertainment', 'developer': 'Blizzard Team 4', 'esrb': 'T', 'score': 79},
            {'id': 14, 'title': 'Hades', 'genre': 'Roguelike', 'platform': 'PC', 'release_year': 2020, 'publisher': 'Supergiant Games', 'developer': 'Supergiant Games', 'esrb': 'T', 'score': 93},
            {'id': 15, 'title': 'Final Fantasy VII Remake', 'genre': 'RPG', 'platform': 'PlayStation 5', 'release_year': 2020, 'publisher': 'Square Enix', 'developer': 'Square Enix', 'esrb': 'T', 'score': 88},
            {'id': 16, 'title': 'The Last of Us Part II', 'genre': 'Action-Adventure', 'platform': 'PlayStation 4', 'release_year': 2020, 'publisher': 'Sony Interactive Entertainment', 'developer': 'Naughty Dog', 'esrb': 'M', 'score': 93},
            {'id': 17, 'title': 'Doom Eternal', 'genre': 'First-Person Shooter', 'platform': 'PC', 'release_year': 2020, 'publisher': 'Bethesda Softworks', 'developer': 'id Software', 'esrb': 'M', 'score': 88},
            {'id': 18, 'title': 'Sekiro: Shadows Die Twice', 'genre': 'Action-Adventure', 'platform': 'PC', 'release_year': 2019, 'publisher': 'Activision', 'developer': 'FromSoftware', 'esrb': 'M', 'score': 90},
            {'id': 19, 'title': 'Stardew Valley', 'genre': 'Simulation', 'platform': 'PC', 'release_year': 2016, 'publisher': 'ConcernedApe', 'developer': 'ConcernedApe', 'esrb': 'E', 'score': 89},
            {'id': 20, 'title': 'Hollow Knight', 'genre': 'Metroidvania', 'platform': 'PC', 'release_year': 2017, 'publisher': 'Team Cherry', 'developer': 'Team Cherry', 'esrb': 'E10+', 'score': 87}
        ]

        # Filter logic
        results = []
        title_lower = title.lower()
        for game in games_db:
            if title_lower not in game['title'].lower():
                continue
            if genre and genre.strip().lower() != game['genre'].lower():
                continue
            if platform and platform.strip().lower() != game['platform'].lower():
                continue
            if min_score is not None:
                if not isinstance(min_score, (int, float)):
                    return json.dumps({'error': 'min_score must be a number'}, ensure_ascii=False)
                if game['score'] < min_score:
                    continue
            results.append(game)

        # Sort by score descending, then by title
        results.sort(key=lambda x: (-x['score'], x['title']))
        results = results[:max_results]

        return json.dumps({'results': results, 'count': len(results)}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "game_database_lookup",
    "description": "Search a video game database by title, genre, or platform to retrieve game metadata including release year, publisher, developer, genre, platform, ESRB rating, and aggregate critic score.",
    "category": "search",
    "domain": "entertainment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "title": {
            "type": "string",
            "description": "Full or partial game title to search for. Supports fuzzy matching."
        },
        "genre": {
            "type": "string",
            "description": "Optional: Filter by genre (e.g., 'Action', 'RPG', 'Strategy', 'Simulation', 'Sports')."
        },
        "platform": {
            "type": "string",
            "description": "Optional: Filter by platform (e.g., 'PC', 'PlayStation 5', 'Xbox Series X', 'Nintendo Switch')."
        },
        "min_score": {
            "type": "number",
            "description": "Optional: Minimum aggregate critic score (0-100) to filter results."
        },
        "max_results": {
            "type": "integer",
            "description": "Optional: Maximum number of results to return (default 10, max 50)."
        }
    },
    "required": [
        "title"
    ]
},
}
