"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Search for scientific experiments by keyword, methodology, or outcome."""
    import json
    try:
        data = json.loads(payload)
        query = data.get('query')
        if not query:
            return json.dumps({'error': 'Missing required parameter: query'})
        methodology = data.get('methodology')
        field = data.get('field')
        year_from = data.get('year_from', 1900)
        year_to = data.get('year_to', 2025)
        max_results = data.get('max_results', 10)
        # Simulated experiment database (in production, this would query a real database or API)
        experiments = [
            {'title': 'CRISPR-Cas9 gene editing in human embryos', 'hypothesis': 'CRISPR can correct genetic mutations in early embryos', 'variables': {'independent': 'CRISPR guide RNA', 'dependent': 'gene correction rate'}, 'methodology': 'Randomized controlled trial', 'field': 'biology', 'outcome': 'Successful correction in 72% of cases', 'publication': {'title': 'Nature Medicine', 'year': 2023, 'doi': '10.1038/s41591-023-02245-1'}},
            {'title': 'Photosynthetic efficiency in algae under varying light spectra', 'hypothesis': 'Red and blue light increase algal biomass production', 'variables': {'independent': 'light spectrum', 'dependent': 'biomass yield'}, 'methodology': 'Observational study', 'field': 'environmental_science', 'outcome': 'Blue light increased biomass by 30%', 'publication': {'title': 'Journal of Phycology', 'year': 2021, 'doi': '10.1111/jpy.13145'}},
            {'title': 'Effect of cognitive behavioral therapy on anxiety in adolescents', 'hypothesis': 'CBT reduces anxiety scores compared to placebo', 'variables': {'independent': 'CBT sessions', 'dependent': 'anxiety score (GAD-7)'}, 'methodology': 'Randomized controlled trial', 'field': 'psychology', 'outcome': 'Significant reduction (p<0.05)', 'publication': {'title': 'Journal of Clinical Psychology', 'year': 2022, 'doi': '10.1002/jclp.23345'}},
            {'title': 'Superconductivity in graphene at room temperature', 'hypothesis': 'Twisted bilayer graphene exhibits superconductivity above 300K', 'variables': {'independent': 'twist angle', 'dependent': 'critical temperature'}, 'methodology': 'Simulation', 'field': 'physics', 'outcome': 'Predicted Tc ~ 350K', 'publication': {'title': 'Physical Review Letters', 'year': 2024, 'doi': '10.1103/PhysRevLett.132.056001'}},
            {'title': 'Enzyme kinetics of lactase in dairy processing', 'hypothesis': 'pH 6.5 maximizes lactose hydrolysis rate', 'variables': {'independent': 'pH', 'dependent': 'reaction rate (umol/min)'}, 'methodology': 'Observational study', 'field': 'chemistry', 'outcome': 'Optimal pH 6.5, Km=1.2 mM', 'publication': {'title': 'Journal of Agricultural and Food Chemistry', 'year': 2020, 'doi': '10.1021/acs.jafc.9b08000'}}
        ]
        # Filter by query (case-insensitive substring match across title, hypothesis, outcome)
        query_lower = query.lower()
        results = [exp for exp in experiments if (query_lower in exp['title'].lower() or query_lower in exp['hypothesis'].lower() or query_lower in exp['outcome'].lower())]
        # Filter by methodology if provided
        if methodology:
            results = [exp for exp in results if exp['methodology'].lower() == methodology.lower()]
        # Filter by field if provided
        if field:
            results = [exp for exp in results if exp['field'] == field]
        # Filter by year range
        results = [exp for exp in results if year_from <= exp['publication']['year'] <= year_to]
        # Limit results
        results = results[:max_results]
        return json.dumps({'query': query, 'total_results': len(results), 'experiments': results}, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "experiment_search",
    "description": "Search for scientific experiments by keyword, methodology, or outcome, returning a list of matching experiments with their titles, hypotheses, variables, results, and publication references.",
    "category": "search",
    "domain": "science",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "The search keyword or phrase (e.g., 'CRISPR gene editing', 'photosynthesis in algae')."
        },
        "methodology": {
            "type": "string",
            "description": "Optional: Filter experiments by methodology (e.g., 'randomized controlled trial', 'observational study', 'simulation')."
        },
        "field": {
            "type": "string",
            "enum": [
                "biology",
                "chemistry",
                "physics",
                "psychology",
                "environmental_science",
                "medicine"
            ],
            "description": "Optional: Scientific field to narrow the search."
        },
        "year_from": {
            "type": "integer",
            "minimum": 1900,
            "maximum": 2025,
            "description": "Optional: The start year for the experiment publication date range."
        },
        "year_to": {
            "type": "integer",
            "minimum": 1900,
            "maximum": 2025,
            "description": "Optional: The end year for the experiment publication date range."
        },
        "max_results": {
            "type": "integer",
            "minimum": 1,
            "maximum": 100,
            "description": "Optional: Maximum number of results to return (default 10)."
        }
    },
    "required": [
        "query"
    ]
},
}
