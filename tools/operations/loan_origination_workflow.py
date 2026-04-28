"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Initiate a loan application, underwrite creditworthiness, generate loan decision."""
    import json
    import math
    from datetime import datetime

    try:
        data = json.loads(payload)

        # Validate required fields
        required = ['borrower_id', 'requested_amount', 'requested_term_months', 'credit_score', 'annual_income', 'loan_purpose']
        for field in required:
            if field not in data:
                return json.dumps({'error': f'Missing required field: {field}'})

        borrower_id = str(data['borrower_id']).strip()
        if not borrower_id:
            return json.dumps({'error': 'borrower_id must be non-empty'})

        requested_amount = float(data['requested_amount'])
        if requested_amount < 1000.0 or requested_amount > 1000000.0:
            return json.dumps({'error': 'requested_amount out of range [1000, 1000000]'})

        term_months = int(data['requested_term_months'])
        if term_months < 12 or term_months > 360:
            return json.dumps({'error': 'requested_term_months out of range [12, 360]'})

        credit_score = int(data['credit_score'])
        if credit_score < 300 or credit_score > 850:
            return json.dumps({'error': 'credit_score out of range [300, 850]'})

        annual_income = float(data['annual_income'])
        if annual_income < 0:
            return json.dumps({'error': 'annual_income must be >= 0'})

        loan_purpose = data['loan_purpose']
        valid_purposes = ['debt_consolidation', 'home_improvement', 'major_purchase', 'business', 'other']
        if loan_purpose not in valid_purposes:
            return json.dumps({'error': f'loan_purpose must be one of {valid_purposes}'})

        existing_debt = float(data.get('existing_debt_total', 0.0))
        if existing_debt < 0:
            return json.dumps({'error': 'existing_debt_total must be >= 0'})

        # Underwriting logic
        # Determine risk tier based on credit score
        if credit_score >= 750:
            base_rate = 0.045
            risk_tier = 'low'
        elif credit_score >= 680:
            base_rate = 0.065
            risk_tier = 'medium'
        elif credit_score >= 600:
            base_rate = 0.095
            risk_tier = 'high'
        else:
            base_rate = 0.145
            risk_tier = 'very_high'

        # Adjust rate based on purpose
        purpose_adjust = {
            'debt_consolidation': 0.0,
            'home_improvement': -0.005,
            'major_purchase': 0.005,
            'business': 0.015,
            'other': 0.01
        }
        rate = base_rate + purpose_adjust.get(loan_purpose, 0.0)

        # Debt-to-income ratio check
        monthly_debt = existing_debt / 12.0 if existing_debt > 0 else 0.0
        monthly_income = annual_income / 12.0
        dti_ratio = monthly_debt / monthly_income if monthly_income > 0 else 999.0

        # Decision logic
        status = 'denied'
        offered_amount = 0.0
        offered_rate = 0.0
        offered_term = 0
        fees = 0.0
        reasons = []

        if dti_ratio > 0.5:
            reasons.append('debt_to_income_ratio_too_high')
        if credit_score < 600:
            reasons.append('credit_score_below_minimum')
        if requested_amount > annual_income * 2:
            reasons.append('loan_amount_exceeds_income_threshold')

        if not reasons:
            # Approve with modified terms if necessary
            status = 'approved'
            # Reduce amount if too high relative to income
            max_amount = min(requested_amount, annual_income * 1.5)
            offered_amount = round(max_amount, 2)
            # Adjust term to max 60 months for high risk
            if risk_tier in ('high', 'very_high'):
                offered_term = min(term_months, 60)
            else:
                offered_term = term_months
            offered_rate = round(rate, 4)
            # Fees: origination fee 1% for low/medium, 2% for high/very_high
            fee_rate = 0.01 if risk_tier in ('low', 'medium') else 0.02
            fees = round(offered_amount * fee_rate, 2)
        else:
            status = 'denied'
            offered_amount = 0.0
            offered_rate = 0.0
            offered_term = 0
            fees = 0.0

        # Generate reference ID
        ref_id = f"LN-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{borrower_id[-4:].upper()}"

        result = {
            'reference_id': ref_id,
            'borrower_id': borrower_id,
            'status': status,
            'offered_amount': offered_amount,
            'offered_annual_rate': offered_rate,
            'offered_term_months': offered_term,
            'origination_fees': fees,
            'risk_tier': risk_tier,
            'dti_ratio': round(dti_ratio, 4),
            'denial_reasons': reasons if status == 'denied' else [],
            'timestamp': datetime.utcnow().isoformat()
        }

        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        return json.dumps({'error': f'Unexpected error: {str(e)}'})



TOOL_SPEC = {
    "name": "loan_origination_workflow",
    "description": "Initiate a loan application, underwrite the borrower's creditworthiness, and generate a loan decision with terms (amount, rate, duration, fees). Returns a loan_decision record with status (approved, denied, pending_review), offered terms, and a reference ID for downstream processing.",
    "category": "operations",
    "domain": "finance",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "borrower_id": {
            "type": "string",
            "description": "Unique identifier for the borrower (e.g., customer account number). Must be non-empty."
        },
        "requested_amount": {
            "type": "number",
            "description": "Desired loan principal in USD. Must be between 1000.0 and 1000000.0."
        },
        "requested_term_months": {
            "type": "integer",
            "description": "Desired loan duration in months. Must be between 12 and 360."
        },
        "credit_score": {
            "type": "integer",
            "description": "Borrower's credit score (300-850). Used for underwriting decision.",
            "examples": [
                720,
                650
            ]
        },
        "annual_income": {
            "type": "number",
            "description": "Borrower's annual gross income in USD. Must be >= 0.",
            "examples": [
                75000.0,
                120000.0
            ]
        },
        "loan_purpose": {
            "type": "string",
            "enum": [
                "debt_consolidation",
                "home_improvement",
                "major_purchase",
                "business",
                "other"
            ],
            "description": "Primary purpose of the loan. Affects risk tier selection."
        },
        "existing_debt_total": {
            "type": "number",
            "description": "Optional: Total existing debt obligations (credit cards, auto loans, etc.) in USD. Defaults to 0 if omitted.",
            "examples": [
                15000.0
            ]
        }
    },
    "required": [
        "borrower_id",
        "requested_amount",
        "requested_term_months",
        "credit_score",
        "annual_income",
        "loan_purpose"
    ]
},
}
