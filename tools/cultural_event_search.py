"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    from datetime import datetime
    try:
        data = json.loads(payload)
        query = data.get('query', '').strip()
        if not query:
            return json.dumps({'error': 'query is required'}, ensure_ascii=False)
        location = data.get('location', '').strip()
        category = data.get('category', 'all')
        start_date = data.get('start_date', '')
        end_date = data.get('end_date', '')
        max_results = min(data.get('max_results', 10), 50)
        if start_date:
            try:
                datetime.strptime(start_date, '%Y-%m-%d')
            except ValueError:
                return json.dumps({'error': 'start_date must be in YYYY-MM-DD format'}, ensure_ascii=False)
        if end_date:
            try:
                datetime.strptime(end_date, '%Y-%m-%d')
            except ValueError:
                return json.dumps({'error': 'end_date must be in YYYY-MM-DD format'}, ensure_ascii=False)
        if max_results < 1 or max_results > 50:
            return json.dumps({'error': 'max_results must be between 1 and 50'}, ensure_ascii=False)
        events = []
        if 'impressionism' in query.lower():
            events = [
                {
                    'title': 'Impressionism: A New Dawn',
                    'date': '2025-06-15',
                    'venue': 'Musée d\'Orsay, Paris',
                    'category': 'exhibition',
                    'description': 'Major exhibition featuring works by Monet, Renoir, and Degas.'
                },
                {
                    'title': 'Monet\'s Garden in Giverny',
                    'date': '2025-07-01',
                    'venue': 'Giverny Gardens',
                    'category': 'exhibition',
                    'description': 'Outdoor exhibition of Monet\'s water lilies and garden paintings.'
                }
            ]
        elif 'beethoven' in query.lower():
            events = [
                {
                    'title': 'Beethoven Symphony No. 9',
                    'date': '2025-05-10',
                    'venue': 'Berlin Philharmonic',
                    'category': 'concert',
                    'description': 'Performance of Beethoven\'s Ninth Symphony featuring full orchestra and choir.'
                }
            ]
        else:
            events = [
                {
                    'title': f'{category.title()} Event: {query.title()}',
                    'date': '2025-08-01',
                    'venue': location if location else 'TBD',
                    'category': category,
                    'description': f'Description for {query} in {category} category.'
                }
            ]
        if start_date:
            events = [e for e in events if e['date'] >= start_date]
        if end_date:
            events = [e for e in events if e['date'] <= end_date]
        if location:
            events = [e for e in events if location.lower() in e['venue'].lower()]
        if category and category != 'all':
            events = [e for e in events if e['category'] == category]
        events = events[:max_results]
        result = {
            'query': query,
            'count': len(events),
            'events': events
        }
        return json.dumps(result, ensure_ascii=False)
    except json.JSONDecodeError:
        return json.dumps({'error': 'Invalid JSON payload'}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "cultural_event_search",
    "description": "Search for cultural events (exhibitions, concerts, theater, festivals) by keywords, location, date range, and category, returning a list of events with title, date, venue, and description.",
    "category": "search",
    "domain": "culture",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Free-text search terms (e.g., event name, artist, theme)"
        },
        "location": {
            "type": "string",
            "description": "City or region to filter events (e.g., 'Paris', 'New York')"
        },
        "category": {
            "type": "string",
            "description": "Filter by event category",
            "enum": [
                "exhibition",
                "concert",
                "theatre",
                "festival",
                "lecture",
                "film",
                "literature",
                "all"
            ]
        },
        "start_date": {
            "type": "string",
            "description": "Start date for date range filter (format: YYYY-MM-DD)"
        },
        "end_date": {
            "type": "string",
            "description": "End date for date range filter (format: YYYY-MM-DD)"
        },
        "max_results": {
            "type": "integer",
            "description": "Optional: maximum number of results to return (default: 10, max: 50)",
            "minimum": 1,
            "maximum": 50,
            "default": 10
        }
    },
    "required": [
        "query"
    ]
},
}
