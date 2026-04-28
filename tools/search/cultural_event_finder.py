"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Search for cultural events near a location within a date range."""
    import json
    from datetime import datetime, date
    import math

    try:
        data = json.loads(payload)
        location = data.get('location')
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        category_filter = data.get('category_filter', 'all')
        radius_km = data.get('radius_km', 50)
        max_results = data.get('max_results', 20)

        if not location or not start_date_str or not end_date_str:
            return json.dumps({'error': 'Missing required parameters: location, start_date, end_date'}, ensure_ascii=False)

        # Simulate event database query (in production would call actual API)
        events = []
        sample_events = [
            {'name': 'Summer Art Exhibition', 'category': 'art', 'venue': 'Louvre Museum', 'date': '2025-07-15', 'price': 25, 'description': 'Contemporary art exhibition featuring international artists'},
            {'name': 'Jazz in the Park', 'category': 'music', 'venue': 'Central Park Amphitheater', 'date': '2025-07-20', 'price': 0, 'description': 'Free outdoor jazz concert series'},
            {'name': 'Shakespeare in the Garden', 'category': 'theatre', 'venue': 'Botanical Gardens', 'date': '2025-07-22', 'price': 35, 'description': 'Outdoor theatre performance of A Midsummer Night\'s Dream'},
            {'name': 'Folk Dance Festival', 'category': 'dance', 'venue': 'City Square', 'date': '2025-07-28', 'price': 0, 'description': 'Annual folk dance celebration with workshops'},
            {'name': 'Book Fair & Author Talks', 'category': 'literature', 'venue': 'Convention Center', 'date': '2025-07-10', 'price': 10, 'description': 'Book fair with author signings and panel discussions'},
            {'name': 'International Film Festival', 'category': 'film', 'venue': 'Grand Cinema', 'date': '2025-07-18', 'price': 15, 'description': 'Showcase of independent films from around the world'},
            {'name': 'Heritage Walking Tour', 'category': 'heritage', 'venue': 'Old Town District', 'date': '2025-07-05', 'price': 20, 'description': 'Guided tour of historic landmarks'},
            {'name': 'Ceramics Workshop', 'category': 'workshop', 'venue': 'Art Center Studio', 'date': '2025-07-12', 'price': 45, 'description': 'Hands-on pottery making workshop for beginners'},
            {'name': 'Summer Food & Wine Festival', 'category': 'festival', 'venue': 'Waterfront Park', 'date': '2025-07-25', 'price': 50, 'description': 'Culinary festival with local food vendors and wine tastings'},
            {'name': 'Photography Masterclass', 'category': 'workshop', 'venue': 'Gallery Space', 'date': '2025-07-08', 'price': 60, 'description': 'Professional photography techniques workshop'}
        ]

        # Filter by date range and category
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

        for event in sample_events:
            event_date = datetime.strptime(event['date'], '%Y-%m-%d').date()
            if start_date <= event_date <= end_date:
                if category_filter == 'all' or category_filter == event['category']:
                    # Simulate distance calculation (within radius)
                    events.append({
                        'name': event['name'],
                        'category': event['category'],
                        'venue': event['venue'],
                        'date': event['date'],
                        'price': event['price'],
                        'description': event['description'],
                        'distance_km': round(15 + (hash(event['name']) % 30), 1),  # Simulated distance
                        'estimated': True
                    })
            if len(events) >= max_results:
                break

        # Sort by date
        events.sort(key=lambda x: x['date'])

        result = {
            'query': {
                'location': location,
                'date_range': f'{start_date_str} to {end_date_str}',
                'category': category_filter,
                'radius_km': radius_km,
                'max_results': max_results
            },
            'total_events': len(events),
            'events': events,
            'metadata': {
                'source': 'cultural_event_database',
                'timestamp': datetime.now().isoformat(),
                'disclaimer': 'Results are simulated for demonstration. Real implementation would connect to actual event databases.'
            }
        }

        return json.dumps(result, ensure_ascii=False, default=str)

    except json.JSONDecodeError:
        return json.dumps({'error': 'Invalid JSON payload'}, ensure_ascii=False)
    except KeyError as e:
        return json.dumps({'error': f'Missing required field: {str(e)}'}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': f'Processing error: {str(e)}'}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "cultural_event_finder",
    "description": "Search for cultural events (festivals, exhibitions, performances, workshops) near a location within a date range, returning a list of matching events with venue details, dates, and categories.",
    "category": "search",
    "domain": "culture",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "location": {
            "type": "string",
            "description": "Geographic location for the event search (city name, postal code, or coordinates as 'lat,lng')",
            "examples": [
                "Paris",
                "10001",
                "51.5074,-0.1278"
            ]
        },
        "start_date": {
            "type": "string",
            "format": "date",
            "description": "Start of the search date range in YYYY-MM-DD format",
            "examples": [
                "2025-07-01"
            ]
        },
        "end_date": {
            "type": "string",
            "format": "date",
            "description": "End of the search date range in YYYY-MM-DD format",
            "examples": [
                "2025-07-31"
            ]
        },
        "category_filter": {
            "type": "string",
            "enum": [
                "art",
                "music",
                "theatre",
                "dance",
                "literature",
                "film",
                "festival",
                "workshop",
                "heritage",
                "all"
            ],
            "description": "Optional: Filter by specific cultural category. Use 'all' or leave empty for all categories.",
            "examples": [
                "festival",
                "art"
            ]
        },
        "radius_km": {
            "type": "number",
            "minimum": 1,
            "maximum": 200,
            "description": "Optional: Search radius in kilometers from the specified location (default: 50)",
            "examples": [
                100
            ]
        },
        "max_results": {
            "type": "integer",
            "minimum": 1,
            "maximum": 100,
            "description": "Optional: Maximum number of events to return (default: 20)",
            "examples": [
                50
            ]
        }
    },
    "required": [
        "location",
        "start_date",
        "end_date"
    ]
},
}
