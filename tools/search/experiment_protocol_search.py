"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        query = data.get('query', '').strip().lower()
        if not query:
            return 'error: query is required'

        # Simulated protocol database (in production would query a real database)
        protocols_db = [
            {
                "title": "PCR Amplification of DNA Samples",
                "author": "Dr. Jane Smith",
                "materials": ["Taq polymerase", "dNTPs", "primers", "DNA template", "thermocycler"],
                "steps": [
                    "Prepare master mix with Taq, dNTPs, primers, buffer.",
                    "Add DNA template.",
                    "Run thermocycler: 95°C 2min, 30 cycles (95°C 30s, 55°C 30s, 72°C 60s), 72°C 5min.",
                    "Analyze products on agarose gel."
                ],
                "safety_notes": "Use gloves and UV shield for gel visualization."
            },
            {
                "title": "Protein Extraction from E. coli",
                "author": "Prof. Alan Turing",
                "materials": ["E. coli culture", "lysis buffer", "protease inhibitors", "centrifuge", "sonicator"],
                "steps": [
                    "Pellet cells by centrifugation.",
                    "Resuspend in lysis buffer with protease inhibitors.",
                    "Sonicate on ice.",
                    "Centrifuge to separate soluble fraction.",
                    "Store at -80°C."
                ],
                "safety_notes": "Handle liquid nitrogen and sonicator with care."
            },
            {
                "title": "Synthesis of Silver Nanoparticles",
                "author": "Dr. Maria Fernandez",
                "materials": ["silver nitrate", "sodium borohydride", "stirring plate", "ice bath"],
                "steps": [
                    "Prepare 1mM silver nitrate solution.",
                    "Add dropwise 2mM sodium borohydride while stirring.",
                    "Maintain temperature below 5°C.",
                    "Stir for 30 minutes.",
                    "Characterize by UV-Vis."
                ],
                "safety_notes": "Wear gloves; silver nitrate stains skin."
            }
        ]

        results = []
        for proto in protocols_db:
            title_match = query in proto['title'].lower()
            if title_match:
                results.append(proto)
                continue
            keyword_match = any(query in mat.lower() for mat in proto['materials'])
            if keyword_match:
                results.append(proto)
                continue

        max_results = data.get('max_results', 10)
        if max_results < 1:
            max_results = 10
        results = results[:max_results]

        # Apply filters
        if 'author' in data and data['author']:
            author_filter = data['author'].lower()
            results = [r for r in results if author_filter in r['author'].lower()]

        if 'material' in data and data['material']:
            material_filter = data['material'].lower()
            results = [r for r in results if any(material_filter in m.lower() for m in r['materials'])]

        return json.dumps({
            "protocols": results,
            "count": len(results)
        }, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "experiment_protocol_search",
    "description": "Search scientific experiment protocols by keywords, author, or material. Returns matching protocols with title, author, materials, steps, and safety notes.",
    "category": "search",
    "domain": "science",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Keywords or phrase to search in protocol titles and descriptions."
        },
        "author": {
            "type": "string",
            "description": "Optional: Filter by protocol author or principal investigator name."
        },
        "material": {
            "type": "string",
            "description": "Optional: Filter by specific material or reagent used in the protocol."
        },
        "max_results": {
            "type": "integer",
            "description": "Optional: Maximum number of results to return (default 10)."
        }
    },
    "required": [
        "query"
    ]
},
}
