"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        theme = data.get('theme')
        if not theme:
            return json.dumps({'error': 'Missing required parameter: theme'})
        region = data.get('region', 'global')
        start_year = data.get('start_year', 0)
        end_year = data.get('end_year', 2025)
        max_events = min(data.get('max_events', 20), 50)
        # Simulated database of cultural events (in a real tool, this would query a knowledge base)
        database = [
            {'date': '1401', 'event': 'Birth of Masaccio, pioneer of Renaissance painting', 'category': 'Art'},
            {'date': '1450', 'event': 'Johannes Gutenberg invents the printing press', 'category': 'Technology'},
            {'date': '1501', 'event': 'Michelangelo begins work on David', 'category': 'Art'},
            {'date': '1508', 'event': 'Raphael paints the Stanza della Segnatura in Vatican', 'category': 'Art'},
            {'date': '1517', 'event': 'Martin Luther posts 95 Theses, starting Reformation', 'category': 'History'},
            {'date': '1543', 'event': 'Copernicus publishes De revolutionibus orbium coelestium', 'category': 'Science'},
            {'date': '1564', 'event': 'Birth of William Shakespeare', 'category': 'Literature'},
            {'date': '1590', 'event': 'Shakespeare writes A Midsummer Night\'s Dream', 'category': 'Literature'},
            {'date': '1600', 'event': 'Giordano Bruno burned at stake for heresy', 'category': 'History'},
            {'date': '1603', 'event': 'Tokugawa Ieyasu establishes Edo period in Japan', 'category': 'History'},
            {'date': '1605', 'event': 'Publication of Don Quixote by Cervantes', 'category': 'Literature'},
            {'date': '1610', 'event': 'Galileo publishes Sidereus Nuncius', 'category': 'Science'},
            {'date': '1623', 'event': 'First Folio of Shakespeare\'s plays published', 'category': 'Literature'},
            {'date': '1632', 'event': 'Birth of Baruch Spinoza', 'category': 'Philosophy'},
            {'date': '1642', 'event': 'Birth of Isaac Newton', 'category': 'Science'},
            {'date': '1650', 'event': 'Descartes dies in Stockholm', 'category': 'Philosophy'},
            {'date': '1667', 'event': 'Milton publishes Paradise Lost', 'category': 'Literature'},
            {'date': '1687', 'event': 'Newton publishes Principia Mathematica', 'category': 'Science'},
            {'date': '1720', 'event': 'Bach composes Brandenburg Concertos', 'category': 'Music'},
            {'date': '1740', 'event': 'Vivaldi\'s Four Seasons published', 'category': 'Music'},
            {'date': '1750', 'event': 'Death of Johann Sebastian Bach', 'category': 'Music'},
            {'date': '1776', 'event': 'Declaration of Independence, USA', 'category': 'History'},
            {'date': '1789', 'event': 'French Revolution begins', 'category': 'History'},
            {'date': '1791', 'event': 'Mozart dies, leaving Requiem unfinished', 'category': 'Music'},
            {'date': '1804', 'event': 'Beethoven\'s Eroica Symphony premieres', 'category': 'Music'},
            {'date': '1818', 'event': 'Frankenstein published by Mary Shelley', 'category': 'Literature'},
            {'date': '1830', 'event': 'First railroad in US (Baltimore and Ohio)', 'category': 'Technology'},
            {'date': '1851', 'event': 'Great Exhibition in London', 'category': 'History'},
            {'date': '1859', 'event': 'Darwin publishes On the Origin of Species', 'category': 'Science'},
            {'date': '1865', 'event': 'Lincoln assassinated; Alice in Wonderland published', 'category': 'Literature'},
            {'date': '1875', 'event': 'First Kentucky Derby; Bizet\'s Carmen premieres', 'category': 'Sports'},
            {'date': '1900', 'event': 'Sigmund Freud publishes The Interpretation of Dreams', 'category': 'Psychology'},
            {'date': '1905', 'event': 'Einstein publishes special relativity', 'category': 'Science'},
            {'date': '1910', 'event': 'First public radio broadcast', 'category': 'Technology'},
            {'date': '1913', 'event': 'Russian Ballet premieres The Rite of Spring', 'category': 'Dance'},
            {'date': '1920', 'event': 'Jazz Age begins; first commercial radio station', 'category': 'Music'},
            {'date': '1925', 'event': 'Fitzgerald publishes The Great Gatsby', 'category': 'Literature'},
            {'date': '1936', 'event': 'Spanish Civil War begins; first TV broadcast by BBC', 'category': 'History'},
            {'date': '1940', 'event': 'Hemingway publishes For Whom the Bell Tolls', 'category': 'Literature'},
            {'date': '1950', 'event': 'Korean War starts; Charlie Chaplin\'s Limelight', 'category': 'History'},
            {'date': '1960', 'event': 'Cuban Revolution; first laser built', 'category': 'Science'},
            {'date': '1963', 'event': 'Martin Luther King\'s I Have a Dream speech', 'category': 'History'},
            {'date': '1969', 'event': 'Moon landing; Woodstock festival', 'category': 'Technology'},
            {'date': '1971', 'event': 'First email sent; Disney World opens', 'category': 'Technology'},
            {'date': '1980', 'event': 'CNN launches; Pac-Man released', 'category': 'Technology'},
            {'date': '1991', 'event': 'World Wide Web becomes public', 'category': 'Technology'},
            {'date': '2000', 'event': 'Millennium celebrations; first human genome draft', 'category': 'Science'},
            {'date': '2010', 'event': 'First iPad released; Haitian earthquake', 'category': 'Technology'},
            {'date': '2020', 'event': 'COVID-19 pandemic declared', 'category': 'Health'},
            {'date': '2023', 'event': 'ChatGPT gains widespread adoption', 'category': 'Technology'}
        ]
        # Filter by theme (case-insensitive substring match on event, category, or theme)
        filtered = [e for e in database if (theme.lower() in e['event'].lower() or theme.lower() in e['category'].lower())]
        # Filter by region if not global (in this simplified DB, region is not stored, so we simulate)
        if region.lower() != 'global':
            region_filtered = []
            for e in filtered:
                if region.lower() in e['event'].lower() or region.lower() in e['category'].lower():
                    region_filtered.append(e)
            filtered = region_filtered if region_filtered else filtered
        # Filter by year range
        filtered = [e for e in filtered if int(e['date'][:4]) >= start_year and int(e['date'][:4]) <= end_year]
        # Sort by date
        filtered.sort(key=lambda x: int(x['date'][:4]))
        # Limit events
        filtered = filtered[:max_events]
        if not filtered:
            return json.dumps({'timeline': [], 'message': 'No events found for the given criteria.'})
        result = {'theme': theme, 'region': region, 'start_year': start_year, 'end_year': end_year, 'timeline': filtered}
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {str(e)}'


TOOL_SPEC = {
    "name": "generate_cultural_timeline",
    "description": "Generate a chronological timeline visualization of cultural events, artworks, literary works, or historical milestones based on a specified theme, region, or period, returning a structured list of events with dates and summaries for use in presentations or reports.",
    "category": "visualization",
    "domain": "culture",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "theme": {
            "type": "string",
            "description": "The cultural theme or topic for the timeline, e.g., Renaissance art, Japanese literature, or music festivals."
        },
        "region": {
            "type": "string",
            "description": "Geographic region or country to filter events, e.g., Europe, Japan, or global."
        },
        "start_year": {
            "type": "integer",
            "description": "Start year for the timeline range, e.g., 1400. Default is 0.",
            "minimum": 0
        },
        "end_year": {
            "type": "integer",
            "description": "End year for the timeline range, e.g., 1600. Default is current year.",
            "minimum": 0
        },
        "max_events": {
            "type": "integer",
            "description": "Optional: Maximum number of events to include in the timeline (1-50). Default is 20.",
            "minimum": 1,
            "maximum": 50
        }
    },
    "required": [
        "theme"
    ]
},
}
