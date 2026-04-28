"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        items = data.get('data', [])
        chart_type = data.get('chart_type')
        if not items or not chart_type:
            return json.dumps({'error': 'Missing required input'})
        if chart_type == 'genre_distribution':
            genre_count = {}
            for item in items:
                g = item['genre']
                genre_count[g] = genre_count.get(g, 0) + 1
            result = {'chart': 'genre_distribution', 'data': [{'genre': k, 'count': v} for k, v in sorted(genre_count.items(), key=lambda x: -x[1])]}
        elif chart_type == 'rating_histogram':
            bins = {str(i): 0 for i in range(1, 11)}
            for item in items:
                r = int(round(item['rating']))
                if 1 <= r <= 10:
                    bins[str(r)] += 1
            result = {'chart': 'rating_histogram', 'data': [{'rating': int(k), 'count': v} for k, v in sorted(bins.items())]}
        elif chart_type == 'year_trend':
            year_count = {}
            for item in items:
                y = item['year']
                year_count[y] = year_count.get(y, 0) + 1
            result = {'chart': 'year_trend', 'data': [{'year': k, 'count': v} for k, v in sorted(year_count.items())]}
        else:
            return json.dumps({'error': 'Invalid chart_type'})
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "viewing_insights",
    "description": "Aggregate and display trend charts and statistics from a library of movies and TV shows by analyzing user ratings, genre distribution, and release patterns to provide actionable insights for content curators and enthusiasts.",
    "category": "visualization",
    "domain": "entertainment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "data": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Name of the movie or TV show."
                    },
                    "genre": {
                        "type": "string",
                        "description": "Primary genre of the content (e.g., Drama, Comedy, Sci-Fi)."
                    },
                    "rating": {
                        "type": "number",
                        "description": "User rating on a scale from 1 to 10."
                    },
                    "year": {
                        "type": "integer",
                        "description": "Release year (e.g., 2023)."
                    }
                },
                "required": [
                    "title",
                    "genre",
                    "rating",
                    "year"
                ]
            },
            "description": "Array of content objects with title, genre, rating, and year."
        },
        "chart_type": {
            "type": "string",
            "enum": [
                "genre_distribution",
                "rating_histogram",
                "year_trend"
            ],
            "description": "Type of visualization to generate: genre distribution pie chart, rating histogram, or trend over years."
        }
    },
    "required": [
        "data",
        "chart_type"
    ]
},
}
