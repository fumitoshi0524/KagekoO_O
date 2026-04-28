"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        required = ["applicant_name", "annual_income", "credit_score", "loan_amount", "loan_term_months", "employment_status", "loan_purpose"]
        for r in required:
            if r not in data:
                return json.dumps({"error": f"Missing required field: {r}"})
        
        name = data["applicant_name"]
        income = data["annual_income"]
        credit = data["credit_score"]
        amount = data["loan_amount"]
        term = data["loan_term_months"]
        status = data["employment_status"]
        purpose = data["loan_purpose"]
        existing_debt = data.get("existing_debt_monthly", 0)
        
        if income <= 0 or amount <= 0:
            return json.dumps({"error": "Income and loan amount must be positive"})
        if credit < 300 or credit > 850:
            return json.dumps({"error": "Credit score must be between 300 and 850"})
        if term not in [12,24,36,48,60,72,84,120,180,240,360]:
            return json.dumps({"error": "Invalid loan term"})
        if status not in ["employed","self-employed","unemployed","retired"]:
            return json.dumps({"error": "Invalid employment status"})
        if purpose not in ["mortgage","auto","personal","student","business","debt_consolidation"]:
            return json.dumps({"error": "Invalid loan purpose"})
        if existing_debt < 0:
            return json.dumps({"error": "Existing debt cannot be negative"})
        
        # Credit risk assessment
        credit_rating = "poor"
        if credit >= 750:
            credit_rating = "excellent"
        elif credit >= 700:
            credit_rating = "good"
        elif credit >= 650:
            credit_rating = "fair"
        elif credit >= 600:
            credit_rating = "below_average"
        
        # Calculate debt-to-income ratio (DTI)
        monthly_income = income / 12
        total_monthly_debt = existing_debt
        # Estimate monthly loan payment (simple interest approximation)
        interest_rate = 0.02  # base 2%
        if credit_rating == "excellent":
            interest_rate = 0.03
        elif credit_rating == "good":
            interest_rate = 0.05
        elif credit_rating == "fair":
            interest_rate = 0.08
        elif credit_rating == "below_average":
            interest_rate = 0.12
        else:
            interest_rate = 0.18
        
        monthly_rate = interest_rate / 12
        if monthly_rate == 0:
            monthly_payment = amount / term
        else:
            monthly_payment = amount * (monthly_rate * (1 + monthly_rate)**term) / ((1 + monthly_rate)**term - 1)
        total_monthly_debt += monthly_payment
        dti_ratio = total_monthly_debt / monthly_income if monthly_income > 0 else float('inf')
        
        risk_factors = []
        approved = True
        rejection_reasons = []
        
        # Employment check
        if status == "unemployed":
            rejection_reasons.append("Unemployed applicants do not qualify")
            approved = False
        
        # DTI check
        if dti_ratio > 0.50:
            rejection_reasons.append(f"Debt-to-income ratio {dti_ratio:.2%} exceeds 50%")
            approved = False
        elif dti_ratio > 0.43:
            risk_factors.append(f"High DTI ratio ({dti_ratio:.2%})")
        
        # Credit score check
        if credit < 600:
            rejection_reasons.append("Credit score below minimum 600")
            approved = False
        elif credit < 650:
            risk_factors.append("Below average credit score")
        
        # Loan amount relative to income
        loan_to_income = amount / income if income > 0 else float('inf')
        if loan_to_income > 5:
            rejection_reasons.append(f"Loan amount exceeds 5x annual income")
            approved = False
        elif loan_to_income > 3:
            risk_factors.append(f"Loan amount is {loan_to_income:.1f}x annual income")
        
        # Purpose-specific checks
        if purpose == "mortgage" and loan_to_income > 4:
            rejection_reasons.append("Mortgage amount exceeds 4x annual income")
            approved = False
        if purpose == "student" and status == "retired":
            rejection_reasons.append("Student loans not available for retired applicants")
            approved = False
        
        if approved:
            # Calculate maximum amount
            max_affordable = (monthly_income * 0.43 - existing_debt) * ((1 + monthly_rate)**term - 1) / (monthly_rate * (1 + monthly_rate)**term) if monthly_rate > 0 else (monthly_income * 0.43 - existing_debt) * term
            max_affordable = max(0, max_affordable)
            
            result = {
                "status": "approved",
                "applicant": name,
                "credit_rating": credit_rating,
                "dti_ratio": round(dti_ratio, 4),
                "monthly_payment": round(monthly_payment, 2),
                "interest_rate": round(interest_rate, 4),
                "max_affordable_amount": round(max_affordable, 2),
                "approved_amount": min(amount, max_affordable),
                "risk_factors": risk_factors,
                "loan_terms": {
                    "amount": round(min(amount, max_affordable), 2),
                    "term_months": term,
                    "interest_rate": round(interest_rate, 4),
                    "monthly_payment": round(monthly_payment, 2)
                }
            }
        else:
            result = {
                "status": "rejected",
                "applicant": name,
                "credit_rating": credit_rating,
                "dti_ratio": round(dti_ratio, 4),
                "rejection_reasons": rejection_reasons,
                "suggestions": ["Improve credit score", "Reduce existing debt", "Increase down payment", "Choose a shorter loan term"]
            }
        
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


TOOL_SPEC = {
    "name": "process_loan_application",
    "description": "Process a loan application by validating applicant financial data, performing credit risk assessment, calculating affordability ratios, and returning an approval decision with loan terms or rejection reasons.",
    "category": "operations",
    "domain": "finance",
    "risk_level": "high",
    "schema": {
    "type": "object",
    "properties": {
        "applicant_name": {
            "type": "string",
            "description": "Name of the loan applicant"
        },
        "annual_income": {
            "type": "number",
            "description": "Annual pre-tax income in USD, must be > 0"
        },
        "credit_score": {
            "type": "integer",
            "description": "Credit score between 300 and 850"
        },
        "loan_amount": {
            "type": "number",
            "description": "Requested loan amount in USD, must be > 0"
        },
        "loan_term_months": {
            "type": "integer",
            "description": "Duration of loan in months (12, 24, 36, 48, 60, 72, 84, 120, 180, 240, 360)"
        },
        "existing_debt_monthly": {
            "type": "number",
            "description": "Optional: Total existing monthly debt payments in USD, default 0"
        },
        "employment_status": {
            "type": "string",
            "description": "Employment status of the applicant",
            "enum": [
                "employed",
                "self-employed",
                "unemployed",
                "retired"
            ]
        },
        "loan_purpose": {
            "type": "string",
            "description": "Purpose of the loan",
            "enum": [
                "mortgage",
                "auto",
                "personal",
                "student",
                "business",
                "debt_consolidation"
            ]
        }
    },
    "required": [
        "applicant_name",
        "annual_income",
        "credit_score",
        "loan_amount",
        "loan_term_months",
        "employment_status",
        "loan_purpose"
    ]
},
}
