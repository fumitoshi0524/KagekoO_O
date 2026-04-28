"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Search for sports teams by name, sport, or league and retrieve team details including location, stadium, and key players."""
    import json
    try:
        data = json.loads(payload)
        team_name = data.get('team_name', '').strip().lower()
        if not team_name:
            return json.dumps({'error': 'team_name is required and cannot be empty'}, ensure_ascii=False)
        sport_filter = data.get('sport', '').strip().lower() if data.get('sport') else None
        league_filter = data.get('league', '').strip().lower() if data.get('league') else None
        
        # Simulated in-memory sports team database
        teams_db = [
            {"name": "Los Angeles Lakers", "sport": "basketball", "league": "NBA", "location": "Los Angeles, CA", "stadium": "Staples Center", "players": ["LeBron James", "Anthony Davis", "Russell Westbrook"]},
            {"name": "New York Yankees", "sport": "baseball", "league": "MLB", "location": "New York, NY", "stadium": "Yankee Stadium", "players": ["Aaron Judge", "Gerrit Cole", "Giancarlo Stanton"]},
            {"name": "Manchester United", "sport": "soccer", "league": "Premier League", "location": "Manchester, England", "stadium": "Old Trafford", "players": ["Cristiano Ronaldo", "Marcus Rashford", "Bruno Fernandes"]},
            {"name": "Green Bay Packers", "sport": "football", "league": "NFL", "location": "Green Bay, WI", "stadium": "Lambeau Field", "players": ["Aaron Rodgers", "Davante Adams", "Jaire Alexander"]},
            {"name": "Golden State Warriors", "sport": "basketball", "league": "NBA", "location": "San Francisco, CA", "stadium": "Chase Center", "players": ["Stephen Curry", "Draymond Green", "Klay Thompson"]},
            {"name": "FC Barcelona", "sport": "soccer", "league": "La Liga", "location": "Barcelona, Spain", "stadium": "Camp Nou", "players": ["Lionel Messi", "Sergio Busquets", "Gerard Pique"]},
            {"name": "Chicago Bears", "sport": "football", "league": "NFL", "location": "Chicago, IL", "stadium": "Soldier Field", "players": ["Justin Fields", "David Montgomery", "Khalil Mack"]},
            {"name": "Boston Celtics", "sport": "basketball", "league": "NBA", "location": "Boston, MA", "stadium": "TD Garden", "players": ["Jayson Tatum", "Jaylen Brown", "Marcus Smart"]}
        ]
        
        # Filter teams based on criteria (case-insensitive)
        results = []
        for team in teams_db:
            if team_name in team['name'].lower():
                if sport_filter and sport_filter != team['sport'].lower():
                    continue
                if league_filter and league_filter != team['league'].lower():
                    continue
                results.append(team)
        
        if not results:
            return json.dumps({'teams': [], 'message': 'No teams found matching the search criteria.'}, ensure_ascii=False)
        
        return json.dumps({'teams': results}, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "sports_team_search",
    "description": "Search for sports teams by name, sport, or league and retrieve team details including location, stadium, and key players.",
    "category": "search",
    "domain": "sports",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "team_name": {
            "type": "string",
            "description": "Full or partial name of the sports team to search for (e.g., 'Lakers')."
        },
        "sport": {
            "type": "string",
            "description": "Optional: Filter by sport type (e.g., 'basketball', 'football', 'soccer'). If not provided, all sports are searched."
        },
        "league": {
            "type": "string",
            "description": "Optional: Filter by league name (e.g., 'NBA', 'NFL', 'Premier League'). If not provided, all leagues are searched."
        }
    },
    "required": [
        "team_name"
    ]
},
}
