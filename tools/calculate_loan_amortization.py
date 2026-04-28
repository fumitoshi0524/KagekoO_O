"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a complete loan amortization schedule."""
    import json
    from datetime import datetime, timedelta
    import math

    try:
        data = json.loads(payload)

        loan_amount = data.get('loan_amount')
        annual_rate = data.get('annual_interest_rate')
        term_years = data.get('loan_term_years')
        payments_per_year = data.get('payments_per_year', 12)
        start_date_str = data.get('start_date')

        # Validate required inputs
        if loan_amount is None or annual_rate is None or term_years is None:
            return json.dumps({'error': 'Missing required parameters: loan_amount, annual_interest_rate, loan_term_years'})

        # Type and range checks
        if not isinstance(loan_amount, (int, float)) or loan_amount <= 0:
            return json.dumps({'error': 'loan_amount must be a positive number'})
        if not isinstance(annual_rate, (int, float)) or annual_rate < 0 or annual_rate > 100:
            return json.dumps({'error': 'annual_interest_rate must be between 0 and 100'})
        if not isinstance(term_years, int) or term_years < 1 or term_years > 50:
            return json.dumps({'error': 'loan_term_years must be an integer between 1 and 50'})
        if not isinstance(payments_per_year, int) or payments_per_year < 1 or payments_per_year > 52:
            return json.dumps({'error': 'payments_per_year must be an integer between 1 and 52'})

        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            except ValueError:
                return json.dumps({'error': 'start_date must be in YYYY-MM-DD format'})
        else:
            start_date = datetime.now()

        # Calculate payment details
        r = (annual_rate / 100.0) / payments_per_year
        n = term_years * payments_per_year

        if r == 0:
            payment = loan_amount / n
        else:
            payment = loan_amount * (r * (1 + r) ** n) / ((1 + r) ** n - 1)

        schedule = []
        balance = loan_amount
        total_interest = 0.0

        for period in range(1, n + 1):
            interest = balance * r
            principal = payment - interest
            if balance < principal:
                principal = balance
                payment = principal + interest
            balance -= principal
            total_interest += interest

            if start_date_str:
                days_per_period = 365.0 / payments_per_year
                due_date = start_date + timedelta(days=int(days_per_period * period))
                due_date_str = due_date.strftime('%Y-%m-%d')
            else:
                due_date_str = None

            schedule.append({
                'period': period,
                'payment': round(payment, 2),
                'principal': round(principal, 2),
                'interest': round(interest, 2),
                'balance': round(balance, 2),
                'due_date': due_date_str
            })

            # Avoid floating point negative balance
            if balance < 0.01:
                balance = 0.0
                break

        result = {
            'schedule': schedule,
            'total_principal': round(loan_amount, 2),
            'total_interest_paid': round(total_interest, 2),
            'total_payments': round(payment * len(schedule), 2),
            'payment_per_period': round(payment, 2),
            'number_of_payments': len(schedule)
        }

        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "calculate_loan_amortization",
    "description": "Generate a complete loan amortization schedule showing periodic payment amounts, interest and principal breakdown, and total interest paid over the life of the loan for a fixed-rate amortizing loan.",
    "category": "operations",
    "domain": "finance",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "loan_amount": {
            "type": "number",
            "description": "The principal loan amount in the loan's currency (must be positive)."
        },
        "annual_interest_rate": {
            "type": "number",
            "description": "The annual nominal interest rate as a percentage (e.g., 5.5 for 5.5%). Must be between 0 and 100."
        },
        "loan_term_years": {
            "type": "integer",
            "description": "The total loan term in whole years (e.g., 30 for a 30-year mortgage). Must be between 1 and 50."
        },
        "payments_per_year": {
            "type": "integer",
            "description": "Number of payment periods per year (e.g., 12 for monthly, 26 for bi-weekly). Default is 12."
        },
        "start_date": {
            "type": "string",
            "description": "Optional: The start date of the loan in YYYY-MM-DD format. If provided, each schedule row will include a due date. Default is current date."
        }
    },
    "required": [
        "loan_amount",
        "annual_interest_rate",
        "loan_term_years"
    ]
},
}
