"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        source = data['source_database']
        reference = data['reference_catalog']
        fields = data.get('check_fields', None)
        include_deac = data.get('include_deaccessioned', False)

        # Simulated database lookups (replace with real API calls in production)
        art_inventory = {
            "met_museum": [{"id": "MET001", "title": "Starry Night", "artist": "van Gogh", "date": 1889, "medium": "oil"}],
            "british_museum": [{"id": "BM001", "title": "The Great Wave", "artist": "Hokusai", "date": 1831, "medium": "woodblock"}],
            "louvre": [{"id": "LV001", "title": "Mona Lisa", "artist": "Leonardo da Vinci", "date": 1503, "medium": "oil"}],
            "smithsonian": [{"id": "SM001", "title": "Wright Flyer", "artist": "Wright Brothers", "date": 1903, "medium": "metal"}],
            "local_archive": []
        }
        reference_catalog = {
            "world_art_census": [
                {"id": "CEN001", "title": "Starry Night", "artist": "Vincent van Gogh", "date": 1889, "medium": "oil on canvas"},
                {"id": "CEN002", "title": "The Great Wave off Kanagawa", "artist": "Katsushika Hokusai", "date": 1831, "medium": "woodblock print"},
                {"id": "CEN003", "title": "Mona Lisa", "artist": "Leonardo da Vinci", "date": 1503, "medium": "oil on poplar panel"},
                {"id": "CEN004", "title": "The Thinker", "artist": "Auguste Rodin", "date": 1882, "medium": "bronze"}
            ],
            "national_heritage_list": [],
            "union_list_of_artists": []
        }

        source_items = art_inventory.get(source, [])
        ref_items = reference_catalog.get(reference, [])

        # Build lookup by title
        ref_by_title = {}
        for item in ref_items:
            title_lower = item['title'].lower()
            ref_by_title[title_lower] = item

        missing = []
        duplicates = []
        inconsistencies = []

        seen_titles = set()
        for item in source_items:
            title_lower = item['title'].lower()
            if title_lower in seen_titles:
                duplicates.append(item)
            seen_titles.add(title_lower)

            if title_lower not in ref_by_title:
                if include_deac or item.get('deaccessioned', False) == False:
                    missing.append(item)
            else:
                ref_item = ref_by_title[title_lower]
                if fields:
                    for field in fields:
                        if field in item and field in ref_item:
                            if str(item[field]) != str(ref_item[field]):
                                inconsistencies.append({
                                    "source_id": item['id'],
                                    "field": field,
                                    "source_value": item[field],
                                    "ref_value": ref_item[field]
                                })
                else:
                    for field in ['title', 'artist', 'date', 'medium']:
                        if field in item and field in ref_item:
                            if str(item[field]) != str(ref_item[field]):
                                inconsistencies.append({
                                    "source_id": item['id'],
                                    "field": field,
                                    "source_value": item[field],
                                    "ref_value": ref_item[field]
                                })

        result = {
            "audit_summary": {
                "source_database": source,
                "reference_catalog": reference,
                "total_source_items": len(source_items),
                "total_reference_items": len(ref_items),
                "missing_records": len(missing),
                "duplicate_entries": len(duplicates),
                "metadata_inconsistencies": len(inconsistencies)
            },
            "missing_records": missing if missing else "None found",
            "duplicate_entries": duplicates if duplicates else "None found",
            "metadata_inconsistencies": inconsistencies if inconsistencies else "None found"
        }
        return json.dumps(result, ensure_ascii=False)
    except KeyError as e:
        return f'error: Missing required parameter: {e}'
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "artifact_inventory_audit",
    "description": "Audit and reconcile the digital catalog of cultural artifacts (paintings, sculptures, manuscripts) across museum collection databases, returning a structured report of missing records, duplicate entries, and metadata inconsistencies.",
    "category": "system",
    "domain": "culture",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "source_database": {
            "type": "string",
            "description": "Identifier of the primary collection database to audit (e.g., museum ID, archive name).",
            "enum": [
                "met_museum",
                "british_museum",
                "louvre",
                "smithsonian",
                "local_archive"
            ]
        },
        "reference_catalog": {
            "type": "string",
            "description": "Identifier of the authoritative reference catalog to compare against (e.g., census of antique art, national heritage list).",
            "enum": [
                "world_art_census",
                "national_heritage_list",
                "union_list_of_artists"
            ]
        },
        "check_fields": {
            "type": "array",
            "description": "Optional: List of metadata fields to compare for consistency (e.g., title, artist, date, medium, dimensions, provenance). If omitted, checks all available fields.",
            "items": {
                "type": "string",
                "enum": [
                    "title",
                    "artist",
                    "date",
                    "medium",
                    "dimensions",
                    "provenance",
                    "acquisition_date",
                    "location"
                ]
            }
        },
        "include_deaccessioned": {
            "type": "boolean",
            "description": "Optional: If True, includes deaccessioned or removed items in the audit report. Default False."
        }
    },
    "required": [
        "source_database",
        "reference_catalog"
    ]
},
}
