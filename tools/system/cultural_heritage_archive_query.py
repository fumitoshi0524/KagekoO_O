"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        artifact_type = data.get('artifact_type')
        if not artifact_type:
            return json.dumps({'error': 'artifact_type is required'}, ensure_ascii=False)
        historical_period = data.get('historical_period', '')
        region = data.get('region', '')
        keywords = data.get('keywords', [])
        limit = data.get('limit', 10)
        # Simulated archive lookup (in real scenario, query a database)
        archive = {
            'paintings': [
                {'id': 1, 'title': 'Mona Lisa', 'artist': 'Leonardo da Vinci', 'period': 'Renaissance', 'region': 'Italy', 'year': 1503, 'description': 'Portrait of Lisa Gherardini', 'materials': ['oil_on_poplar_panel']},
                {'id': 2, 'title': 'Starry Night', 'artist': 'Vincent van Gogh', 'period': 'Post-Impressionist', 'region': 'Netherlands', 'year': 1889, 'description': 'Night landscape from asylum window', 'materials': ['oil_on_canvas']}
            ],
            'sculptures': [
                {'id': 3, 'title': 'David', 'artist': 'Michelangelo', 'period': 'Renaissance', 'region': 'Italy', 'year': 1504, 'description': 'Marble statue of biblical hero', 'materials': ['marble']}
            ]
        }
        # Filter based on artifact_type
        key_map = {
            'painting': 'paintings',
            'sculpture': 'sculptures',
            'manuscript': 'manuscripts',
            'architecture': 'architecture',
            'textile': 'textiles',
            'ceramic': 'ceramics',
            'music_score': 'music_scores',
            'photograph': 'photographs',
            'film': 'films',
            'folklore': 'folklore'
        }
        collection_key = key_map.get(artifact_type)
        if not collection_key or collection_key not in archive:
            # Return empty result for unsupported types
            return json.dumps({'results': [], 'total': 0}, ensure_ascii=False)
        results = archive[collection_key]
        # Apply filters
        if historical_period:
            results = [r for r in results if r.get('period', '').lower() == historical_period.lower()]
        if region:
            results = [r for r in results if r.get('region', '').lower() == region.lower()]
        if keywords:
            kw_lower = [k.lower() for k in keywords]
            results = [r for r in results if any(k in r.get('title', '').lower() or k in r.get('artist', '').lower() or k in r.get('description', '').lower() for k in kw_lower)]
        # Apply limit
        results = results[:limit]
        return json.dumps({'results': results, 'total': len(results)}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "cultural_heritage_archive_query",
    "description": "Search and retrieve records from a cultural heritage archive based on artifact type, historical period, region, and keywords, returning structured metadata including title, date, origin, description, and related materials.",
    "category": "system",
    "domain": "culture",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "artifact_type": {
            "type": "string",
            "description": "Category of cultural artifact to search for",
            "enum": [
                "painting",
                "sculpture",
                "manuscript",
                "architecture",
                "textile",
                "ceramic",
                "music_score",
                "photograph",
                "film",
                "folklore"
            ]
        },
        "historical_period": {
            "type": "string",
            "description": "Historical period filter for the artifacts (e.g., 'Renaissance', 'Edo period', 'Ming dynasty')"
        },
        "region": {
            "type": "string",
            "description": "Geographic region or country of origin"
        },
        "keywords": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "Optional: List of search keywords to refine results by artistic style, theme, or creator"
        },
        "limit": {
            "type": "integer",
            "description": "Optional: Maximum number of results to return (1-100)",
            "minimum": 1,
            "maximum": 100
        }
    },
    "required": [
        "artifact_type"
    ]
},
}
