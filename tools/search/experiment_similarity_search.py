"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Search for scientific experiments based on semantic similarity to query."""
    import json
    import math
    from datetime import datetime

    try:
        data = json.loads(payload)
        query_text = data.get("query_text")
        if not query_text:
            return json.dumps({"error": "query_text is required"})

        max_results = min(max(data.get("max_results", 5), 1), 50)
        min_similarity = max(0.0, min(data.get("min_similarity", 0.3), 1.0))
        exper_type = data.get("experiment_type")
        year_range = data.get("year_range")

        # Simulated experiment database
        experiments = [
            {"id": 1, "title": "Photosynthetic efficiency under varying CO2 concentrations", "type": "controlled", "year": 2022, "keywords": ["photosynthesis", "CO2", "chlorophyll", "light intensity"], "hypothesis": "Increased CO2 enhances photosynthetic rate in C3 plants"},
            {"id": 2, "title": "Behavioral response of Drosophila to magnetic fields", "type": "controlled", "year": 2021, "keywords": ["magnetic field", "behavior", "Drosophila", "navigation"], "hypothesis": "Fruit flies can detect and respond to Earth-strength magnetic fields"},
            {"id": 3, "title": "Long-term climate patterns in Arctic sea ice extent", "type": "observational", "year": 2023, "keywords": ["climate", "Arctic", "sea ice", "temperature", "satellite"], "hypothesis": "Arctic sea ice decline accelerates with positive feedback loops"},
            {"id": 4, "title": "Drug efficacy of novel antibiotics against MRSA", "type": "controlled", "year": 2022, "keywords": ["antibiotic", "MRSA", "bacterial resistance", "clinical trial"], "hypothesis": "Novel beta-lactamase inhibitors restore antibiotic sensitivity in MRSA"},
            {"id": 5, "title": "Neural network model for protein folding prediction", "type": "computational", "year": 2023, "keywords": ["protein folding", "deep learning", "AlphaFold", "amino acid"], "hypothesis": "Transformer-based architectures can predict 3D protein structures from sequence alone"},
            {"id": 6, "title": "Soil microbiome diversity in agricultural vs forest ecosystems", "type": "observational", "year": 2021, "keywords": ["microbiome", "soil", "biodiversity", "16S rRNA"], "hypothesis": "Land use type significantly alters microbial community composition and function"},
            {"id": 7, "title": "Quantum entanglement in superconducting qubit arrays", "type": "controlled", "year": 2023, "keywords": ["quantum", "entanglement", "superconducting", "qubit", "coherence"], "hypothesis": "Multi-qubit entanglement can be maintained beyond 100 microseconds at millikelvin temperatures"},
            {"id": 8, "title": "Ocean acidification effects on coral calcification", "type": "controlled", "year": 2022, "keywords": ["ocean acidification", "coral", "calcification", "pH", "carbonate"], "hypothesis": "Reduced seawater pH decreases coral skeletal density and growth rate"},
            {"id": 9, "title": "Gene expression patterns in drought-resistant wheat cultivars", "type": "field", "year": 2023, "keywords": ["gene expression", "drought", "wheat", "transcriptomics", "abiotic stress"], "hypothesis": "Upregulation of dehydrin genes correlates with improved drought tolerance in Triticum aestivum"},
            {"id": 10, "title": "Dark matter distribution in galactic halos using gravitational lensing", "type": "observational", "year": 2022, "keywords": ["dark matter", "gravitational lensing", "galaxy", "halo", "cosmology"], "hypothesis": "Dark matter halos follow a universal density profile with cuspy centers"}
        ]

        # Simple keyword matching as similarity proxy (real system would use embeddings)
        query_lower = query_text.lower()
        query_tokens = set(query_lower.split())

        results = []
        for exp in experiments:
            # Apply filters
            if exper_type and exp["type"] != exper_type:
                continue
            if year_range:
                if year_range.get("start") and exp["year"] < year_range["start"]:
                    continue
                if year_range.get("end") and exp["year"] > year_range["end"]:
                    continue

            # Calculate similarity score (simplified)
            text_fields = [exp["title"].lower(), exp["hypothesis"].lower()] + [k.lower() for k in exp["keywords"]]
            combined_text = " ".join(text_fields)
            text_tokens = set(combined_text.split())

            if len(query_tokens) == 0:
                similarity = 0.0
            else:
                intersection = len(query_tokens.intersection(text_tokens))
                union = len(query_tokens.union(text_tokens))
                similarity = intersection / union if union > 0 else 0.0

            if similarity >= min_similarity:
                results.append({
                    "id": exp["id"],
                    "title": exp["title"],
                    "type": exp["type"],
                    "year": exp["year"],
                    "keywords": exp["keywords"],
                    "relevance_score": round(similarity, 4)
                })

        # Sort by relevance score descending
        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        results = results[:max_results]

        return json.dumps({
            "query": query_text,
            "total_matches": len(results),
            "results": results,
            "metadata": {
                "max_results_requested": max_results,
                "min_similarity_threshold": min_similarity
            }
        }, ensure_ascii=False)

    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON payload: {str(e)}"})
    except Exception as e:
        return json.dumps({"error": str(e)})


TOOL_SPEC = {
    "name": "experiment_similarity_search",
    "description": "Search for scientific experiments based on their design methodology, hypothesis, variables, or observation types using semantic similarity to find related studies in the experiment knowledge base. Returns a ranked list of matched experiments with their titles, core parameters, and relevance scores for literature review and research cross-referencing.",
    "category": "search",
    "domain": "science",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "query_text": {
            "type": "string",
            "description": "Natural language description of the experiment characteristics to search for (e.g., methodology, hypothesis, variables, conditions)"
        },
        "max_results": {
            "type": "integer",
            "description": "Optional: Maximum number of matching experiments to return (default: 5, range: 1-50)"
        },
        "min_similarity": {
            "type": "number",
            "description": "Optional: Minimum similarity threshold between 0 and 1 for result inclusion (default: 0.3)"
        },
        "experiment_type": {
            "type": "string",
            "description": "Optional: Filter by experiment type (e.g., controlled, observational, field, computational)",
            "enum": [
                "controlled",
                "observational",
                "field",
                "computational",
                "quasi-experimental"
            ]
        },
        "year_range": {
            "type": "object",
            "description": "Optional: Filter by publication year range",
            "properties": {
                "start": {
                    "type": "integer",
                    "description": "Start year (inclusive), must be between 1900 and current year"
                },
                "end": {
                    "type": "integer",
                    "description": "End year (inclusive), must be between start year and current year"
                }
            }
        }
    },
    "required": [
        "query_text"
    ]
},
}
