"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        events = data['events']
        start_year = data['start_year']
        end_year = data['end_year']
        aggregation = data.get('aggregation', 'year')
        
        # Filter events within window
        filtered = [e for e in events if start_year <= e['year'] <= end_year]
        
        if not filtered:
            return json.dumps({"insights": []})
        
        # Group by aggregation
        groups = {}
        for e in filtered:
            yr = e['year']
            if aggregation == 'decade':
                key = (yr // 10) * 10
            elif aggregation == 'century':
                key = (yr // 100) * 100
            else:
                key = yr
            groups.setdefault(key, {'count': 0, 'themes': set(), 'artists': set()})
            groups[key]['count'] += 1
            groups[key]['themes'].add(e.get('theme', ''))
            if 'artist' in e and e['artist']:
                groups[key]['artists'].add(e['artist'])
        
        # Compute insights
        time_ranges = sorted(groups.keys())
        peak_year = max(groups, key=lambda k: groups[k]['count'])
        all_themes = set()
        for g in groups.values():
            all_themes.update(g['themes'])
        theme_freq = {t: sum(1 for g in groups.values() if t in g['themes']) for t in all_themes}
        top_themes = sorted(theme_freq, key=theme_freq.get, reverse=True)[:5]
        
        result = {
            "total_events_analyzed": len(filtered),
            "time_range_covered": f"{start_year}-{end_year}",
            "aggregation": aggregation,
            "groups": [{"time_period": k, "event_count": groups[k]['count'], "unique_themes": list(groups[k]['themes']), "unique_artists": list(groups[k]['artists'])} for k in time_ranges],
            "peak_activity": {"time_period": peak_year, "event_count": groups[peak_year]['count']},
            "top_themes": top_themes,
            "diversity_index": len(all_themes) / len(filtered) if filtered else 0
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "cultural_trend_analyzer",
    "description": "Analyze historical cultural event data to identify trends, compute frequency of themes/artists/movements over a given period, and return insights such as top keywords, peak activity years, and correlation with economic or social indicators.",
    "category": "analysis",
    "domain": "culture",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "events": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "year": {
                        "type": "integer",
                        "description": "Year of the event (e.g., 1925)"
                    },
                    "theme": {
                        "type": "string",
                        "description": "Main theme or movement (e.g., 'Impressionism', 'Modernism')"
                    },
                    "artist": {
                        "type": "string",
                        "description": "Artist or creator name"
                    },
                    "location": {
                        "type": "string",
                        "description": "Location of event (city/country)"
                    }
                },
                "required": [
                    "year",
                    "theme"
                ]
            },
            "description": "List of cultural events with year, theme, artist, and location."
        },
        "start_year": {
            "type": "integer",
            "description": "Start year of analysis window (inclusive)."
        },
        "end_year": {
            "type": "integer",
            "description": "End year of analysis window (inclusive)."
        },
        "aggregation": {
            "type": "string",
            "enum": [
                "year",
                "decade",
                "century"
            ],
            "description": "Time granularity for trend grouping."
        }
    },
    "required": [
        "events",
        "start_year",
        "end_year"
    ]
},
}
