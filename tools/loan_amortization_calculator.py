"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Calculate the complete loan amortization schedule."""
    import json
    from math import pow

    try:
        data = json.loads(payload)
        loan_amount = float(data.get('loan_amount', 0))
        annual_rate = float(data.get('annual_interest_rate', 0))
        term_months = int(data.get('loan_term_months', 0))
        extra_payment = float(data.get('extra_monthly_payment', 0))

        if loan_amount <= 0:
            return json.dumps({'error': 'Loan amount must be greater than 0.'})
        if annual_rate <= 0:
            return json.dumps({'error': 'Annual interest rate must be greater than 0.'})
        if term_months <= 0 or term_months > 600:
            return json.dumps({'error': 'Loan term must be between 1 and 600 months.'})
        if extra_payment < 0:
            return json.dumps({'error': 'Extra monthly payment cannot be negative.'})

        monthly_rate = (annual_rate / 100) / 12
        # Standard monthly payment formula: P * r * (1+r)^n / ((1+r)^n - 1)
        if monthly_rate > 0:
            monthly_payment = loan_amount * monthly_rate * pow(1 + monthly_rate, term_months) / (pow(1 + monthly_rate, term_months) - 1)
        else:
            # 0% interest case
            monthly_payment = loan_amount / term_months

        total_interest = 0.0
        remaining_balance = loan_amount
        schedule = []
        current_month = 0

        while remaining_balance > 0.01 and current_month < term_months:
            current_month += 1
            interest_payment = remaining_balance * monthly_rate if monthly_rate > 0 else 0.0
            principal_payment_base = monthly_payment - interest_payment
            
            total_principal_payment = principal_payment_base + extra_payment
            if total_principal_payment > remaining_balance:
                total_principal_payment = remaining_balance
                interest_payment = 0.0
                monthly_payment = remaining_balance + interest_payment

            remaining_balance -= total_principal_payment
            if remaining_balance < 0:
                remaining_balance = 0.0

            total_interest += interest_payment

            schedule.append({
                'month': current_month,
                'payment': round(monthly_payment + extra_payment, 2) if extra_payment > 0 else round(monthly_payment, 2),
                'principal': round(total_principal_payment, 2),
                'interest': round(interest_payment, 2),
                'remaining_balance': round(remaining_balance, 2)
            })

            if remaining_balance < 0.01:
                break

        result = {
            'loan_amount': round(loan_amount, 2),
            'annual_interest_rate': annual_rate,
            'loan_term_months': term_months,
            'monthly_payment': round(monthly_payment, 2),
            'extra_monthly_payment': round(extra_payment, 2),
            'total_interest': round(total_interest, 2),
            'total_paid': round(loan_amount + total_interest, 2),
            'actual_payoff_month': current_month,
            'amortization_schedule': schedule
        }

        return json.dumps(result, ensure_ascii=False)

    except json.JSONDecodeError:
        return json.dumps({'error': 'Invalid JSON payload.'})
    except (ValueError, TypeError) as e:
        return json.dumps({'error': f'Invalid input: {str(e)}'})
    except Exception as e:
        return json.dumps({'error': f'Calculation error: {str(e)}'})


TOOL_SPEC = {
    "name": "loan_amortization_calculator",
    "description": "Calculate the complete loan amortization schedule (principal, interest, monthly payment, total interest, and payoff date) for a fixed-rate loan, enabling borrowers to visualize payment breakdown over the loan term.",
    "category": "operations",
    "domain": "finance",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "loan_amount": {
            "type": "number",
            "description": "The total principal amount of the loan in the base currency (e.g., USD). Must be greater than 0.",
            "examples": [
                300000,
                15000,
                50000
            ]
        },
        "annual_interest_rate": {
            "type": "number",
            "description": "The annual nominal interest rate as a percentage (e.g., 6.5 for 6.5%). Must be greater than 0.",
            "examples": [
                6.5,
                3.2,
                8.99
            ]
        },
        "loan_term_months": {
            "type": "integer",
            "description": "The total duration of the loan in months. Must be a positive integer between 1 and 600.",
            "examples": [
                360,
                60,
                48
            ]
        },
        "extra_monthly_payment": {
            "type": "number",
            "description": "Optional: An additional fixed amount paid each month toward the principal, reducing total interest and shortening the loan term. Default is 0.",
            "examples": [
                200,
                500,
                0
            ]
        }
    },
    "required": [
        "loan_amount",
        "annual_interest_rate",
        "loan_term_months"
    ]
},
}
