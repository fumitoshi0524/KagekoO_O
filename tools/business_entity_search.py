"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        query = data.get('query', '').strip()
        if len(query) < 2:
            return json.dumps({'error': 'Query must be at least 2 characters'})

        entity_type = data.get('entity_type', 'all')
        industry = data.get('industry', None)
        country = data.get('country', None)
        active_only = data.get('active_only', False)
        max_results = min(data.get('max_results', 20), 100)

        # Simulated business entity database
        business_entities = [
            {"id": "BE-001", "name": "Acme Corp", "type": "client", "industry": "technology", "country": "US", "status": "active", "registration": "123456789"},
            {"id": "BE-002", "name": "GlobalTech Solutions", "type": "vendor", "industry": "technology", "country": "DE", "status": "active", "registration": "DE987654321"},
            {"id": "BE-003", "name": "HealthFirst Medical", "type": "partner", "industry": "healthcare", "country": "US", "status": "active", "registration": "US456789123"},
            {"id": "BE-004", "name": "EcoBuild Materials", "type": "vendor", "industry": "manufacturing", "country": "CN", "status": "inactive", "registration": "CN321654987"},
            {"id": "BE-005", "name": "FinTrust Banking", "type": "client", "industry": "finance", "country": "US", "status": "active", "registration": "US147258369"},
            {"id": "BE-006", "name": "MedTech Innovations", "type": "partner", "industry": "healthcare", "country": "IL", "status": "active", "registration": "IL963852741"},
            {"id": "BE-007", "name": "AutoParts Inc.", "type": "vendor", "industry": "manufacturing", "country": "MX", "status": "active", "registration": "MX741852963"},
            {"id": "BE-008", "name": "DataAnalytics Pro", "type": "contact", "industry": "technology", "country": "UK", "status": "active", "registration": "UK852963741"},
            {"id": "BE-009", "name": "GreenEnergy Corp", "type": "client", "industry": "energy", "country": "NO", "status": "inactive", "registration": "NO369258147"},
            {"id": "BE-010", "name": "SafeHands Insurance", "type": "partner", "industry": "finance", "country": "CH", "status": "active", "registration": "CH159357456"}
        ]

        results = []
        query_lower = query.lower()
        for entity in business_entities:
            # Filter by entity type
            if entity_type != 'all' and entity['type'] != entity_type:
                continue

            # Filter by active status
            if active_only and entity['status'] != 'active':
                continue

            # Filter by industry
            if industry and industry.lower() not in entity['industry'].lower():
                continue

            # Filter by country
            if country and country.upper() != entity['country']:
                continue

            # Search query matching
            name_match = query_lower in entity['name'].lower()
            reg_match = query in entity['registration']
            if not name_match and not reg_match:
                continue

            results.append(entity)

        # Sort by relevance (exact name match first)
        results.sort(key=lambda x: (0 if x['name'].lower() == query_lower else 1 if query_lower in x['name'].lower() else 2))

        # Limit results
        results = results[:max_results]

        return json.dumps({
            'count': len(results),
            'results': results,
            'query': query,
            'filters': {
                'entity_type': entity_type,
                'industry': industry,
                'country': country,
                'active_only': active_only
            }
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({'error': str(e)})


TOOL_SPEC = {
    "name": "business_entity_search",
    "description": "Search across business entities (clients, vendors, partners, contacts) by name, industry, location, or registration number, returning matching profiles with key identifiers and status.",
    "category": "search",
    "domain": "business",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Free-text search string to match against entity names, aliases, or registration numbers. Minimum 2 characters."
        },
        "entity_type": {
            "type": "string",
            "enum": [
                "client",
                "vendor",
                "partner",
                "contact",
                "all"
            ],
            "description": "Filter results to a specific business entity type: client, vendor, partner, contact, or all types."
        },
        "industry": {
            "type": "string",
            "description": "Optional: Filter by industry sector (e.g., 'technology', 'healthcare', 'manufacturing', 'finance'). Partial matches supported."
        },
        "country": {
            "type": "string",
            "description": "Optional: Filter by ISO 3166-1 alpha-2 country code (e.g., 'US', 'DE', 'JP')."
        },
        "active_only": {
            "type": "boolean",
            "description": "Optional: When true, returns only entities with active status. Default false returns all statuses."
        },
        "max_results": {
            "type": "integer",
            "description": "Maximum number of results to return (1-100). Default 20.",
            "minimum": 1,
            "maximum": 100
        }
    },
    "required": [
        "query"
    ]
},
}
