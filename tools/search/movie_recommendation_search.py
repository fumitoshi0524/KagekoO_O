"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        # Simulate a local movie database (in production, use a real DB or API)
        movies = [
            {"title": "Inception", "year": 2010, "genre": "Sci-Fi", "language": "English", "rating": 8.8, "plot": "A thief who steals corporate secrets through dream-sharing technology is given the task of planting an idea."},
            {"title": "The Dark Knight", "year": 2008, "genre": "Action", "language": "English", "rating": 9.0, "plot": "Batman faces the Joker, a criminal mastermind who wants to plunge Gotham into chaos."},
            {"title": "Parasite", "year": 2019, "genre": "Drama", "language": "Korean", "rating": 8.6, "plot": "A poor family schemes to become employed by a wealthy family, leading to unexpected and dark consequences."},
            {"title": "Spirited Away", "year": 2001, "genre": "Animation", "language": "Japanese", "rating": 8.6, "plot": "A young girl enters a magical world where she must work to free her parents from a curse."},
            {"title": "The Matrix", "year": 1999, "genre": "Sci-Fi", "language": "English", "rating": 8.7, "plot": "A computer hacker learns about the true nature of reality and his role in the war against its controllers."},
            {"title": "Coco", "year": 2017, "genre": "Animation", "language": "English", "rating": 8.4, "plot": "A young musician journeys to the Land of the Dead to discover his family's history."},
            {"title": "Amélie", "year": 2001, "genre": "Comedy", "language": "French", "rating": 8.3, "plot": "A shy waitress decides to change the lives of those around her for the better."},
            {"title": "Oldboy", "year": 2003, "genre": "Thriller", "language": "Korean", "rating": 8.4, "plot": "A man is imprisoned for 15 years and then released, seeking revenge."}
        ]
        # Parse optional filters
        query = data.get('query', '').lower().strip()
        genre = data.get('genre', '').lower().strip()
        language = data.get('language', '').lower().strip()
        min_rating = data.get('min_rating', 0.0)
        year_from = data.get('year_from', 1900)
        year_to = data.get('year_to', 2030)
        max_results = min(data.get('max_results', 10), 50)
        # Filter
        results = []
        for m in movies:
            if query and query not in m['title'].lower() and query not in m['plot'].lower():
                continue
            if genre and genre not in m['genre'].lower():
                continue
            if language and language not in m['language'].lower():
                continue
            if m['rating'] < min_rating:
                continue
            if m['year'] < year_from or m['year'] > year_to:
                continue
            results.append(m)
        # Sort by rating descending
        results.sort(key=lambda x: x['rating'], reverse=True)
        # Limit results
        results = results[:max_results]
        return json.dumps({"results": results, "count": len(results)}, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "movie_recommendation_search",
    "description": "Search for movie recommendations by querying a local dataset of films based on genre, language, release year, or rating threshold, returning a list of matching movies with title, year, genre, language, rating, and plot summary.",
    "category": "search",
    "domain": "entertainment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Free-text search query to match against movie titles or plot summaries (e.g., 'time travel', 'sci-fi adventure')"
        },
        "genre": {
            "type": "string",
            "description": "Optional: Filter by genre (e.g., 'Action', 'Comedy', 'Drama', 'Horror', 'Sci-Fi')"
        },
        "language": {
            "type": "string",
            "description": "Optional: Filter by language (e.g., 'English', 'Hindi', 'French')"
        },
        "min_rating": {
            "type": "number",
            "description": "Optional: Minimum rating threshold (0.0 to 10.0) to filter movies by average user rating"
        },
        "year_from": {
            "type": "integer",
            "description": "Optional: Start year for release date filter (e.g., 2000)"
        },
        "year_to": {
            "type": "integer",
            "description": "Optional: End year for release date filter (e.g., 2025)"
        },
        "max_results": {
            "type": "integer",
            "description": "Optional: Maximum number of results to return (default 10, max 50)"
        }
    },
    "required": []
},
}
