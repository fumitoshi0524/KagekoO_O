"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        query = data.get('query')
        if not query:
            return json.dumps({'error': 'Missing required parameter: query'}, ensure_ascii=False)
        media_type = data.get('media_type')
        year = data.get('year')
        # Simulated database of media metadata
        media_db = [
            {'title': 'The Matrix', 'type': 'movie', 'year': 1999, 'genre': 'Sci-Fi', 'cast': ['Keanu Reeves', 'Laurence Fishburne'], 'runtime': 136, 'rating': 8.7, 'streaming': ['Netflix']},
            {'title': 'Breaking Bad', 'type': 'tv_show', 'year': 2008, 'genre': 'Crime Drama', 'cast': ['Bryan Cranston', 'Aaron Paul'], 'runtime': 49, 'rating': 9.5, 'streaming': ['Netflix', 'AMC+']},
            {'title': 'Thriller', 'type': 'music_album', 'artist': 'Michael Jackson', 'year': 1982, 'genre': 'Pop', 'tracks': 9, 'rating': 9.6, 'streaming': ['Spotify', 'Apple Music']},
            {'title': 'The Legend of Zelda: Breath of the Wild', 'type': 'game', 'year': 2017, 'genre': 'Action-Adventure', 'publisher': 'Nintendo', 'rating': 9.8, 'streaming': []}
        ]
        results = [item for item in media_db if query.lower() in item['title'].lower()]
        if media_type:
            results = [item for item in results if item['type'] == media_type]
        if year:
            results = [item for item in results if item['year'] == year]
        if not results:
            return json.dumps({'results': [], 'message': 'No matching media found.'}, ensure_ascii=False)
        return json.dumps({'results': results}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "media_metadata_search",
    "description": "Search for movies, TV shows, music albums, or games by title, artist, or release year and retrieve full metadata including genre, cast/crew, runtime, rating, and streaming availability.",
    "category": "search",
    "domain": "entertainment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Search term: movie title, TV show name, album name, game title, or artist name."
        },
        "media_type": {
            "type": "string",
            "enum": [
                "movie",
                "tv_show",
                "music_album",
                "game"
            ],
            "description": "Category of media to restrict search to."
        },
        "year": {
            "type": "integer",
            "description": "Optional: release year filter (e.g., 2020)."
        }
    },
    "required": [
        "query"
    ]
},
}
