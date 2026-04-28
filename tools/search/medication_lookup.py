"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        query = data.get("query", "").strip()
        if not query or len(query) < 2:
            return json.dumps({"error": "Query must be at least 2 characters.", "results": []})
        country = data.get("country", "US").upper()
        if country not in ["US", "UK", "CA", "AU", "DE", "FR", "IN", "BR"]:
            country = "US"
        limit = data.get("limit", 10)
        if not isinstance(limit, int) or limit < 1 or limit > 20:
            limit = 10
        # Simulated medication database for demonstration
        fake_db = {
            "metformin": {
                "generic_name": "Metformin Hydrochloride",
                "brand_names": ["Glucophage", "Fortamet", "Riomet"],
                "therapeutic_class": "Biguanide",
                "indications": ["Type 2 Diabetes Mellitus"],
                "dosage_forms": ["Tablet", "Oral Solution", "Extended-Release Tablet"],
                "strengths": ["500 mg", "850 mg", "1000 mg"],
                "side_effects": ["Gastrointestinal upset", "Metallic taste", "Diarrhea"],
                "country": "US"
            },
            "lipitor": {
                "generic_name": "Atorvastatin Calcium",
                "brand_names": ["Lipitor", "Atorlip"],
                "therapeutic_class": "HMG-CoA Reductase Inhibitor (Statin)",
                "indications": ["Hyperlipidemia", "Coronary Artery Disease"],
                "dosage_forms": ["Tablet"],
                "strengths": ["10 mg", "20 mg", "40 mg", "80 mg"],
                "side_effects": ["Muscle pain", "Headache", "Nausea"],
                "country": "US"
            },
            "ibuprofen": {
                "generic_name": "Ibuprofen",
                "brand_names": ["Advil", "Motrin", "Nurofen"],
                "therapeutic_class": "Nonsteroidal Anti-Inflammatory Drug (NSAID)",
                "indications": ["Pain", "Fever", "Inflammation"],
                "dosage_forms": ["Tablet", "Capsule", "Suspension", "Topical Gel"],
                "strengths": ["100 mg", "200 mg", "400 mg", "600 mg"],
                "side_effects": ["Gastrointestinal irritation", "Bleeding risk", "Kidney impairment"],
                "country": "US"
            }
        }
        # Simple matching logic
        query_lower = query.lower()
        results = []
        for key, med in fake_db.items():
            if query_lower in key or query_lower in med["generic_name"].lower():
                results.append(med)
                if len(results) >= limit:
                    break
            for brand in med["brand_names"]:
                if query_lower in brand.lower():
                    if med not in results:
                        results.append(med)
                    break
            if len(results) >= limit:
                break
        return json.dumps({"query": query, "country": country, "results": results, "error": None}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e), "results": []})


TOOL_SPEC = {
    "name": "medication_lookup",
    "description": "Search for a medication by brand name or generic name to retrieve its active ingredients, therapeutic class, dosage forms, strengths, and common side effects, returning a structured medication profile for clinical decision support.",
    "category": "search",
    "domain": "healthcare",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "The medication brand name or generic name to search (e.g., 'Metformin', 'Advil'). Must be at least 2 characters.",
            "examples": [
                "lipitor",
                "ibuprofen",
                "metformin"
            ]
        },
        "country": {
            "type": "string",
            "enum": [
                "US",
                "UK",
                "CA",
                "AU",
                "DE",
                "FR",
                "IN",
                "BR"
            ],
            "description": "Optional: Country-specific medication database to search. Defaults to 'US' if not provided.",
            "examples": [
                "US",
                "UK",
                "CA"
            ]
        },
        "limit": {
            "type": "integer",
            "description": "Optional: Maximum number of search results to return (1-20). Defaults to 10.",
            "examples": [
                5,
                10,
                20
            ]
        }
    },
    "required": [
        "query"
    ]
},
}
