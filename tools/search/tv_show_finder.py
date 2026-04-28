"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Search for TV shows by title, genre, year range, or streaming platform and return matching results."""
    import json
    import random
    
    try:
        data = json.loads(payload)
        
        # Simulated TV show database
        tv_shows = [
            {"title": "Stranger Things", "year": 2016, "genre": "sci-fi", "rating": 8.7, "seasons": 4, "platforms": ["netflix"]},
            {"title": "The Crown", "year": 2016, "genre": "drama", "rating": 8.6, "seasons": 6, "platforms": ["netflix"]},
            {"title": "Breaking Bad", "year": 2008, "genre": "drama", "rating": 9.5, "seasons": 5, "platforms": ["netflix", "amazon_prime"]},
            {"title": "The Office US", "year": 2005, "genre": "comedy", "rating": 8.9, "seasons": 9, "platforms": ["peacock"]},
            {"title": "Game of Thrones", "year": 2011, "genre": "drama", "rating": 9.2, "seasons": 8, "platforms": ["hbo_max"]},
            {"title": "The Mandalorian", "year": 2019, "genre": "sci-fi", "rating": 8.7, "seasons": 3, "platforms": ["disney_plus"]},
            {"title": "Black Mirror", "year": 2011, "genre": "sci-fi", "rating": 8.8, "seasons": 5, "platforms": ["netflix"]},
            {"title": "Schitt's Creek", "year": 2015, "genre": "comedy", "rating": 8.5, "seasons": 6, "platforms": ["netflix", "hulu"]},
            {"title": "The Boys", "year": 2019, "genre": "thriller", "rating": 8.7, "seasons": 3, "platforms": ["amazon_prime"]},
            {"title": "Succession", "year": 2018, "genre": "drama", "rating": 8.8, "seasons": 4, "platforms": ["hbo_max"]},
            {"title": "Ted Lasso", "year": 2020, "genre": "comedy", "rating": 8.8, "seasons": 3, "platforms": ["apple_tv"]},
            {"title": "Squid Game", "year": 2021, "genre": "thriller", "rating": 8.0, "seasons": 1, "platforms": ["netflix"]},
            {"title": "Better Call Saul", "year": 2015, "genre": "drama", "rating": 8.9, "seasons": 6, "platforms": ["netflix", "amazon_prime"]},
            {"title": "The Witcher", "year": 2019, "genre": "fantasy", "rating": 8.2, "seasons": 3, "platforms": ["netflix"]},
            {"title": "Friends", "year": 1994, "genre": "comedy", "rating": 8.9, "seasons": 10, "platforms": ["hbo_max", "peacock"]},
            {"title": "The Simpsons", "year": 1989, "genre": "comedy", "rating": 8.7, "seasons": 34, "platforms": ["disney_plus"]},
            {"title": "Chernobyl", "year": 2019, "genre": "drama", "rating": 9.4, "seasons": 1, "platforms": ["hbo_max"]},
            {"title": "The Last of Us", "year": 2023, "genre": "drama", "rating": 8.8, "seasons": 1, "platforms": ["hbo_max"]},
            {"title": "Severance", "year": 2022, "genre": "thriller", "rating": 8.7, "seasons": 1, "platforms": ["apple_tv"]},
            {"title": "Rick and Morty", "year": 2013, "genre": "comedy", "rating": 9.1, "seasons": 6, "platforms": ["hulu", "hbo_max"]}
        ]
        
        results = tv_shows.copy()
        
        # Apply filters
        if "title" in data and data["title"]:
            title_lower = data["title"].lower()
            results = [show for show in results if title_lower in show["title"].lower()]
        
        if "genre" in data and data["genre"]:
            genre_lower = data["genre"].lower()
            results = [show for show in results if genre_lower == show["genre"].lower()]
        
        if "year_min" in data and data["year_min"] is not None:
            results = [show for show in results if show["year"] >= data["year_min"]]
        
        if "year_max" in data and data["year_max"] is not None:
            results = [show for show in results if show["year"] <= data["year_max"]]
        
        if "streaming_platform" in data and data["streaming_platform"]:
            platform = data["streaming_platform"].lower()
            results = [show for show in results if platform in show["platforms"]]
        
        if "min_rating" in data and data["min_rating"] is not None:
            rating = float(data["min_rating"])
            results = [show for show in results if show["rating"] >= rating]
        
        # Sort by rating descending
        results.sort(key=lambda x: x["rating"], reverse=True)
        
        # Limit results
        max_results = min(data.get("max_results", 10), 50)
        results = results[:max_results]
        
        result = {
            "count": len(results),
            "shows": results
        }
        
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "tv_show_finder",
    "description": "Search for TV shows by title, genre, year range, or streaming platform and return a list of matching shows with their ratings, seasons count, and available platforms.",
    "category": "search",
    "domain": "entertainment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "title": {
            "type": "string",
            "description": "Full or partial TV show title to search for"
        },
        "genre": {
            "type": "string",
            "description": "Optional: Filter by genre such as drama, comedy, thriller, sci-fi, reality"
        },
        "year_min": {
            "type": "integer",
            "description": "Optional: Minimum release year to filter shows"
        },
        "year_max": {
            "type": "integer",
            "description": "Optional: Maximum release year to filter shows"
        },
        "streaming_platform": {
            "type": "string",
            "description": "Optional: Filter by streaming platform such as netflix, hulu, disney_plus, amazon_prime, hbo_max",
            "enum": [
                "netflix",
                "hulu",
                "disney_plus",
                "amazon_prime",
                "hbo_max",
                "peacock",
                "paramount_plus"
            ]
        },
        "min_rating": {
            "type": "number",
            "description": "Optional: Minimum IMDb rating (0.0 to 10.0) to filter shows"
        },
        "max_results": {
            "type": "integer",
            "description": "Optional: Maximum number of results to return (default 10, max 50)"
        }
    },
    "required": []
},
}
