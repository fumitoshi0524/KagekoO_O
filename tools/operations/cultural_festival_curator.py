"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        region = data.get('region')
        if not region:
            return json.dumps({'error': 'Missing required parameter: region'}, ensure_ascii=False)
        month = data.get('month')
        festival_type = data.get('festival_type')
        max_results = data.get('max_results', 5)

        # Simulated database of cultural festivals
        festivals_db = [
            {'name': 'SXSW', 'month': 'March', 'region': 'USA', 'type': 'multi_arts', 'location': 'Austin, Texas', 'description': 'A confluence of film, interactive media, and music festivals.'},
            {'name': 'Cannes Film Festival', 'month': 'May', 'region': 'France', 'type': 'film', 'location': 'Cannes, France', 'description': 'Annual film festival showcasing new films and honoring cinematic achievements.'},
            {'name': 'Oktoberfest', 'month': 'September', 'region': 'Germany', 'type': 'food', 'location': 'Munich, Germany', 'description': 'World-famous beer festival and folk tradition.'},
            {'name': 'Diwali Celebrations', 'month': 'October', 'region': 'India', 'type': 'multi_arts', 'location': 'Various cities, India', 'description': 'Festival of lights with fireworks, sweets, and cultural performances.'},
            {'name': 'Hanami', 'month': 'April', 'region': 'Japan', 'type': 'art', 'location': 'Tokyo, Japan', 'description': 'Traditional cherry blossom viewing festival with picnics and poetry.'},
            {'name': 'Glastonbury Festival', 'month': 'June', 'region': 'UK', 'type': 'music', 'location': 'Pilton, Somerset, UK', 'description': 'Five-day festival of contemporary performing arts.'},
            {'name': 'Fiesta de la Candelaria', 'month': 'February', 'region': 'Peru', 'type': 'multi_arts', 'location': 'Puno, Peru', 'description': 'Religious and cultural festival with parades, music, and dance.'},
            {'name': 'Venice Biennale', 'month': 'May', 'region': 'Italy', 'type': 'art', 'location': 'Venice, Italy', 'description': 'Major contemporary art exhibition held every two years.'},
            {'name': 'International Film Festival Rotterdam', 'month': 'January', 'region': 'Netherlands', 'type': 'film', 'location': 'Rotterdam, Netherlands', 'description': 'Festival with a focus on innovative and independent cinema.'},
            {'name': 'New Orleans Jazz & Heritage Festival', 'month': 'April', 'region': 'USA', 'type': 'music', 'location': 'New Orleans, Louisiana', 'description': 'Celebration of local music, food, and culture.'}
        ]

        filtered = []
        for fest in festivals_db:
            if region.lower() not in fest['region'].lower() and region.lower() != 'global' and region.lower() != 'worldwide':
                continue
            if month and fest['month'].lower() != month.lower():
                continue
            if festival_type and fest['type'] != festival_type:
                continue
            filtered.append(fest)

        # If region is Global/Worldwide, include all if no other filters
        if region.lower() in ['global', 'worldwide']:
            filtered = festivals_db[:]
            if month:
                filtered = [f for f in filtered if f['month'].lower() == month.lower()]
            if festival_type:
                filtered = [f for f in filtered if f['type'] == festival_type]

        # Sort by month order for consistency
        month_order = ['January','February','March','April','May','June','July','August','September','October','November','December']
        filtered.sort(key=lambda x: month_order.index(x['month']))

        # Limit results
        filtered = filtered[:max_results]

        result = {
            'festivals': filtered,
            'count': len(filtered),
            'query': {'region': region, 'month': month, 'type': festival_type}
        }
        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "cultural_festival_curator",
    "description": "Curate a personalized list of cultural festivals based on user preferences for region, time of year, and festival type (music, film, food, art, historical reenactment), returning festival names, dates, locations, brief descriptions, and thematic tags.",
    "category": "operations",
    "domain": "culture",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "region": {
            "type": "string",
            "description": "Geographic region or country to search for festivals (e.g., 'Japan', 'Europe', 'Global'). Accepts broad or specific region names.",
            "examples": [
                "Japan",
                "South America",
                "Worldwide"
            ]
        },
        "month": {
            "type": "string",
            "description": "Optional: Month of the year to filter festivals. If not provided, all months are considered.",
            "enum": [
                "January",
                "February",
                "March",
                "April",
                "May",
                "June",
                "July",
                "August",
                "September",
                "October",
                "November",
                "December"
            ],
            "examples": [
                "March",
                "October"
            ]
        },
        "festival_type": {
            "type": "string",
            "description": "Optional: Type of cultural festival to focus on. If not provided, all types are included.",
            "enum": [
                "music",
                "film",
                "food",
                "art",
                "historical_reenactment",
                "multi_arts"
            ],
            "examples": [
                "food",
                "film"
            ]
        },
        "max_results": {
            "type": "integer",
            "description": "Optional: Maximum number of festivals to return (1-20). Default is 5.",
            "minimum": 1,
            "maximum": 20,
            "default": 5,
            "examples": [
                3,
                10
            ]
        }
    },
    "required": [
        "region"
    ]
},
}
