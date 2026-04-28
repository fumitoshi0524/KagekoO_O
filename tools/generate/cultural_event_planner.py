"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a personalized cultural event itinerary."""
    import json
    try:
        data = json.loads(payload)
        city = data.get('city')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        interests = data.get('interests')
        max_per_day = data.get('max_events_per_day', 3)
        
        if not city or not start_date or not end_date or not interests:
            return json.dumps({'error': 'Missing required parameters: city, start_date, end_date, interests'})
        
        # Simulated event database based on city and interests
        event_db = {
            'Paris': {
                'art_exhibition': [
                    {'name': 'Impressionists at Musée d\'Orsay', 'venue': 'Musée d\'Orsay', 'time': '10:00 AM', 'description': 'Masterpieces by Monet, Renoir, and Degas.'},
                    {'name': 'Modern Art at Centre Pompidou', 'venue': 'Centre Pompidou', 'time': '11:00 AM', 'description': 'Contemporary works from global artists.'}
                ],
                'theater': [
                    {'name': 'Le Malade Imaginaire at Comédie-Française', 'venue': 'Comédie-Française', 'time': '8:00 PM', 'description': 'Molière\'s classic comedy performed by the national theater.'},
                    {'name': 'West Side Story at Théâtre du Châtelet', 'venue': 'Théâtre du Châtelet', 'time': '7:30 PM', 'description': 'A modern musical retelling of Romeo and Juliet.'}
                ],
                'music_festival': [
                    {'name': 'Fête de la Musique', 'venue': 'Various locations across Paris', 'time': '6:00 PM', 'description': 'Citywide free music festival with genres from classical to electronic.'}
                ],
                'literary_reading': [
                    {'name': 'Shakespeare & Company Reading Series', 'venue': 'Shakespeare & Company Bookstore', 'time': '7:00 PM', 'description': 'Readings by emerging authors and poets.'}
                ],
                'dance_performance': [
                    {'name': 'Ballet at Palais Garnier', 'venue': 'Palais Garnier', 'time': '8:00 PM', 'description': 'Classical ballet performance by the Paris Opera Ballet.'}
                ],
                'historical_tour': [
                    {'name': 'Walking Tour of Montmartre', 'venue': 'Montmartre district', 'time': '10:00 AM', 'description': 'Explore the historic artist quarter and Sacré-Cœur.'}
                ]
            },
            'New York': {
                'art_exhibition': [
                    {'name': 'Metropolitan Museum of Art: Modern Wing', 'venue': 'The Met', 'time': '10:00 AM', 'description': 'Extensive collection of modern and contemporary art.'},
                    {'name': 'Whitney Biennial', 'venue': 'Whitney Museum of American Art', 'time': '11:00 AM', 'description': 'Survey of contemporary American art.'}
                ],
                'theater': [
                    {'name': 'Hamilton on Broadway', 'venue': 'Richard Rodgers Theatre', 'time': '8:00 PM', 'description': 'Blockbuster musical about Alexander Hamilton.'},
                    {'name': 'The Lion King at Minskoff Theatre', 'venue': 'Minskoff Theatre', 'time': '7:30 PM', 'description': 'Disney\'s beloved musical adapted for stage.'}
                ],
                'music_festival': [
                    {'name': 'SummerStage in Central Park', 'venue': 'Central Park', 'time': '3:00 PM', 'description': 'Outdoor music festival featuring diverse genres.'}
                ],
                'literary_reading': [
                    {'name': 'Poetry Reading at The Strand', 'venue': 'The Strand Bookstore', 'time': '7:00 PM', 'description': 'Readings by established and emerging poets.'}
                ],
                'dance_performance': [
                    {'name': 'NYC Ballet', 'venue': 'Lincoln Center', 'time': '8:00 PM', 'description': 'Performance by the New York City Ballet.'}
                ],
                'historical_tour': [
                    {'name': 'Lower East Side Tenement Museum Tour', 'venue': 'Tenement Museum', 'time': '10:00 AM', 'description': 'Explore the history of immigrant life in NYC.'}
                ]
            }
        }
        
        city_events = event_db.get(city)
        if not city_events:
            return json.dumps({'error': f'No data available for city: {city}'})
        
        # Generate itinerary for each day in range
        from datetime import datetime, timedelta
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            return json.dumps({'error': 'Invalid date format. Use YYYY-MM-DD.'})
        
        if start > end:
            return json.dumps({'error': 'Start date must be before end date.'})
        
        itinerary = {}
        current_date = start
        while current_date <= end:
            date_str = current_date.strftime('%Y-%m-%d')
            day_events = []
            for interest in interests:
                events = city_events.get(interest, [])
                for event in events[:max_per_day]:
                    day_events.append(event)
            # Shuffle to add variety each day, then limit to max_per_day
            import random
            random.shuffle(day_events)
            itinerary[date_str] = day_events[:max_per_day]
            current_date += timedelta(days=1)
        
        result = {
            'city': city,
            'start_date': start_date,
            'end_date': end_date,
            'interests': interests,
            'itinerary': itinerary
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)})


TOOL_SPEC = {
    "name": "cultural_event_planner",
    "description": "Generate a personalized cultural event itinerary based on user preferences for city, date range, and interests (e.g., art exhibitions, theater, music festivals, literary readings). Returns a structured schedule with event names, venues, times, and brief descriptions to help users plan their cultural outings.",
    "category": "generate",
    "domain": "culture",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "city": {
            "type": "string",
            "description": "Name of the city for which to generate cultural event recommendations (e.g., Paris, New York, Tokyo).",
            "examples": [
                "Paris"
            ]
        },
        "start_date": {
            "type": "string",
            "description": "Start date for the event search in YYYY-MM-DD format.",
            "examples": [
                "2025-06-01"
            ]
        },
        "end_date": {
            "type": "string",
            "description": "End date for the event search in YYYY-MM-DD format.",
            "examples": [
                "2025-06-07"
            ]
        },
        "interests": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [
                    "art_exhibition",
                    "theater",
                    "music_festival",
                    "literary_reading",
                    "dance_performance",
                    "historical_tour"
                ]
            },
            "description": "List of cultural interest categories to include in the itinerary.",
            "examples": [
                [
                    "art_exhibition",
                    "theater"
                ]
            ]
        },
        "max_events_per_day": {
            "type": "integer",
            "description": "Optional: Maximum number of events to schedule per day (default 3).",
            "minimum": 1,
            "maximum": 10,
            "examples": [
                3
            ]
        }
    },
    "required": [
        "city",
        "start_date",
        "end_date",
        "interests"
    ]
},
}
