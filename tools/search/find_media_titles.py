"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Search for films, TV series, and music albums by title keyword and return matching titles with release year, genre, and media type."""
    import json
    try:
        data = json.loads(payload)
        keyword = data.get('keyword')
        if not keyword or not isinstance(keyword, str) or len(keyword.strip()) < 2:
            return json.dumps({'error': 'keyword must be a string with at least 2 characters'}, ensure_ascii=False)

        media_type = data.get('media_type', 'all')
        if media_type not in ['film', 'tv_series', 'music_album', 'all']:
            return json.dumps({'error': 'media_type must be one of: film, tv_series, music_album, all'}, ensure_ascii=False)

        max_results = data.get('max_results', 10)
        if not isinstance(max_results, int) or max_results < 1 or max_results > 50:
            return json.dumps({'error': 'max_results must be an integer between 1 and 50'}, ensure_ascii=False)

        # Simulated media database with realistic titles (in production this would query a real API or database)
        media_database = [
            {'title': 'Inception', 'year': 2010, 'genre': 'Sci-Fi', 'media_type': 'film', 'rating': 8.8},
            {'title': 'The Matrix', 'year': 1999, 'genre': 'Action', 'media_type': 'film', 'rating': 8.7},
            {'title': 'Breaking Bad', 'year': 2008, 'genre': 'Drama', 'media_type': 'tv_series', 'rating': 9.5},
            {'title': 'Stranger Things', 'year': 2016, 'genre': 'Horror', 'media_type': 'tv_series', 'rating': 8.7},
            {'title': 'Thriller', 'year': 1982, 'genre': 'Pop', 'media_type': 'music_album', 'artist': 'Michael Jackson', 'rating': 9.1},
            {'title': 'Abbey Road', 'year': 1969, 'genre': 'Rock', 'media_type': 'music_album', 'artist': 'The Beatles', 'rating': 9.3},
            {'title': 'The Dark Knight', 'year': 2008, 'genre': 'Action', 'media_type': 'film', 'rating': 9.0},
            {'title': 'Game of Thrones', 'year': 2011, 'genre': 'Fantasy', 'media_type': 'tv_series', 'rating': 9.2},
            {'title': 'Back in Black', 'year': 1980, 'genre': 'Hard Rock', 'media_type': 'music_album', 'artist': 'AC/DC', 'rating': 9.0},
            {'title': 'Interstellar', 'year': 2014, 'genre': 'Sci-Fi', 'media_type': 'film', 'rating': 8.6},
            {'title': 'The Office', 'year': 2005, 'genre': 'Comedy', 'media_type': 'tv_series', 'rating': 8.9},
            {'title': 'Random Access Memories', 'year': 2013, 'genre': 'Electronic', 'media_type': 'music_album', 'artist': 'Daft Punk', 'rating': 8.8},
            {'title': 'Pulp Fiction', 'year': 1994, 'genre': 'Crime', 'media_type': 'film', 'rating': 8.9},
            {'title': 'Friends', 'year': 1994, 'genre': 'Comedy', 'media_type': 'tv_series', 'rating': 8.9},
            {'title': 'Hotel California', 'year': 1976, 'genre': 'Rock', 'media_type': 'music_album', 'artist': 'Eagles', 'rating': 8.7},
            {'title': 'The Shawshank Redemption', 'year': 1994, 'genre': 'Drama', 'media_type': 'film', 'rating': 9.3},
            {'title': 'The Crown', 'year': 2016, 'genre': 'History', 'media_type': 'tv_series', 'rating': 8.6},
            {'title': 'Rumours', 'year': 1977, 'genre': 'Rock', 'media_type': 'music_album', 'artist': 'Fleetwood Mac', 'rating': 9.1},
        ]

        keyword_lower = keyword.strip().lower()

        # Filter by keyword match in title
        results = []
        for item in media_database:
            if keyword_lower in item['title'].lower():
                if media_type == 'all' or item['media_type'] == media_type:
                    # Build result without rating (just title, year, genre, media_type)
                    result_item = {
                        'title': item['title'],
                        'year': item['year'],
                        'genre': item['genre'],
                        'media_type': item['media_type']
                    }
                    if item['media_type'] == 'music_album':
                        result_item['artist'] = item['artist']
                    results.append(result_item)

        # Sort by year descending, then title
        results.sort(key=lambda x: (-x['year'], x['title']))

        # Limit results
        results = results[:max_results]

        response = {
            'query': keyword.strip(),
            'media_type_filter': media_type if media_type != 'all' else 'all',
            'total_results': len(results),
            'results': results
        }
        return json.dumps(response, ensure_ascii=False)

    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "find_media_titles",
    "description": "Search for films, TV series, and music albums by title keyword and return matching titles with their release year, genre, and media type.",
    "category": "search",
    "domain": "entertainment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "keyword": {
            "type": "string",
            "description": "The title keyword or phrase to search for (e.g. movie name, album name, show name). Minimum 2 characters."
        },
        "media_type": {
            "type": "string",
            "enum": [
                "film",
                "tv_series",
                "music_album",
                "all"
            ],
            "description": "Optional: Filter results by media type. Default is 'all'."
        },
        "max_results": {
            "type": "integer",
            "description": "Optional: Maximum number of results to return (1-50). Default is 10.",
            "minimum": 1,
            "maximum": 50
        }
    },
    "required": [
        "keyword"
    ]
},
}
