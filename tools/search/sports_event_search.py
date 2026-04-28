"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Search for sports events by sport type, date range, location, or team/player name, returning event name, date, venue, participating teams/athletes, and ticket availability status."""
    import json
    from datetime import datetime, timedelta
    
    try:
        data = json.loads(payload)
        
        # Validate required fields
        if 'sport' not in data:
            return json.dumps({"error": "Missing required field: sport"}, ensure_ascii=False)
        
        sport = data['sport'].lower()
        valid_sports = ["basketball", "soccer", "tennis", "baseball", "football", "hockey", "golf", "boxing", "mma", "cricket", "rugby", "volleyball", "swimming", "track_and_field"]
        if sport not in valid_sports:
            return json.dumps({"error": f"Invalid sport: {sport}. Valid options: {', '.join(valid_sports)}"}, ensure_ascii=False)
        
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        location = data.get('location', '').strip()
        team_or_player = data.get('team_or_player', '').strip()
        max_results = min(data.get('max_results', 20), 100)
        status_filter = data.get('status_filter', 'upcoming')
        
        # Validate dates if provided
        if start_date:
            try:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            except ValueError:
                return json.dumps({"error": "Invalid start_date format. Use YYYY-MM-DD."}, ensure_ascii=False)
        else:
            start_dt = datetime.now()
        
        if end_date:
            try:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            except ValueError:
                return json.dumps({"error": "Invalid end_date format. Use YYYY-MM-DD."}, ensure_ascii=False)
        else:
            end_dt = start_dt + timedelta(days=30)
        
        if end_dt < start_dt:
            return json.dumps({"error": "end_date must be after start_date."}, ensure_ascii=False)
        
        # Simulated sports event database
        # In production, this would query a real API or database
        events_database = [
            {
                "event_name": "NBA Finals 2025 Game 1",
                "sport": "basketball",
                "date": "2025-06-05",
                "venue": "TD Garden, Boston, MA",
                "participants": ["Boston Celtics", "Los Angeles Lakers"],
                "status": "upcoming",
                "ticket_available": True,
                "ticket_url": "https://tickets.example.com/nba-finals-2025-g1"
            },
            {
                "event_name": "Wimbledon 2025 - Men's Final",
                "sport": "tennis",
                "date": "2025-07-13",
                "venue": "All England Club, London, UK",
                "participants": ["Carlos Alcaraz", "Novak Djokovic"],
                "status": "upcoming",
                "ticket_available": False,
                "ticket_url": None
            },
            {
                "event_name": "Premier League: Manchester United vs Liverpool",
                "sport": "soccer",
                "date": "2025-03-15",
                "venue": "Old Trafford, Manchester, UK",
                "participants": ["Manchester United", "Liverpool FC"],
                "status": "upcoming",
                "ticket_available": True,
                "ticket_url": "https://tickets.example.com/manu-vs-liverpool"
            },
            {
                "event_name": "Super Bowl LX",
                "sport": "football",
                "date": "2026-02-08",
                "venue": "Levi's Stadium, Santa Clara, CA",
                "participants": ["TBD vs TBD"],
                "status": "upcoming",
                "ticket_available": True,
                "ticket_url": "https://tickets.example.com/super-bowl-lx"
            },
            {
                "event_name": "2025 MLB All-Star Game",
                "sport": "baseball",
                "date": "2025-07-15",
                "venue": "Dodger Stadium, Los Angeles, CA",
                "participants": ["American League All-Stars", "National League All-Stars"],
                "status": "upcoming",
                "ticket_available": True,
                "ticket_url": "https://tickets.example.com/mlb-all-star-2025"
            },
            {
                "event_name": "Stanley Cup Finals 2025 Game 7",
                "sport": "hockey",
                "date": "2025-06-20",
                "venue": "Bell Centre, Montreal, Canada",
                "participants": ["Montreal Canadiens", "Colorado Avalanche"],
                "status": "upcoming",
                "ticket_available": True,
                "ticket_url": "https://tickets.example.com/stanley-cup-2025-g7"
            },
            {
                "event_name": "The Masters 2025 - Final Round",
                "sport": "golf",
                "date": "2025-04-13",
                "venue": "Augusta National Golf Club, Augusta, GA",
                "participants": ["Professional Golfers - Final Field TBD"],
                "status": "upcoming",
                "ticket_available": False,
                "ticket_url": None
            },
            {
                "event_name": "UFC 315: Adesanya vs Pereira 3",
                "sport": "mma",
                "date": "2025-04-19",
                "venue": "T-Mobile Arena, Las Vegas, NV",
                "participants": ["Israel Adesanya", "Alex Pereira"],
                "status": "upcoming",
                "ticket_available": True,
                "ticket_url": "https://tickets.example.com/ufc-315"
            },
            {
                "event_name": "2025 Cricket World Cup - Final",
                "sport": "cricket",
                "date": "2025-11-16",
                "venue": "Lord's Cricket Ground, London, UK",
                "participants": ["India", "Australia"],
                "status": "upcoming",
                "ticket_available": True,
                "ticket_url": "https://tickets.example.com/cricket-wc-2025"
            },
            {
                "event_name": "Olympic Games Los Angeles 2028 - Opening Ceremony",
                "sport": "track_and_field",
                "date": "2028-07-14",
                "venue": "Los Angeles Memorial Coliseum, Los Angeles, CA",
                "participants": ["International Athletes - 200+ Nations"],
                "status": "upcoming",
                "ticket_available": True,
                "ticket_url": "https://tickets.example.com/la2028-opening"
            }
        ]
        
        # Filter events based on criteria
        filtered_events = []
        
        for event in events_database:
            # Filter by sport
            if event['sport'] != sport:
                continue
            
            # Filter by date range
            try:
                event_date = datetime.strptime(event['date'], '%Y-%m-%d')
            except ValueError:
                continue
            
            if event_date < start_dt or event_date > end_dt:
                continue
            
            # Filter by status
            if status_filter and event['status'] != status_filter:
                continue
            
            # Filter by location (case-insensitive partial match)
            if location:
                location_lower = location.lower()
                venue_lower = event['venue'].lower()
                if location_lower not in venue_lower and location_lower not in [p.lower() for p in event['participants']]:
                    continue
            
            # Filter by team or player (case-insensitive partial match)
            if team_or_player:
                search_term = team_or_player.lower()
                match_found = False
                for participant in event['participants']:
                    if search_term in participant.lower():
                        match_found = True
                        break
                if not match_found:
                    continue
            
            filtered_events.append(event)
        
        # Sort by date (earliest first)
        filtered_events.sort(key=lambda e: e['date'])
        
        # Apply max_results limit
        filtered_events = filtered_events[:max_results]
        
        # Prepare result
        result = {
            "query": {
                "sport": sport,
                "start_date": start_dt.strftime('%Y-%m-%d'),
                "end_date": end_dt.strftime('%Y-%m-%d'),
                "location": location if location else None,
                "team_or_player": team_or_player if team_or_player else None,
                "status_filter": status_filter if status_filter else None
            },
            "total_results": len(filtered_events),
            "results": filtered_events
        }
        
        return json.dumps(result, ensure_ascii=False)
        
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON payload"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"An unexpected error occurred: {str(e)}"}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "sports_event_search",
    "description": "Search for sports events by sport type, date range, location, or team/player name, returning event name, date, venue, participating teams/athletes, and ticket availability status.",
    "category": "search",
    "domain": "sports",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "sport": {
            "type": "string",
            "description": "Type of sport to filter by (e.g., basketball, soccer, tennis, baseball)",
            "enum": [
                "basketball",
                "soccer",
                "tennis",
                "baseball",
                "football",
                "hockey",
                "golf",
                "boxing",
                "mma",
                "cricket",
                "rugby",
                "volleyball",
                "swimming",
                "track_and_field"
            ]
        },
        "start_date": {
            "type": "string",
            "description": "Start date for event search range in YYYY-MM-DD format. Events on or after this date will be included.",
            "pattern": "^\\d{4}-\\d{2}-\\d{2}$"
        },
        "end_date": {
            "type": "string",
            "description": "End date for event search range in YYYY-MM-DD format. Events on or before this date will be included.",
            "pattern": "^\\d{4}-\\d{2}-\\d{2}$"
        },
        "location": {
            "type": "string",
            "description": "Optional: City, state, or venue name to filter events by geographic location (e.g., 'New York', 'Madison Square Garden', 'London'). Partial matches supported with minimum 2 characters."
        },
        "team_or_player": {
            "type": "string",
            "description": "Optional: Team or athlete name to search for events involving that team or player (e.g., 'Lakers', 'Serena Williams', 'Manchester United'). Partial matches supported."
        },
        "max_results": {
            "type": "integer",
            "description": "Optional: Maximum number of event results to return. Default is 20, maximum is 100.",
            "minimum": 1,
            "maximum": 100,
            "default": 20
        },
        "status_filter": {
            "type": "string",
            "description": "Optional: Filter events by current status. Leave empty for all statuses.",
            "enum": [
                "upcoming",
                "ongoing",
                "completed",
                "cancelled",
                "postponed"
            ],
            "default": "upcoming"
        }
    },
    "required": [
        "sport"
    ]
},
}
