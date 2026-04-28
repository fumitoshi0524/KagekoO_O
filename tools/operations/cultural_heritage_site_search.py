"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        country = data.get('country')
        region = data.get('region')
        category = data.get('category', 'cultural')
        max_results = data.get('max_results', 10)
        if max_results < 1 or max_results > 50:
            return json.dumps({'error': 'max_results must be between 1 and 50'}, ensure_ascii=False)
        if category not in ['cultural', 'natural', 'mixed']:
            return json.dumps({'error': 'category must be cultural, natural, or mixed'}, ensure_ascii=False)
        site_database = {
            'France': [{'name': 'Mont-Saint-Michel and its Bay', 'year_inscribed': 1979, 'coordinates': {'lat': 48.636, 'lng': -1.511}, 'significance': 'A tidal island with a medieval abbey, a masterpiece of human genius.'}],
            'Egypt': [{'name': 'Memphis and its Necropolis – the Pyramid Fields from Giza to Dahshur', 'year_inscribed': 1979, 'coordinates': {'lat': 29.979, 'lng': 31.134}, 'significance': 'Home to the Great Pyramids, one of the Seven Wonders of the Ancient World.'}],
            'China': [{'name': 'The Great Wall', 'year_inscribed': 1987, 'coordinates': {'lat': 40.431, 'lng': 116.570}, 'significance': 'An ancient fortification built over centuries, symbolizing Chinese civilization.'}]
        }
        results = []
        if country:
            sites = site_database.get(country.title(), [])
            for site in sites:
                results.append(site)
        else:
            for country_sites in site_database.values():
                results.extend(country_sites)
        if region:
            region_map = {'Europe': ['France', 'Italy', 'Germany', 'Spain', 'United Kingdom'], 'Asia': ['China', 'India', 'Japan', 'Thailand'], 'Africa': ['Egypt', 'Morocco', 'South Africa', 'Ethiopia']}
            countries_in_region = region_map.get(region.title(), [])
            if country and country.title() not in countries_in_region:
                return json.dumps({'error': f'Country {country} is not in region {region}'}, ensure_ascii=False)
            filtered_results = []
            for site in results:
                for c in countries_in_region:
                    if site.get('country', c).lower() == country.lower() if country else True:
                        filtered_results.append(site)
            results = filtered_results[:max_results] if len(filtered_results) > 0 else []
        else:
            results = results[:max_results]
        return json.dumps({'sites': results, 'count': len(results)}, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "cultural_heritage_site_search",
    "description": "Search for UNESCO World Heritage sites by country, region, or category and retrieve detailed information including historical significance, year of inscription, and geographical coordinates.",
    "category": "operations",
    "domain": "culture",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "country": {
            "type": "string",
            "description": "Name of a country (in English) to filter sites by location. Must be a valid country name.",
            "examples": [
                "France",
                "Egypt",
                "China"
            ]
        },
        "region": {
            "type": "string",
            "description": "Optional: Name of a geographic region (e.g., 'Europe', 'Asia', 'Africa') to narrow the search. If provided, overrides country filter.",
            "examples": [
                "Europe",
                "Asia"
            ]
        },
        "category": {
            "type": "string",
            "description": "Type of heritage: 'cultural' for man-made sites, 'natural' for natural sites, or 'mixed' for both. Defaults to 'cultural' if omitted.",
            "enum": [
                "cultural",
                "natural",
                "mixed"
            ]
        },
        "max_results": {
            "type": "integer",
            "description": "Optional: Maximum number of sites to return in the result set. Must be between 1 and 50. Default is 10.",
            "minimum": 1,
            "maximum": 50,
            "examples": [
                5,
                20
            ]
        }
    },
    "required": []
},
}
