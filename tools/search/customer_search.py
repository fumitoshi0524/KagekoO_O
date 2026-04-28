"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        query = data.get('query', '').strip()
        if not query:
            return json.dumps({"error": "Missing required parameter: query"}, ensure_ascii=False)
        segment = data.get('segment', 'all')
        limit = min(data.get('limit', 20), 100)
        active_only = data.get('active_only', False)
        # Simulated customer database
        customers = [
            {"id": "C001", "name": "Acme Corp", "email": "contact@acme.com", "phone": "+1-555-0101", "company": "Acme Corp", "segment": "enterprise", "status": "active"},
            {"id": "C002", "name": "Jane Smith", "email": "jane@example.com", "phone": "+1-555-0102", "company": "TechStart", "segment": "smb", "status": "active"},
            {"id": "C003", "name": "Bob Lee", "email": "bob@example.com", "phone": "+1-555-0103", "company": "Design Studio", "segment": "premium", "status": "inactive"},
            {"id": "C004", "name": "Global Industries", "email": "info@global.com", "phone": "+1-555-0104", "company": "Global Industries", "segment": "enterprise", "status": "active"},
            {"id": "C005", "name": "Alice Wang", "email": "alice@test.com", "phone": "+1-555-0105", "company": "Freelance", "segment": "trial", "status": "active"}
        ]
        # Filter by query
        query_lower = query.lower()
        results = [c for c in customers if any(query_lower in str(val).lower() for val in [c['name'], c['email'], c['phone'], c['company']])]
        # Filter by segment
        if segment != 'all':
            results = [c for c in results if c['segment'] == segment]
        # Filter by active status
        if active_only:
            results = [c for c in results if c['status'] == 'active']
        # Sort by relevance (simple: exact match first, then by name length)
        results.sort(key=lambda c: (0 if query_lower == c['name'].lower() else 1, len(c['name'])))
        # Apply limit
        results = results[:limit]
        return json.dumps({"customers": results, "total_count": len(results)}, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "customer_search",
    "description": "Search for customer records by name, email, phone, or company. Returns matching customer profiles including contact info, account status, and segment tags for use in CRM and support workflows.",
    "category": "search",
    "domain": "business",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Free-text search query to match against customer name, email, phone, or company name."
        },
        "segment": {
            "type": "string",
            "description": "Optional: Filter results by customer segment (e.g., enterprise, smb, premium, trial).",
            "enum": [
                "enterprise",
                "smb",
                "premium",
                "trial",
                "all"
            ]
        },
        "limit": {
            "type": "integer",
            "description": "Optional: Maximum number of customer records to return (default 20, max 100).",
            "minimum": 1,
            "maximum": 100
        },
        "active_only": {
            "type": "boolean",
            "description": "Optional: If True, only return customers with an active account status."
        }
    },
    "required": [
        "query"
    ]
},
}
