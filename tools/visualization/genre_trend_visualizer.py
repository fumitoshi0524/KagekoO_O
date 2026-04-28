"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        media_type = data.get('media_type')
        time_range = data.get('time_range')
        genre_filter = data.get('genre')
        top_n = data.get('top_n', 10)
        if not media_type or time_range not in ['last_7_days', 'last_30_days', 'last_6_months', 'last_year']:
            return json.dumps({'error': 'Invalid or missing media_type or time_range'}, ensure_ascii=False)

        # Simulate genre trend data from a real database or API
        # This is a mock but follows the structure of real entertainment trend data
        mock_data = {
            'music': {
                'last_30_days': [{'genre': 'pop', 'popularity_score': 85, 'stream_count': 1200000, 'chart_entries': 45},
                                 {'genre': 'hip-hop', 'popularity_score': 78, 'stream_count': 950000, 'chart_entries': 38},
                                 {'genre': 'rock', 'popularity_score': 62, 'stream_count': 740000, 'chart_entries': 29},
                                 {'genre': 'electronic', 'popularity_score': 55, 'stream_count': 620000, 'chart_entries': 22},
                                 {'genre': 'jazz', 'popularity_score': 40, 'stream_count': 480000, 'chart_entries': 15},
                                 {'genre': 'classical', 'popularity_score': 30, 'stream_count': 350000, 'chart_entries': 10},
                                 {'genre': 'reggae', 'popularity_score': 25, 'stream_count': 200000, 'chart_entries': 8},
                                 {'genre': 'country', 'popularity_score': 58, 'stream_count': 680000, 'chart_entries': 24},
                                 {'genre': 'r&b', 'popularity_score': 70, 'stream_count': 880000, 'chart_entries': 32},
                                 {'genre': 'latin', 'popularity_score': 50, 'stream_count': 560000, 'chart_entries': 18}]
            },
            'movies': {
                'last_30_days': [{'genre': 'action', 'popularity_score': 92, 'box_office_revenue': 8500000, 'release_count': 12},
                                 {'genre': 'comedy', 'popularity_score': 80, 'box_office_revenue': 7200000, 'release_count': 15},
                                 {'genre': 'drama', 'popularity_score': 75, 'box_office_revenue': 6800000, 'release_count': 18},
                                 {'genre': 'horror', 'popularity_score': 68, 'box_office_revenue': 5500000, 'release_count': 9},
                                 {'genre': 'sci-fi', 'popularity_score': 88, 'box_office_revenue': 9200000, 'release_count': 7},
                                 {'genre': 'romance', 'popularity_score': 55, 'box_office_revenue': 4300000, 'release_count': 11},
                                 {'genre': 'thriller', 'popularity_score': 72, 'box_office_revenue': 6100000, 'release_count': 10},
                                 {'genre': 'animation', 'popularity_score': 85, 'box_office_revenue': 7800000, 'release_count': 6},
                                 {'genre': 'documentary', 'popularity_score': 45, 'box_office_revenue': 2900000, 'release_count': 14},
                                 {'genre': 'musical', 'popularity_score': 60, 'box_office_revenue': 4700000, 'release_count': 4}]
            },
            'tv_shows': {
                'last_30_days': [{'genre': 'drama', 'popularity_score': 91, 'viewers_millions': 15.2, 'season_count': 6},
                                 {'genre': 'comedy', 'popularity_score': 82, 'viewers_millions': 12.7, 'season_count': 8},
                                 {'genre': 'reality', 'popularity_score': 70, 'viewers_millions': 10.3, 'season_count': 5},
                                 {'genre': 'crime', 'popularity_score': 78, 'viewers_millions': 11.5, 'season_count': 7},
                                 {'genre': 'sci-fi', 'popularity_score': 85, 'viewers_millions': 13.9, 'season_count': 4},
                                 {'genre': 'fantasy', 'popularity_score': 88, 'viewers_millions': 14.6, 'season_count': 3},
                                 {'genre': 'documentary', 'popularity_score': 60, 'viewers_millions': 8.8, 'season_count': 10},
                                 {'genre': 'thriller', 'popularity_score': 74, 'viewers_millions': 10.9, 'season_count': 5},
                                 {'genre': 'mystery', 'popularity_score': 77, 'viewers_millions': 11.2, 'season_count': 4},
                                 {'genre': 'romance', 'popularity_score': 52, 'viewers_millions': 7.1, 'season_count': 3}]
            }
        }

        genre_data = mock_data.get(media_type, {}).get(time_range, [])
        if not genre_data:
            return json.dumps({'error': 'No data available for the specified media_type and time_range'}, ensure_ascii=False)

        # Apply optional genre filter
        if genre_filter:
            filtered = [g for g in genre_data if g['genre'].lower() == genre_filter.lower()]
            if not filtered:
                return json.dumps({'error': f'Genre "{genre_filter}" not found for {media_type}'}, ensure_ascii=False)
            genre_data = filtered

        # Sort by popularity_score descending and limit to top_n
        genre_data.sort(key=lambda x: x['popularity_score'], reverse=True)
        top_genres = genre_data[:top_n]

        result = {
            'media_type': media_type,
            'time_range': time_range,
            'genre_trends': top_genres,
            'visualization_type': 'bar_chart_or_line_graph',
            'x_axis': 'genre',
            'y_axis': 'popularity_score'
        }
        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "genre_trend_visualizer",
    "description": "Visualizes trending entertainment genres across music, movies, and TV shows over a specified time period, returning a structured dataset suitable for bar charts or line graphs to help content creators identify popular genres and plan their next projects.",
    "category": "visualization",
    "domain": "entertainment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "media_type": {
            "type": "string",
            "description": "The type of entertainment media to analyze for genre trends.",
            "enum": [
                "music",
                "movies",
                "tv_shows"
            ]
        },
        "time_range": {
            "type": "string",
            "description": "The historical time range over which to aggregate genre popularity data.",
            "enum": [
                "last_7_days",
                "last_30_days",
                "last_6_months",
                "last_year"
            ]
        },
        "genre": {
            "type": "string",
            "description": "Optional: Filter results to a single specific genre (e.g., 'pop', 'sci-fi', 'drama'). If omitted, all available genres are returned.",
            "examples": [
                "pop",
                "sci-fi",
                "drama"
            ]
        },
        "top_n": {
            "type": "integer",
            "description": "Optional: Number of top genres to return, sorted by popularity descending. Default is 10.",
            "minimum": 1,
            "maximum": 50,
            "examples": [
                5
            ]
        }
    },
    "required": [
        "media_type",
        "time_range"
    ]
},
}
