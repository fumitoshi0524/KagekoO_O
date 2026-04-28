"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        query = data.get('query')
        search_type = data.get('search_type')
        include_properties = data.get('include_properties')

        if not query or not search_type:
            return json.dumps({'error': 'Missing required parameters: query, search_type'}, ensure_ascii=False)

        # Simulated compound database (in real-world, would query PubChem or similar API)
        compound_db = [
            {
                'name': 'Water',
                'formula': 'H2O',
                'cas_number': '7732-18-5',
                'molecular_weight': 18.015,
                'iupac_name': 'oxidane',
                'smiles': 'O',
                'inchi': 'InChI=1S/H2O/h1H2',
                'logp': -0.2,
                'melting_point': 0.0
            },
            {
                'name': 'Ethanol',
                'formula': 'C2H6O',
                'cas_number': '64-17-5',
                'molecular_weight': 46.068,
                'iupac_name': 'ethanol',
                'smiles': 'CCO',
                'inchi': 'InChI=1S/C2H6O/c1-2-3/h3H,2H2,1H3',
                'logp': -0.3,
                'melting_point': -114.1
            },
            {
                'name': 'Carbon dioxide',
                'formula': 'CO2',
                'cas_number': '124-38-9',
                'molecular_weight': 44.009,
                'iupac_name': 'carbon dioxide',
                'smiles': 'C(=O)=O',
                'inchi': 'InChI=1S/CO2/c2-1-3',
                'logp': 0.83,
                'melting_point': -56.6
            }
        ]

        results = []
        for compound in compound_db:
            if search_type == 'name' and query.lower() in compound['name'].lower():
                results.append(compound)
            elif search_type == 'formula' and query.upper() == compound['formula'].upper():
                results.append(compound)
            elif search_type == 'cas_number' and query == compound['cas_number']:
                results.append(compound)

        if not results:
            return json.dumps({'matches': [], 'message': 'No compounds found matching the query.'}, ensure_ascii=False)

        # Filter properties if specified
        if include_properties:
            filtered_results = []
            for compound in results:
                filtered = {'name': compound['name'], 'formula': compound['formula'], 'cas_number': compound['cas_number']}
                for prop in include_properties:
                    if prop in compound:
                        filtered[prop] = compound[prop]
                filtered_results.append(filtered)
            results = filtered_results

        return json.dumps({'matches': results, 'count': len(results), 'message': f'Found {len(results)} compound(s).'}, ensure_ascii=False)

    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "chemical_compound_search",
    "description": "Search for chemical compounds by name, formula, or CAS number and retrieve their molecular weight, IUPAC name, and structural properties from a scientific database.",
    "category": "search",
    "domain": "science",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "The search term for the chemical compound, e.g., common name, systematic name, molecular formula, or CAS registry number."
        },
        "search_type": {
            "type": "string",
            "enum": [
                "name",
                "formula",
                "cas_number"
            ],
            "description": "The type of search to perform: by common or systematic name, molecular formula (e.g., H2O), or CAS registry number (e.g., 7732-18-5)."
        },
        "include_properties": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [
                    "molecular_weight",
                    "iupac_name",
                    "smiles",
                    "inchi",
                    "logp",
                    "melting_point"
                ]
            },
            "description": "Optional: specify which additional properties to include in the results, such as molecular weight, IUPAC name, SMILES notation, InChI, LogP, or melting point. Default returns all available properties."
        }
    },
    "required": [
        "query",
        "search_type"
    ]
},
}
