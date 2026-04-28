"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        
        # Validate mandatory fields
        if 'amount' not in data or 'jurisdiction' not in data:
            return json.dumps({'error': 'Missing required input: amount and jurisdiction'}, ensure_ascii=False)
        
        amount = data['amount']
        jurisdiction = data['jurisdiction'].upper().strip()
        
        # Validate amount
        if not isinstance(amount, (int, float)) or amount < 0:
            return json.dumps({'error': 'Amount must be a non-negative number'}, ensure_ascii=False)
        
        # Built-in reference tax rates (simplified combined state + average local rates)
        tax_rates = {
            'AL': 0.04, 'AK': 0.00, 'AZ': 0.056, 'AR': 0.065, 'CA': 0.0725,
            'CO': 0.029, 'CT': 0.0635, 'DE': 0.00, 'FL': 0.06, 'GA': 0.04,
            'HI': 0.04, 'ID': 0.06, 'IL': 0.0625, 'IN': 0.07, 'IA': 0.06,
            'KS': 0.065, 'KY': 0.06, 'LA': 0.0445, 'ME': 0.055, 'MD': 0.06,
            'MA': 0.0625, 'MI': 0.06, 'MN': 0.06875, 'MS': 0.07, 'MO': 0.04225,
            'MT': 0.00, 'NE': 0.055, 'NV': 0.0685, 'NH': 0.00, 'NJ': 0.06625,
            'NM': 0.05125, 'NY': 0.04, 'NC': 0.0475, 'ND': 0.05, 'OH': 0.0575,
            'OK': 0.045, 'OR': 0.00, 'PA': 0.06, 'RI': 0.07, 'SC': 0.06,
            'SD': 0.045, 'TN': 0.07, 'TX': 0.0625, 'UT': 0.0485, 'VT': 0.06,
            'VA': 0.043, 'WA': 0.065, 'WV': 0.06, 'WI': 0.05, 'WY': 0.04,
            'DC': 0.06, 'AS': 0.00, 'GU': 0.04, 'MP': 0.00, 'PR': 0.105, 'VI': 0.05
        }
        
        if jurisdiction not in tax_rates:
            return json.dumps({'error': f'Unsupported jurisdiction: {jurisdiction}'}, ensure_ascii=False)
        
        rate = tax_rates[jurisdiction]
        tax_amount = round(amount * rate, 2)
        total = round(amount + tax_amount, 2)
        
        result = {
            'original_amount': round(amount, 2),
            'tax_rate': rate,
            'tax_amount': tax_amount,
            'total_after_tax': total,
            'jurisdiction': jurisdiction
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "sales_tax_calculator",
    "description": "Calculate the total cost including applicable sales tax for a given monetary amount and jurisdiction (US state or territory). Returns the original amount, tax rate, tax amount, and total after tax.",
    "category": "system",
    "domain": "business",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "amount": {
            "type": "number",
            "description": "Monetary amount before tax, in USD, with up to 2 decimal places.",
            "examples": [
                29.99,
                100.0,
                5.5
            ]
        },
        "jurisdiction": {
            "type": "string",
            "description": "Two-letter US state or territory code (e.g., CA, NY, TX, PR).",
            "enum": [
                "AL",
                "AK",
                "AZ",
                "AR",
                "CA",
                "CO",
                "CT",
                "DE",
                "FL",
                "GA",
                "HI",
                "ID",
                "IL",
                "IN",
                "IA",
                "KS",
                "KY",
                "LA",
                "ME",
                "MD",
                "MA",
                "MI",
                "MN",
                "MS",
                "MO",
                "MT",
                "NE",
                "NV",
                "NH",
                "NJ",
                "NM",
                "NY",
                "NC",
                "ND",
                "OH",
                "OK",
                "OR",
                "PA",
                "RI",
                "SC",
                "SD",
                "TN",
                "TX",
                "UT",
                "VT",
                "VA",
                "WA",
                "WV",
                "WI",
                "WY",
                "DC",
                "AS",
                "GU",
                "MP",
                "PR",
                "VI"
            ],
            "examples": [
                "CA",
                "TX",
                "NY"
            ]
        }
    },
    "required": [
        "amount",
        "jurisdiction"
    ]
},
}
