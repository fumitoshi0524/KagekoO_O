"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Search for corporate bonds by issuer, rating, and maturity."""
    import json
    try:
        data = json.loads(payload)
        issuer = data.get('issuer_name', '').strip()
        rating = data.get('credit_rating', '').strip()
        if not issuer:
            return json.dumps({'error': 'issuer_name is required'}, ensure_ascii=False)
        if rating not in ['AAA', 'AA+', 'AA', 'AA-', 'A+', 'A', 'A-', 'BBB+', 'BBB', 'BBB-', 'BB+', 'BB', 'BB-', 'B+', 'B', 'B-', 'CCC+', 'CCC', 'CCC-', 'CC', 'C', 'D']:
            return json.dumps({'error': f'invalid credit_rating: {rating}'}, ensure_ascii=False)
        min_maturity = data.get('maturity_min_years')
        max_maturity = data.get('maturity_max_years')
        coupon_type = data.get('coupon_type')
        currency = data.get('currency')
        max_results = data.get('max_results', 20)
        if not isinstance(max_results, int) or max_results < 1:
            max_results = 20
        if max_results > 100:
            max_results = 100
        if min_maturity is not None and (not isinstance(min_maturity, int) or min_maturity < 0):
            return json.dumps({'error': 'maturity_min_years must be a non-negative integer'}, ensure_ascii=False)
        if max_maturity is not None and (not isinstance(max_maturity, int) or max_maturity < 0):
            return json.dumps({'error': 'maturity_max_years must be a non-negative integer'}, ensure_ascii=False)
        if min_maturity is not None and max_maturity is not None and min_maturity > max_maturity:
            return json.dumps({'error': 'maturity_min_years cannot exceed maturity_max_years'}, ensure_ascii=False)
        if coupon_type and coupon_type not in ['fixed', 'floating', 'zero_coupon', 'step_up']:
            return json.dumps({'error': f'invalid coupon_type: {coupon_type}'}, ensure_ascii=False)
        if currency and not (len(currency) == 3 and currency.isupper() and currency.isalpha()):
            return json.dumps({'error': 'currency must be a valid ISO 4217 code (3 uppercase letters)'}, ensure_ascii=False)
        # Simulated bond database
        bond_db = [
            {'isin': 'US1234567890', 'issuer': 'Apple Inc.', 'rating': 'AA+', 'maturity_years': 5, 'coupon_type': 'fixed', 'currency': 'USD', 'coupon_rate': 3.5, 'yield_to_maturity': 3.2, 'current_price': 101.50, 'issue_date': '2022-01-15'},
            {'isin': 'US0987654321', 'issuer': 'Microsoft Corp', 'rating': 'AAA', 'maturity_years': 10, 'coupon_type': 'fixed', 'currency': 'USD', 'coupon_rate': 2.8, 'yield_to_maturity': 2.5, 'current_price': 98.75, 'issue_date': '2020-06-01'},
            {'isin': 'US5555666677', 'issuer': 'Tesla Inc', 'rating': 'BBB-', 'maturity_years': 3, 'coupon_type': 'floating', 'currency': 'USD', 'coupon_rate': 4.2, 'yield_to_maturity': 4.5, 'current_price': 99.10, 'issue_date': '2023-03-10'},
            {'isin': 'US1111222233', 'issuer': 'JPMorgan Chase', 'rating': 'A+', 'maturity_years': 7, 'coupon_type': 'fixed', 'currency': 'USD', 'coupon_rate': 3.0, 'yield_to_maturity': 2.9, 'current_price': 100.25, 'issue_date': '2021-11-20'},
        ]
        results = []
        for bond in bond_db:
            if issuer.lower() not in bond['issuer'].lower():
                continue
            if bond['rating'] != rating:
                continue
            if min_maturity is not None and bond['maturity_years'] < min_maturity:
                continue
            if max_maturity is not None and bond['maturity_years'] > max_maturity:
                continue
            if coupon_type and bond['coupon_type'] != coupon_type:
                continue
            if currency and bond['currency'] != currency:
                continue
            results.append(bond)
            if len(results) >= max_results:
                break
        response = {
            'total_found': len(results),
            'query': {'issuer_name': issuer, 'credit_rating': rating},
            'bonds': results
        }
        return json.dumps(response, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "corporate_bond_search",
    "description": "Search for corporate bonds by issuer name, credit rating, maturity range, and coupon type, returning matched bond details including ISIN, issue date, yield to maturity, and current price.",
    "category": "search",
    "domain": "finance",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "issuer_name": {
            "type": "string",
            "description": "Full or partial name of the corporate entity that issued the bond."
        },
        "credit_rating": {
            "type": "string",
            "description": "Credit rating assigned by major agencies (e.g., S&P, Moody's, Fitch) to filter bonds by credit quality.",
            "enum": [
                "AAA",
                "AA+",
                "AA",
                "AA-",
                "A+",
                "A",
                "A-",
                "BBB+",
                "BBB",
                "BBB-",
                "BB+",
                "BB",
                "BB-",
                "B+",
                "B",
                "B-",
                "CCC+",
                "CCC",
                "CCC-",
                "CC",
                "C",
                "D"
            ]
        },
        "maturity_min_years": {
            "type": "integer",
            "description": "Optional: Minimum remaining years to maturity for the bond, must be non-negative integer.",
            "minimum": 0
        },
        "maturity_max_years": {
            "type": "integer",
            "description": "Optional: Maximum remaining years to maturity for the bond, must be greater than or equal to maturity_min_years.",
            "minimum": 0
        },
        "coupon_type": {
            "type": "string",
            "description": "Optional: Type of coupon payment structure of the bond.",
            "enum": [
                "fixed",
                "floating",
                "zero_coupon",
                "step_up"
            ]
        },
        "currency": {
            "type": "string",
            "description": "Optional: ISO 4217 three-letter currency code for the bond's denomination (e.g., USD, EUR, JPY).",
            "pattern": "^[A-Z]{3}$"
        },
        "max_results": {
            "type": "integer",
            "description": "Optional: Maximum number of bond results to return, between 1 and 100. Default is 20.",
            "minimum": 1,
            "maximum": 100
        }
    },
    "required": [
        "issuer_name",
        "credit_rating"
    ]
},
}
