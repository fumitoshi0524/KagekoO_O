"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Search for athlete performance records by name, sport, or team."""
    import json
    import re
    from datetime import datetime

    try:
        data = json.loads(payload)
        
        # Validate required inputs
        if 'name' not in data or not data['name']:
            return json.dumps({"error": "'name' is required and must be non-empty"})
        
        search_name = data['name'].lower().strip()
        sport_filter = data.get('sport', '').lower().strip() if data.get('sport') else None
        team_filter = data.get('team', '').lower().strip() if data.get('team') else None
        min_ranking = data.get('min_ranking')
        max_results = min(data.get('max_results', 10), 50)
        
        # Simulated athlete database (in production, this would query a real database)
        athlete_database = [
            {"name": "LeBron James", "sport": "basketball", "team": "Lakers", "ranking": 5, "age": 39, "personal_best": "38.4 PPG (2022-23 season)", "career_stats": {"points": 40474, "assists": 11009, "rebounds": 11185}, "achievements": "4x NBA Champion, 4x Finals MVP"},
            {"name": "Lionel Messi", "sport": "soccer", "team": "Inter Miami", "ranking": 1, "age": 37, "personal_best": "91 goals in a calendar year (2012)", "career_stats": {"goals": 838, "assists": 386, "appearances": 1058}, "achievements": "8x Ballon d'Or winner, World Cup champion"},
            {"name": "Cristiano Ronaldo", "sport": "soccer", "team": "Al Nassr", "ranking": 3, "age": 39, "personal_best": "44 goals in 2014-15 season", "career_stats": {"goals": 873, "assists": 256, "appearances": 1192}, "achievements": "5x Ballon d'Or winner, Euro 2016 champion"},
            {"name": "Usain Bolt", "sport": "athletics", "team": "Jamaica", "ranking": 1, "age": 38, "personal_best": "9.58s (100m), 19.19s (200m)", "career_stats": {"olympic_golds": 8, "world_championship_golds": 11}, "achievements": "Fastest man in history, 8x Olympic gold medalist"},
            {"name": "Serena Williams", "sport": "tennis", "team": "USA", "ranking": 2, "age": 43, "personal_best": "World No. 1 for 319 weeks", "career_stats": {"grand_slam_titles": 23, "wins": 858, "losses": 156}, "achievements": "23 Grand Slam singles titles, 4 Olympic gold medals"},
            {"name": "Tom Brady", "sport": "football", "team": "Patriots", "ranking": 1, "age": 47, "personal_best": "5,316 passing yards (2011 season)", "career_stats": {"touchdowns": 649, "passing_yards": 89514, "super_bowl_wins": 7}, "achievements": "7x Super Bowl champion, 5x Super Bowl MVP"},
            {"name": "Megan Rapinoe", "sport": "soccer", "team": "OL Reign", "ranking": 4, "age": 39, "personal_best": "6 goals in 2019 World Cup", "career_stats": {"goals": 63, "assists": 73, "appearances": 203}, "achievements": "World Cup champion (2015, 2019), Ballon d'Or Féminin (2019)"},
            {"name": "Kobe Bryant", "sport": "basketball", "team": "Lakers", "ranking": 10, "age": 41, "personal_best": "81 points in a single game (2006)", "career_stats": {"points": 33643, "assists": 6306, "rebounds": 7047}, "achievements": "5x NBA Champion, 2x Finals MVP, 2008 MVP"},
            {"name": "Michael Jordan", "sport": "basketball", "team": "Bulls", "ranking": 1, "age": 61, "personal_best": "37.1 PPG (1986-87 season)", "career_stats": {"points": 32292, "assists": 5633, "rebounds": 6672}, "achievements": "6x NBA Champion, 6x Finals MVP, 5x MVP"},
            {"name": "Simone Biles", "sport": "gymnastics", "team": "USA", "ranking": 1, "age": 27, "personal_best": "5 world all-around titles", "career_stats": {"olympic_medals": 7, "world_championship_medals": 25}, "achievements": "Most decorated gymnast in history, 4 Olympic golds"},
            {"name": "Katie Ledecky", "sport": "swimming", "team": "USA", "ranking": 1, "age": 27, "personal_best": "8:04.79 (800m freestyle WR)", "career_stats": {"olympic_golds": 7, "world_records": 14}, "achievements": "7x Olympic gold medalist, 21 world championship golds"},
            {"name": "Roger Federer", "sport": "tennis", "team": "Switzerland", "ranking": 3, "age": 43, "personal_best": "World No. 1 for 310 weeks", "career_stats": {"grand_slam_titles": 20, "wins": 1251, "losses": 275}, "achievements": "20 Grand Slam singles titles, 8 Wimbledon titles"},
            {"name": "Shohei Ohtani", "sport": "baseball", "team": "Dodgers", "ranking": 1, "age": 30, "personal_best": "44 HR, 10 wins as pitcher (2021)", "career_stats": {"home_runs": 171, "batting_avg": 0.274, "pitch_strikeouts": 608}, "achievements": "2023 AL MVP, 2x unanimous MVP"},
            {"name": "Lewis Hamilton", "sport": "motorsport", "team": "Mercedes", "ranking": 2, "age": 39, "personal_best": "7 F1 World Championships", "career_stats": {"race_wins": 103, "pole_positions": 104, "podiums": 197}, "achievements": "7x F1 World Champion, 103 race wins (record)"},
        ]
        
        results = []
        for athlete in athlete_database:
            # Name matching (partial, case-insensitive)
            if search_name not in athlete["name"].lower():
                continue
            
            # Sport filter
            if sport_filter and sport_filter != athlete["sport"].lower():
                continue
            
            # Team filter
            if team_filter and team_filter != athlete["team"].lower():
                continue
            
            # Ranking filter
            if min_ranking is not None and athlete["ranking"] > min_ranking:
                continue
            
            results.append(athlete)
            if len(results) >= max_results:
                break
        
        if not results:
            return json.dumps({
                "query": {"name": data["name"], "sport": data.get("sport"), "team": data.get("team")},
                "count": 0,
                "results": [],
                "message": "No athletes found matching your search criteria."
            }, ensure_ascii=False)
        
        # Sort by ranking for relevance
        results.sort(key=lambda x: x["ranking"])
        
        return json.dumps({
            "query": {"name": data["name"], "sport": data.get("sport"), "team": data.get("team")},
            "count": len(results),
            "results": results,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }, ensure_ascii=False)
        
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON payload: {str(e)}"})
    except Exception as e:
        return json.dumps({"error": f"Unexpected error: {str(e)}"})


TOOL_SPEC = {
    "name": "find_athlete_records",
    "description": "Search for athlete performance records by name, sport, or team, returning a list of matching athletes with their personal bests, career statistics, and recent achievements.",
    "category": "search",
    "domain": "sports",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "name": {
            "type": "string",
            "description": "Full or partial name of the athlete to search for (case-insensitive, supports wildcards)"
        },
        "sport": {
            "type": "string",
            "description": "Optional: Filter by sport type (e.g., basketball, soccer, tennis, swimming, athletics)"
        },
        "team": {
            "type": "string",
            "description": "Optional: Filter by team name or abbreviation (e.g., Lakers, Man Utd, NYY)"
        },
        "min_ranking": {
            "type": "integer",
            "description": "Optional: Minimum world ranking position (1-2000) for competitive athletes"
        },
        "max_results": {
            "type": "integer",
            "description": "Optional: Maximum number of athlete records to return (default 10, max 50)"
        }
    },
    "required": [
        "name"
    ]
},
}
