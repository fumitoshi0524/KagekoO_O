"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Query a curated database of cultural festivals worldwide."""
    import json
    try:
        data = json.loads(payload)
        country = data.get('country')
        month = data.get('month')
        festival_type = data.get('festival_type')
        keyword = data.get('keyword')

        if month is not None:
            if not isinstance(month, int) or month < 1 or month > 12:
                return json.dumps({'error': 'month must be an integer between 1 and 12'}, ensure_ascii=False)

        if festival_type is not None:
            valid_types = ['religious', 'harvest', 'music', 'film', 'food', 'dance', 'historical', 'seasonal']
            if festival_type not in valid_types:
                return json.dumps({'error': f'festival_type must be one of {valid_types}'}, ensure_ascii=False)

        # Curated database of festivals (extendable)
        festivals = [
            {'name': 'Diwali', 'country': 'India', 'month': 10, 'type': 'religious', 'duration_days': 5, 'description': 'Festival of lights, symbolizing victory of light over darkness.'},
            {'name': 'Holi', 'country': 'India', 'month': 3, 'type': 'religious', 'duration_days': 2, 'description': 'Festival of colors, celebrating spring and love.'},
            {'name': 'Hanami', 'country': 'Japan', 'month': 3, 'type': 'seasonal', 'duration_days': 14, 'description': 'Cherry blossom viewing festival.'},
            {'name': 'Gion Matsuri', 'country': 'Japan', 'month': 7, 'type': 'religious', 'duration_days': 31, 'description': 'One of Japan\'s most famous festivals with parades and street food.'},
            {'name': 'Dia de los Muertos', 'country': 'Mexico', 'month': 11, 'type': 'religious', 'duration_days': 2, 'description': 'Day of the Dead, honoring deceased loved ones with altars and offerings.'},
            {'name': 'Oktoberfest', 'country': 'Germany', 'month': 9, 'type': 'food', 'duration_days': 16, 'description': 'World-famous beer festival and folk culture celebration.'},
            {'name': 'Carnival', 'country': 'Brazil', 'month': 2, 'type': 'dance', 'duration_days': 5, 'description': 'Largest carnival celebration with samba parades and music.'},
            {'name': 'Chinese New Year', 'country': 'China', 'month': 1, 'type': 'seasonal', 'duration_days': 15, 'description': 'Lunar New Year festival with fireworks, lanterns, and family gatherings.'},
            {'name': 'Glastonbury Festival', 'country': 'United Kingdom', 'month': 6, 'type': 'music', 'duration_days': 5, 'description': 'Iconic music and performing arts festival.'},
            {'name': 'Edinburgh Fringe', 'country': 'United Kingdom', 'month': 8, 'type': 'film', 'duration_days': 25, 'description': 'World\'s largest arts festival featuring theater, comedy, dance, and film.'}
        ]

        # Filtering
        filtered = festivals[:]
        if country:
            filtered = [f for f in filtered if f['country'].lower() == country.lower()]
        if month:
            filtered = [f for f in filtered if f['month'] == month]
        if festival_type:
            filtered = [f for f in filtered if f['type'] == festival_type]
        if keyword:
            keyword_lower = keyword.lower()
            filtered = [f for f in filtered if keyword_lower in f['name'].lower() or keyword_lower in f['description'].lower()]

        # Sort by month for consistent ordering
        filtered.sort(key=lambda x: x['month'])

        result = {
            'count': len(filtered),
            'festivals': filtered
        }
        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "cultural_festival_database",
    "description": "Query a curated database of cultural festivals worldwide to retrieve details such as name, location, date, type, duration, and associated cultural significance. Returns festival entries matching user-specified criteria (e.g., by country, month, or festival type) for event planning, educational research, or cultural exploration.",
    "category": "system",
    "domain": "culture",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "country": {
            "type": "string",
            "description": "Name of a country to filter festivals by (e.g., 'India', 'Japan'). If not provided, all countries are considered.",
            "examples": [
                "India",
                "Japan",
                "Mexico"
            ]
        },
        "month": {
            "type": "integer",
            "description": "Month number (1-12) to filter festivals that typically occur in that month. Optional.",
            "minimum": 1,
            "maximum": 12,
            "examples": [
                10,
                12
            ]
        },
        "festival_type": {
            "type": "string",
            "description": "Category of festival to search for. If provided, must be one of the predefined types: religious, harvest, music, film, food, dance, historical, or seasonal.",
            "enum": [
                "religious",
                "harvest",
                "music",
                "film",
                "food",
                "dance",
                "historical",
                "seasonal"
            ],
            "examples": [
                "music",
                "food"
            ]
        },
        "keyword": {
            "type": "string",
            "description": "Optional: free-text keyword to search in festival names or descriptions (e.g., 'lantern', 'carnival').",
            "examples": [
                "lantern",
                "carnival"
            ]
        }
    },
    "required": []
},
}
