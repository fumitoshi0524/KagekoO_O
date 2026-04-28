"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        keywords = data.get('keywords')
        if not keywords or not isinstance(keywords, list) or len(keywords) == 0:
            return 'error: keywords must be a non-empty list'
        industry = data.get('industry', '')
        max_results = min(data.get('max_results', 10), 50)
        region = data.get('region', '')

        # Simulated lead database (in real life, this would query a CRM or external API)
        sample_leads = [
            {"company": "TechNova Solutions", "description": "AI-powered healthcare analytics platform", "industry": "Healthcare", "region": "North America", "contact": "sales@technova.com", "revenue": "$10M-50M"},
            {"company": "GreenLeaf Finance", "description": "SaaS for sustainable investment management", "industry": "Finance", "region": "Europe", "contact": "info@greenleaf.com", "revenue": "$5M-20M"},
            {"company": "CloudBridge Systems", "description": "Enterprise cloud migration services", "industry": "Technology", "region": "North America", "contact": "partners@cloudbridge.io", "revenue": "$20M-100M"},
            {"company": "MediData Corp", "description": "Health data interoperability platform using AI", "industry": "Healthcare", "region": "APAC", "contact": "hello@medidata.asia", "revenue": "$1M-10M"},
            {"company": "RetailAI Inc.", "description": "Machine learning for retail demand forecasting", "industry": "Retail", "region": "North America", "contact": "info@retailai.com", "revenue": "$5M-20M"},
            {"company": "Safe Harbor Insurance", "description": "Insurtech with AI-driven risk assessment", "industry": "Finance", "region": "Europe", "contact": "contact@safeharbor.com", "revenue": "$50M-200M"}
        ]

        results = []
        for lead in sample_leads:
            # Check keyword match (case-insensitive)
            desc_lower = lead['description'].lower()
            matched = any(kw.lower() in desc_lower for kw in keywords)
            if not matched:
                continue
            # Check industry filter
            if industry and lead['industry'].lower() != industry.lower():
                continue
            # Check region filter
            if region and lead['region'].lower() != region.lower():
                continue
            results.append(lead)
            if len(results) >= max_results:
                break

        return json.dumps({"leads": results, "count": len(results)}, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "find_leads",
    "description": "Search for business leads by matching company descriptions against a set of keywords and return a list of potential customer companies with contact details for sales outreach.",
    "category": "search",
    "domain": "business",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "keywords": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "List of keywords to match against company descriptions (e.g., ['AI', 'healthcare', 'SaaS']). Minimum 1 keyword required."
        },
        "industry": {
            "type": "string",
            "description": "Optional: Filter leads by industry sector (e.g., 'Technology', 'Finance', 'Healthcare'). Leave empty for all industries."
        },
        "max_results": {
            "type": "integer",
            "description": "Optional: Maximum number of leads to return (default 10, max 50)."
        },
        "region": {
            "type": "string",
            "description": "Optional: Geographic region to focus search (e.g., 'North America', 'Europe', 'APAC')."
        }
    },
    "required": [
        "keywords"
    ]
},
}
