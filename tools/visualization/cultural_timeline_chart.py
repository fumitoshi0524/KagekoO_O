"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    import random
    try:
        data = json.loads(payload)
        domain = data.get('domain')
        start_year = data.get('start_year')
        end_year = data.get('end_year')
        region = data.get('region', '')
        max_events = data.get('max_events', 20)
        if not all([domain, start_year, end_year]):
            return 'error: missing required parameters domain, start_year, end_year'
        if start_year > end_year:
            return 'error: start_year must be <= end_year'
        if max_events < 1 or max_events > 100:
            return 'error: max_events must be between 1 and 100'
        # Simulate retrieval of cultural events (in real implementation, this would query a cultural database)
        events_pool = {
            'art': [
                {'year': 1907, 'title': 'Les Demoiselles d\'Avignon', 'description': 'Picasso co-founds Cubism with this painting'},
                {'year': 1917, 'title': 'Fountain', 'description': 'Duchamp challenges art conventions with a readymade'},
                {'year': 1929, 'title': 'The Persistence of Memory', 'description': 'Dalí\'s surrealist masterpiece'},
                {'year': 1937, 'title': 'Guernica', 'description': 'Picasso\'s anti-war mural'},
                {'year': 1952, 'title': 'The Oxbow', 'description': 'Abstract expressionism emerges'},
                {'year': 1962, 'title': 'Campbell\'s Soup Cans', 'description': 'Warhol launches Pop Art'}
            ],
            'literature': [
                {'year': 1922, 'title': 'Ulysses', 'description': 'Joyce revolutionizes the novel'},
                {'year': 1925, 'title': 'The Great Gatsby', 'description': 'Fitzgerald captures the Jazz Age'},
                {'year': 1932, 'title': 'Brave New World', 'description': 'Huxley\'s dystopian vision'},
                {'year': 1949, 'title': '1984', 'description': 'Orwell\'s warning about totalitarianism'},
                {'year': 1951, 'title': 'The Catcher in the Rye', 'description': 'Salinger\'s coming-of-age classic'},
                {'year': 1969, 'title': 'Slaughterhouse-Five', 'description': 'Vonnegut\'s anti-war novel'}
            ],
            'music': [
                {'year': 1920, 'title': 'Birth of Jazz', 'description': 'Jazz emerges from New Orleans'},
                {'year': 1948, 'title': 'Invention of LP', 'description': 'Columbia introduces the 33 1/3 RPM record'},
                {'year': 1955, 'title': 'Rock and Roll', 'description': 'Bill Haley\'s Rock Around the Clock tops charts'},
                {'year': 1964, 'title': 'British Invasion', 'description': 'The Beatles arrive in America'},
                {'year': 1977, 'title': 'Punk Explosion', 'description': 'Sex Pistols release Never Mind the Bollocks'},
                {'year': 1984, 'title': 'MTV Era', 'description': 'Michael Jackson\'s Thriller dominates video'}
            ],
            'history': [
                {'year': 1914, 'title': 'WWI Begins', 'description': 'Assassination of Archduke Franz Ferdinand'},
                {'year': 1917, 'title': 'Russian Revolution', 'description': 'Bolsheviks overthrow the Tsar'},
                {'year': 1929, 'title': 'Great Depression', 'description': 'Wall Street Crash triggers global economic crisis'},
                {'year': 1939, 'title': 'WWII Begins', 'description': 'Germany invades Poland'},
                {'year': 1945, 'title': 'UN Founded', 'description': 'United Nations established after WWII'},
                {'year': 1969, 'title': 'Moon Landing', 'description': 'Apollo 11 lands on the moon'}
            ],
            'general': [
                {'year': 1914, 'title': 'WWI Begins', 'description': 'Global conflict transforms culture'},
                {'year': 1922, 'title': 'Ulysses Published', 'description': 'Modernist masterpieces shift literary boundaries'},
                {'year': 1937, 'title': 'Guernica', 'description': 'Art becomes political weapon'},
                {'year': 1949, 'title': '1984 Published', 'description': 'Dystopian fiction gains prominence'},
                {'year': 1955, 'title': 'Rock and Roll', 'description': 'Cultural revolution through music'},
                {'year': 1969, 'title': 'Moon Landing', 'description': 'Global unity through exploration'}
            ]
        }
        pool = events_pool.get(domain, events_pool['general'])
        filtered = [e for e in pool if start_year <= e['year'] <= end_year]
        if region:
            filtered = [e for e in filtered if region.lower() in e['description'].lower() or region.lower() in e['title'].lower()]
        if not filtered:
            return json.dumps({'error': 'No events found for the given criteria'}, ensure_ascii=False)
        sorted_events = sorted(filtered, key=lambda x: x['year'])
        selected = sorted_events[:min(max_events, len(sorted_events))]
        result = []
        for i, event in enumerate(selected):
            entry = {
                'id': i + 1,
                'year': event['year'],
                'title': event['title'],
                'description': event['description'],
                'position': i + 1,
                'total_events': len(selected)
            }
            result.append(entry)
        output = {
            'domain': domain,
            'start_year': start_year,
            'end_year': end_year,
            'region': region if region else 'global',
            'total_events': len(result),
            'timeline': result
        }
        return json.dumps(output, ensure_ascii=False, indent=2)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "cultural_timeline_chart",
    "description": "Generate a chronological timeline visualization of cultural events, artistic movements, literary periods, or historical milestones within a specific cultural domain and date range.",
    "category": "visualization",
    "domain": "culture",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "domain": {
            "type": "string",
            "description": "Cultural domain to visualize (art, literature, music, history, general).",
            "enum": [
                "art",
                "literature",
                "music",
                "history",
                "general"
            ],
            "examples": [
                "art",
                "literature"
            ]
        },
        "start_year": {
            "type": "integer",
            "description": "Start year for the timeline (e.g., 1900).",
            "examples": [
                1900,
                1800
            ]
        },
        "end_year": {
            "type": "integer",
            "description": "End year for the timeline (e.g., 2000).",
            "examples": [
                2000,
                2025
            ]
        },
        "region": {
            "type": "string",
            "description": "Optional: Filter events by region or culture (e.g., 'Europe', 'Asia', 'Western'). Leave empty for global.",
            "examples": [
                "Europe",
                "Renaissance Italy"
            ]
        },
        "max_events": {
            "type": "integer",
            "description": "Optional: Maximum number of events to include in the timeline (1-100). Defaults to 20.",
            "examples": [
                15
            ]
        }
    },
    "required": [
        "domain",
        "start_year",
        "end_year"
    ]
},
}
