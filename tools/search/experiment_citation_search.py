"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        query = data.get('query_terms')
        if not query or not isinstance(query, str) or len(query.strip()) == 0:
            return json.dumps({'error': 'query_terms is required and must be a non-empty string'})
        query_clean = query.strip().lower()
        method_type = data.get('method_type', None)
        year_start = data.get('publication_year_start', None)
        year_end = data.get('publication_year_end', None)
        max_results = data.get('max_results', 10)
        if not isinstance(max_results, int) or max_results < 1 or max_results > 50:
            max_results = 10
        # Simulated database of citations
        citation_db = [
            {"title": "A rapid DNA extraction protocol for plant tissues", "journal": "Journal of Molecular Biology", "year": 2020, "doi": "10.1016/j.jmb.2020.01.001", "method": "biological"},
            {"title": "High-efficiency western blotting using semi-dry transfer", "journal": "Analytical Biochemistry", "year": 2019, "doi": "10.1016/j.ab.2019.02.005", "method": "biological"},
            {"title": "Optimized PCR primer design for gene amplification", "journal": "Nucleic Acids Research", "year": 2021, "doi": "10.1093/nar/gkab123", "method": "biological"},
            {"title": "Synthesis of gold nanoparticles via citrate reduction", "journal": "Chemistry of Materials", "year": 2018, "doi": "10.1021/acs.chemmater.8b01500", "method": "chemical"},
            {"title": "Computational analysis of protein folding using molecular dynamics", "journal": "Nature Computational Science", "year": 2022, "doi": "10.1038/s43588-022-00345-6", "method": "computational"},
            {"title": "X-ray crystallography structure determination protocol", "journal": "Acta Crystallographica D", "year": 2020, "doi": "10.1107/S2059798320001234", "method": "physical"},
            {"title": "Combined biological and chemical method for wastewater treatment", "journal": "Environmental Science & Technology", "year": 2023, "doi": "10.1021/acs.est.3c01234", "method": "mixed"}
        ]
        # Filter by method if provided
        if method_type and method_type in ['biological', 'chemical', 'physical', 'computational', 'mixed']:
            filtered = [c for c in citation_db if c['method'] == method_type]
        else:
            filtered = citation_db.copy()
        # Filter by year range if provided
        if year_start is not None and year_end is not None:
            filtered = [c for c in filtered if year_start <= c['year'] <= year_end]
        elif year_start is not None:
            filtered = [c for c in filtered if c['year'] >= year_start]
        elif year_end is not None:
            filtered = [c for c in filtered if c['year'] <= year_end]
        # Search by query terms (simple substring match on title)
        query_words = query_clean.split()
        matched = []
        for c in filtered:
            title_lower = c['title'].lower()
            if all(word in title_lower for word in query_words):
                matched.append(c)
        # Limit results
        matched = matched[:max_results]
        result = {
            'query': query.strip(),
            'method_type': method_type,
            'total_matches': len(matched),
            'citations': matched
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': f'Failed to process request: {str(e)}'})


TOOL_SPEC = {
    "name": "experiment_citation_search",
    "description": "Search for scientific experiment protocol citations by querying a curated database of published research methods, returning matching citation records with paper title, journal, publication year, and DOI link.",
    "category": "search",
    "domain": "science",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "query_terms": {
            "type": "string",
            "description": "Keywords or phrases describing the experiment or protocol (e.g., 'DNA extraction', 'western blot', 'PCR amplification')."
        },
        "method_type": {
            "type": "string",
            "enum": [
                "biological",
                "chemical",
                "physical",
                "computational",
                "mixed"
            ],
            "description": "Optional: Filter results to a specific scientific method category."
        },
        "publication_year_start": {
            "type": "integer",
            "description": "Optional: Earliest publication year to include (e.g., 2018)."
        },
        "publication_year_end": {
            "type": "integer",
            "description": "Optional: Latest publication year to include (e.g., 2024)."
        },
        "max_results": {
            "type": "integer",
            "description": "Optional: Maximum number of citation records to return (default 10, max 50)."
        }
    },
    "required": [
        "query_terms"
    ]
},
}
