"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Search across a database of professional and amateur athletes to find performers matching criteria."""
    import json
    try:
        data = json.loads(payload)
        sport = data.get('sport')
        if not sport:
            return 'error: sport is required'
        
        position = data.get('position')
        min_score = data.get('min_performance_score')
        age_min = data.get('age_min')
        age_max = data.get('age_max')
        nationality = data.get('nationality')
        team = data.get('team')
        active_only = data.get('active_only', False)
        search_query = data.get('search_query')
        
        # Simulated athlete database
        athletes_db = [
            {"id": 1, "name": "LeBron James", "sport": "basketball", "position": "forward", "age": 39, "nationality": "US", "team": "Los Angeles Lakers", "performance_score": 92, "active": True, "biography": "Four-time NBA champion and MVP"},
            {"id": 2, "name": "Lionel Messi", "sport": "soccer", "position": "forward", "age": 37, "nationality": "AR", "team": "Inter Miami", "performance_score": 94, "active": True, "biography": "Eight-time Ballon d'Or winner, World Cup champion"},
            {"id": 3, "name": "Katie Ledecky", "sport": "swimming", "position": "freestyle", "age": 27, "nationality": "US", "team": "Stanford Cardinal", "performance_score": 96, "active": True, "biography": "Seven-time Olympic gold medalist, world record holder"},
            {"id": 4, "name": "Usain Bolt", "sport": "athletics", "position": "sprinter", "age": 38, "nationality": "JM", "team": "Retired", "performance_score": 98, "active": False, "biography": "Eight-time Olympic gold medalist, world record holder in 100m and 200m"},
            {"id": 5, "name": "Serena Williams", "sport": "tennis", "position": "singles", "age": 43, "nationality": "US", "team": "N/A", "performance_score": 95, "active": False, "biography": "23 Grand Slam singles titles"},
            {"id": 6, "name": "Cristiano Ronaldo", "sport": "soccer", "position": "forward", "age": 39, "nationality": "PT", "team": "Al Nassr", "performance_score": 91, "active": True, "biography": "Five-time Ballon d'Or winner, all-time top scorer"},
            {"id": 7, "name": "Stephen Curry", "sport": "basketball", "position": "guard", "age": 36, "nationality": "US", "team": "Golden State Warriors", "performance_score": 93, "active": True, "biography": "Four-time NBA champion, greatest three-point shooter"},
            {"id": 8, "name": "Simone Biles", "sport": "gymnastics", "position": "all_around", "age": 27, "nationality": "US", "team": "N/A", "performance_score": 97, "active": True, "biography": "Seven-time Olympic medalist, most decorated gymnast"}
        ]
        
        # Filter by sport
        results = [a for a in athletes_db if a['sport'] == sport]
        
        # Apply filters
        if position:
            results = [a for a in results if a.get('position') == position]
        if min_score is not None:
            results = [a for a in results if a.get('performance_score', 0) >= min_score]
        if age_min is not None:
            results = [a for a in results if a.get('age', 0) >= age_min]
        if age_max is not None:
            results = [a for a in results if a.get('age', 0) <= age_max]
        if nationality:
            results = [a for a in results if a.get('nationality', '').upper() == nationality.upper()]
        if team:
            results = [a for a in results if team.lower() in a.get('team', '').lower()]
        if active_only:
            results = [a for a in results if a.get('active', False)]
        if search_query:
            query_lower = search_query.lower()
            results = [a for a in results if query_lower in a['name'].lower() or query_lower in a.get('biography', '').lower()]
        
        # Sort by performance score descending
        results.sort(key=lambda x: x.get('performance_score', 0), reverse=True)
        
        # Format output
        output = []
        for athlete in results:
            output.append({
                "name": athlete['name'],
                "sport": athlete['sport'],
                "position": athlete.get('position', 'N/A'),
                "age": athlete.get('age'),
                "nationality": athlete.get('nationality'),
                "team": athlete.get('team', 'N/A'),
                "performance_score": athlete.get('performance_score'),
                "active": athlete.get('active'),
                "biography_summary": athlete.get('biography', '')[:100]
            })
        
        result = {
            "total_results": len(output),
            "results": output,
            "search_parameters": {
                "sport": sport,
                "position": position,
                "min_performance_score": min_score,
                "age_min": age_min,
                "age_max": age_max,
                "nationality": nationality,
                "team": team,
                "active_only": active_only,
                "search_query": search_query
            }
        }
        
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "athlete_performance_search",
    "description": "Search across a database of professional and amateur athletes to find performers matching criteria such as sport type, position, minimum performance metrics, age range, and nationality, returning a ranked list of athletes with their key stats, team affiliation, and recent performance trends.",
    "category": "search",
    "domain": "sports",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "sport": {
            "type": "string",
            "description": "The sport category to search within, e.g. basketball, soccer, swimming, athletics",
            "enum": [
                "basketball",
                "soccer",
                "swimming",
                "athletics",
                "tennis",
                "golf",
                "baseball",
                "american_football",
                "hockey",
                "volleyball",
                "cricket",
                "rugby",
                "boxing",
                "cycling",
                "skiing",
                "other"
            ]
        },
        "position": {
            "type": "string",
            "description": "Optional: The specific position or event type the athlete competes in, e.g. point_guard, striker, breaststroke, sprinter"
        },
        "min_performance_score": {
            "type": "number",
            "description": "Optional: Minimum overall performance rating on a 0-100 scale to filter athletes"
        },
        "age_min": {
            "type": "integer",
            "description": "Optional: Minimum athlete age in years (inclusive)"
        },
        "age_max": {
            "type": "integer",
            "description": "Optional: Maximum athlete age in years (inclusive)"
        },
        "nationality": {
            "type": "string",
            "description": "Optional: Country code (ISO 3166-1 alpha-2) or nationality name to filter by"
        },
        "team": {
            "type": "string",
            "description": "Optional: Team name or club affiliation to search within"
        },
        "active_only": {
            "type": "boolean",
            "description": "Optional: If True, only search currently active athletes (retired athletes excluded)",
            "default": False
        },
        "search_query": {
            "type": "string",
            "description": "Optional: A free-text search term to match against athlete name, biography, or known achievements"
        }
    },
    "required": [
        "sport"
    ]
},
}
