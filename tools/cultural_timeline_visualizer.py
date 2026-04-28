"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        domain_type = data.get("domain_type")
        region = data.get("region", "Global")
        start_year = data.get("start_year")
        end_year = data.get("end_year")
        tags = data.get("tags", [])
        max_events = data.get("max_events", 20)

        if not domain_type:
            return json.dumps({"error": "domain_type is required"}, ensure_ascii=False)
        if start_year is None or end_year is None:
            return json.dumps({"error": "start_year and end_year are required"}, ensure_ascii=False)
        if start_year > end_year:
            return json.dumps({"error": "start_year must be <= end_year"}, ensure_ascii=False)
        if max_events < 1:
            max_events = 1
        if max_events > 100:
            max_events = 100

        # Built-in cultural events database (curated list of 30 events for demonstration)
        events_db = [
            {"year": 1401, "title": "Lorenzo Ghiberti wins competition for Florence Baptistery doors", "type": "art", "region": "Europe", "tags": ["renaissance", "sculpture"]},
            {"year": 1455, "title": "Gutenberg Bible printed", "type": "literature", "region": "Europe", "tags": ["printing", "renaissance"]},
            {"year": 1508, "title": "Michelangelo begins painting Sistine Chapel ceiling", "type": "art", "region": "Europe", "tags": ["renaissance", "fresco"]},
            {"year": 1564, "title": "Birth of William Shakespeare", "type": "literature", "region": "Europe", "tags": ["renaissance", "playwright"]},
            {"year": 1607, "title": "First performance of Monteverdi's L'Orfeo", "type": "music", "region": "Europe", "tags": ["baroque", "opera"]},
            {"year": 1687, "title": "Newton publishes Principia Mathematica", "type": "history", "region": "Europe", "tags": ["science", "enlightenment"]},
            {"year": 1722, "title": "Bach completes The Well-Tempered Clavier, Book 1", "type": "music", "region": "Europe", "tags": ["baroque", "keyboard"]},
            {"year": 1789, "title": "French Revolution begins", "type": "history", "region": "Europe", "tags": ["revolution", "politics"]},
            {"year": 1808, "title": "Beethoven's Symphony No. 5 premieres", "type": "music", "region": "Europe", "tags": ["classical", "symphony"]},
            {"year": 1813, "title": "Jane Austen publishes Pride and Prejudice", "type": "literature", "region": "Europe", "tags": ["novel", "romanticism"]},
            {"year": 1830, "title": "Delacroix paints Liberty Leading the People", "type": "art", "region": "Europe", "tags": ["romanticism", "painting"]},
            {"year": 1862, "title": "Victor Hugo publishes Les Misérables", "type": "literature", "region": "Europe", "tags": ["novel", "realism"]},
            {"year": 1874, "title": "First Impressionist Exhibition in Paris", "type": "art", "region": "Europe", "tags": ["impressionism", "painting"]},
            {"year": 1895, "title": "Lumière brothers hold first film screening", "type": "history", "region": "Europe", "tags": ["cinema", "technology"]},
            {"year": 1905, "title": "Einstein publishes special relativity", "type": "history", "region": "Europe", "tags": ["science", "modern"]},
            {"year": 1913, "title": "Stravinsky's The Rite of Spring premieres", "type": "music", "region": "Europe", "tags": ["modern", "ballet"]},
            {"year": 1922, "title": "T.S. Eliot publishes The Waste Land", "type": "literature", "region": "Europe", "tags": ["modernism", "poetry"]},
            {"year": 1925, "title": "F. Scott Fitzgerald publishes The Great Gatsby", "type": "literature", "region": "North America", "tags": ["modernism", "novel"]},
            {"year": 1945, "title": "End of World War II", "type": "history", "region": "Global", "tags": ["war", "20th century"]},
            {"year": 1947, "title": "Jackson Pollock begins drip paintings", "type": "art", "region": "North America", "tags": ["abstract expressionism", "painting"]},
            {"year": 1954, "title": "Elvis Presley records first songs", "type": "music", "region": "North America", "tags": ["rock and roll", "pop"]},
            {"year": 1955, "title": "Rosa Parks refuses to give up bus seat", "type": "history", "region": "North America", "tags": ["civil rights", "social"]},
            {"year": 1969, "title": "Woodstock Music Festival", "type": "music", "region": "North America", "tags": ["rock", "counterculture"]},
            {"year": 1984, "title": "Margaret Atwood publishes The Handmaid's Tale", "type": "literature", "region": "North America", "tags": ["dystopian", "feminist"]},
            {"year": 1000, "title": "Lady Murasaki Shikibu writes The Tale of Genji", "type": "literature", "region": "East Asia", "tags": ["classical", "novel"]},
            {"year": 1300, "title": "Dante Alighieri writes Divine Comedy", "type": "literature", "region": "Europe", "tags": ["medieval", "poetry"]},
            {"year": 1600, "title": "Kabuki theater emerges in Japan", "type": "history", "region": "East Asia", "tags": ["theater", "japanese"]},
            {"year": 1760, "title": "Industrial Revolution begins in Britain", "type": "history", "region": "Europe", "tags": ["technology", "economic"]},
            {"year": 1927, "title": "Virginia Woolf publishes To the Lighthouse", "type": "literature", "region": "Europe", "tags": ["modernism", "stream of consciousness"]},
            {"year": 1951, "title": "Miles Davis records Birth of the Cool", "type": "music", "region": "North America", "tags": ["jazz", "cool"]}
        ]

        # Filter events by domain_type
        filtered = [e for e in events_db if e["year"] >= start_year and e["year"] <= end_year]
        if domain_type != "all":
            filtered = [e for e in filtered if e["type"] == domain_type]

        # Filter by region if specified (case-insensitive partial match)
        region_lower = region.lower()
        if region_lower not in ["global", "world", "all"]:
            filtered = [e for e in filtered if region_lower in e["region"].lower()]

        # Filter by tags if provided
        if tags:
            tags_lower = [t.lower() for t in tags]
            filtered = [e for e in filtered if any(t in [tt.lower() for tt in e["tags"]] for t in tags_lower)]

        # Sort by year
        filtered.sort(key=lambda x: x["year"])

        # Limit results
        events = filtered[:max_events]

        result = {
            "timeline": {
                "domain": domain_type,
                "region": region,
                "start_year": start_year,
                "end_year": end_year,
                "total_events_found": len(filtered),
                "events_returned": len(events)
            },
            "events": events
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "cultural_timeline_visualizer",
    "description": "Generate a chronological timeline visualization of cultural events, artworks, or literary movements within a specified historical period and region, returning a structured JSON with event data suitable for chart/display rendering.",
    "category": "visualization",
    "domain": "culture",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "domain_type": {
            "type": "string",
            "description": "Cultural domain to visualize: art, literature, music, history, or all",
            "enum": [
                "art",
                "literature",
                "music",
                "history",
                "all"
            ]
        },
        "region": {
            "type": "string",
            "description": "Geographic or cultural region to filter events (e.g., Europe, East Asia, Global)",
            "default": "Global"
        },
        "start_year": {
            "type": "integer",
            "description": "Start year of the time range (e.g., 1800)",
            "minimum": -5000,
            "maximum": 2100
        },
        "end_year": {
            "type": "integer",
            "description": "End year of the time range (e.g., 1900)",
            "minimum": -5000,
            "maximum": 2100
        },
        "tags": {
            "type": "array",
            "description": "Optional: filter events by themes or tags (e.g., ['renaissance', 'impressionism', 'baroque'])",
            "items": {
                "type": "string"
            }
        },
        "max_events": {
            "type": "integer",
            "description": "Optional: maximum number of events to return (max 100)",
            "default": 20,
            "minimum": 1,
            "maximum": 100
        }
    },
    "required": [
        "domain_type",
        "start_year",
        "end_year"
    ]
},
}
