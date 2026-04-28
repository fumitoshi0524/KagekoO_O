"""Auto-generated tool module."""

from __future__ import annotations

import json
import random


def run(payload: str) -> str:
    """Generate a themed playlist or recommendation based on mood/genre."""
    try:
        data = json.loads(payload)
        mood = str(data.get("mood", "")).lower().strip()
        genre = str(data.get("genre", "")).lower().strip()
        count = min(int(data.get("count", 10)), 30)
    except (json.JSONDecodeError, TypeError, ValueError):
        mood = ""
        genre = ""
        count = 10

    _library = {
        "pop": ["Blinding Lights - The Weeknd", "Shape of You - Ed Sheeran", "Levitating - Dua Lipa", "Bad Guy - Billie Eilish", "Uptown Funk - Bruno Mars", "Shake It Off - Taylor Swift", "Happy - Pharrell Williams", "Don't Start Now - Dua Lipa", "Watermelon Sugar - Harry Styles", "Senorita - Shawn Mendes"],
        "rock": ["Bohemian Rhapsody - Queen", "Stairway to Heaven - Led Zeppelin", "Hotel California - Eagles", "Back in Black - AC/DC", "Smells Like Teen Spirit - Nirvana", "Sweet Child O' Mine - Guns N' Roses", "Paint It Black - The Rolling Stones", "Purple Haze - Jimi Hendrix", "Born to Run - Bruce Springsteen", "Free Bird - Lynyrd Skynyrd"],
        "electronic": ["Get Lucky - Daft Punk", "Strobe - Deadmau5", "Levels - Avicii", "Clarity - Zedd", "Titanium - David Guetta", "Scary Monsters - Skrillex", "Innerbloom - Rufus Du Sol", "Shelter - Porter Robinson", "Faded - Alan Walker", "Don't You Worry Child - Swedish House Mafia"],
        "jazz": ["Take Five - Dave Brubeck", "So What - Miles Davis", "My Favorite Things - John Coltrane", "Round Midnight - Thelonious Monk", "Summertime - Ella Fitzgerald", "Cantaloupe Island - Herbie Hancock", "A Night in Tunisia - Dizzy Gillespie", "Feeling Good - Nina Simone", "Autumn Leaves - Bill Evans", "Birdland - Weather Report"],
        "classical": ["Symphony No.5 - Beethoven", "Eine Kleine Nachtmusik - Mozart", "The Four Seasons - Vivaldi", "Clair de Lune - Debussy", "Canon in D - Pachelbel", "Ride of the Valkyries - Wagner", "Moonlight Sonata - Beethoven", "The Nutcracker Suite - Tchaikovsky", "Nocturne Op.9 No.2 - Chopin", "Boléro - Ravel"],
    }
    _mood_map = {
        "happy": ["pop", "electronic"],
        "energetic": ["rock", "electronic"],
        "relaxed": ["jazz", "classical"],
        "melancholy": ["jazz", "classical"],
        "focused": ["classical", "electronic"],
    }

    selected_genre = genre if genre in _library else None
    if not selected_genre and mood:
        candidates = _mood_map.get(mood, ["pop"])
        selected_genre = random.choice(candidates)
    if not selected_genre:
        selected_genre = random.choice(list(_library.keys()))

    tracks = random.sample(_library[selected_genre], min(count, len(_library[selected_genre])))
    random.shuffle(tracks)

    return json.dumps({
        "genre": selected_genre,
        "mood": mood or "auto",
        "playlist": [{"track": t.split(" - ")[0], "artist": t.split(" - ")[1] if " - " in t else "Unknown"} for t in tracks],
    }, indent=2, ensure_ascii=False)


TOOL_SPEC = {
    "name": "playlist_generator",
    "description": "Generate a themed music playlist based on mood (happy, energetic, relaxed, melancholy, focused) or genre (pop, rock, electronic, jazz, classical).",
    "category": "generate",
    "domain": "entertainment",
    "risk_level": "read",
    "schema": {
        "type": "object",
        "properties": {
            "mood": {
                "type": "string",
                "description": "Desired mood: happy, energetic, relaxed, melancholy, or focused.",
                "enum": ["happy", "energetic", "relaxed", "melancholy", "focused"]
            },
            "genre": {
                "type": "string",
                "description": "Music genre: pop, rock, electronic, jazz, or classical.",
                "enum": ["pop", "rock", "electronic", "jazz", "classical"]
            },
            "count": {
                "type": "integer",
                "description": "Number of tracks in the playlist (default: 10, max: 30)."
            }
        },
        "required": []
    }
}
