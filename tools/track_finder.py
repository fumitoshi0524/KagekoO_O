"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        query = data.get('query', '').strip()
        if not query:
            return json.dumps({'error': 'query is required'}, ensure_ascii=False)
        artist = data.get('artist', '').strip()
        genre = data.get('genre', '').strip().lower()
        limit = data.get('limit', 10)
        if not isinstance(limit, int) or limit < 1 or limit > 50:
            limit = 10
        # Simulated music database with ~20 tracks
        music_db = [
            {'title': 'Bohemian Rhapsody', 'artist': 'Queen', 'album': 'A Night at the Opera', 'year': 1975, 'genre': 'rock', 'preview_url': 'https://example.com/preview/bohemian_rhapsody.mp3'},
            {'title': 'Stairway to Heaven', 'artist': 'Led Zeppelin', 'album': 'Led Zeppelin IV', 'year': 1971, 'genre': 'rock', 'preview_url': 'https://example.com/preview/stairway.mp3'},
            {'title': 'Imagine', 'artist': 'John Lennon', 'album': 'Imagine', 'year': 1971, 'genre': 'pop', 'preview_url': 'https://example.com/preview/imagine.mp3'},
            {'title': 'Smells Like Teen Spirit', 'artist': 'Nirvana', 'album': 'Nevermind', 'year': 1991, 'genre': 'rock', 'preview_url': 'https://example.com/preview/teen_spirit.mp3'},
            {'title': 'Billie Jean', 'artist': 'Michael Jackson', 'album': 'Thriller', 'year': 1982, 'genre': 'pop', 'preview_url': 'https://example.com/preview/billie_jean.mp3'},
            {'title': 'Hotel California', 'artist': 'Eagles', 'album': 'Hotel California', 'year': 1976, 'genre': 'rock', 'preview_url': 'https://example.com/preview/hotel_california.mp3'},
            {'title': 'Back in Black', 'artist': 'AC/DC', 'album': 'Back in Black', 'year': 1980, 'genre': 'rock', 'preview_url': 'https://example.com/preview/back_in_black.mp3'},
            {'title': 'Shape of You', 'artist': 'Ed Sheeran', 'album': 'Divide', 'year': 2017, 'genre': 'pop', 'preview_url': 'https://example.com/preview/shape_of_you.mp3'},
            {'title': 'Blinding Lights', 'artist': 'The Weeknd', 'album': 'After Hours', 'year': 2020, 'genre': 'pop', 'preview_url': 'https://example.com/preview/blinding_lights.mp3'},
            {'title': 'Take Five', 'artist': 'Dave Brubeck', 'album': 'Time Out', 'year': 1959, 'genre': 'jazz', 'preview_url': 'https://example.com/preview/take_five.mp3'},
            {'title': 'So What', 'artist': 'Miles Davis', 'album': 'Kind of Blue', 'year': 1959, 'genre': 'jazz', 'preview_url': 'https://example.com/preview/so_what.mp3'},
            {'title': 'The Four Seasons: Spring', 'artist': 'Vivaldi', 'album': 'The Four Seasons', 'year': 1723, 'genre': 'classical', 'preview_url': 'https://example.com/preview/spring.mp3'},
            {'title': 'Canon in D', 'artist': 'Pachelbel', 'album': 'Canon and Gigue', 'year': 1680, 'genre': 'classical', 'preview_url': 'https://example.com/preview/canon.mp3'},
            {'title': 'Strobe', 'artist': 'Deadmau5', 'album': 'For Lack of a Better Name', 'year': 2009, 'genre': 'electronic', 'preview_url': 'https://example.com/preview/strobe.mp3'},
            {'title': 'Levels', 'artist': 'Avicii', 'album': 'Levels', 'year': 2011, 'genre': 'electronic', 'preview_url': 'https://example.com/preview/levels.mp3'},
            {'title': 'Beat It', 'artist': 'Michael Jackson', 'album': 'Thriller', 'year': 1982, 'genre': 'pop', 'preview_url': 'https://example.com/preview/beat_it.mp3'},
            {'title': 'Lose Yourself', 'artist': 'Eminem', 'album': '8 Mile Soundtrack', 'year': 2002, 'genre': 'hiphop', 'preview_url': 'https://example.com/preview/lose_yourself.mp3'},
            {'title': 'Alright', 'artist': 'Kendrick Lamar', 'album': 'To Pimp a Butterfly', 'year': 2015, 'genre': 'hiphop', 'preview_url': 'https://example.com/preview/alright.mp3'},
            {'title': 'Old Town Road', 'artist': 'Lil Nas X', 'album': '7 EP', 'year': 2019, 'genre': 'country', 'preview_url': 'https://example.com/preview/old_town_road.mp3'},
            {'title': 'Hips Don\'t Lie', 'artist': 'Shakira', 'album': 'Oral Fixation Vol. 2', 'year': 2005, 'genre': 'latin', 'preview_url': 'https://example.com/preview/hips_dont_lie.mp3'}
        ]
        results = []
        for t in music_db:
            q = query.lower()
            match = q in t['title'].lower() or q in t['artist'].lower() or q in t['album'].lower()
            if artist:
                match = match and artist.lower() in t['artist'].lower()
            if genre:
                valid_genres = ['pop','rock','jazz','electronic','classical','hiphop','rnb','country','latin','indie']
                match = match and (genre in valid_genres and t['genre'] == genre)
            if match:
                results.append(t)
        results = results[:limit]
        return json.dumps({'results': results, 'count': len(results)}, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "track_finder",
    "description": "Search for music tracks by title, artist, or album and return matching songs with artist, album, year, genre, and a preview URL.",
    "category": "search",
    "domain": "entertainment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "The search query, e.g. track title, artist name, or album name."
        },
        "artist": {
            "type": "string",
            "description": "Optional: Filter results by a specific artist name."
        },
        "genre": {
            "type": "string",
            "description": "Optional: Filter results by genre (e.g., 'rock', 'jazz', 'electronic'). Supported genres: pop, rock, jazz, electronic, classical, hiphop, rnb, country, latin, indie."
        },
        "limit": {
            "type": "integer",
            "description": "Optional: Maximum number of results to return (1–50, default 10).",
            "minimum": 1,
            "maximum": 50
        }
    },
    "required": [
        "query"
    ]
},
}
