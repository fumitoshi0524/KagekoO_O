"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    import random
    try:
        data = json.loads(payload)
        risk = data.get('risk_profile')
        amount = data.get('investment_amount')
        horizon = data.get('investment_horizon')
        goal = data.get('investment_goal')
        monthly = data.get('monthly_contribution', 0)

        if amount < 1000:
            return json.dumps({"error": "Minimum investment amount is 1000"})
        if monthly < 0:
            return json.dumps({"error": "Monthly contribution cannot be negative"})

        # Asset allocation models based on risk profile and horizon
        allocations = {
            'conservative': {
                'bonds': (0.60, 0.80),
                'large_cap_equities': (0.10, 0.25),
                'cash': (0.05, 0.15),
                'small_cap_equities': (0, 0.05),
                'international_equities': (0, 0.05)
            },
            'moderate': {
                'bonds': (0.30, 0.50),
                'large_cap_equities': (0.25, 0.40),
                'cash': (0.02, 0.10),
                'small_cap_equities': (0.05, 0.10),
                'international_equities': (0.05, 0.15)
            },
            'aggressive': {
                'bonds': (0.05, 0.15),
                'large_cap_equities': (0.35, 0.55),
                'cash': (0, 0.05),
                'small_cap_equities': (0.10, 0.20),
                'international_equities': (0.15, 0.25)
            }
        }

        # Adjust horizon adjustments
        horizon_multipliers = {
            'short_term': {'equity_mult': 0.7, 'bond_mult': 1.3, 'cash_mult': 2.0},
            'medium_term': {'equity_mult': 1.0, 'bond_mult': 1.0, 'cash_mult': 1.0},
            'long_term': {'equity_mult': 1.3, 'bond_mult': 0.7, 'cash_mult': 0.5}
        }

        risk_alloc = allocations[risk]
        horizon_adj = horizon_multipliers[horizon]

        # Generate semi-random allocation within ranges
        allocation = {}
        total = 0
        for asset, (low, high) in risk_alloc.items():
            base = random.uniform(low, high)
            if 'equity' in asset:
                base *= horizon_adj['equity_mult']
            elif 'bond' in asset:
                base *= horizon_adj['bond_mult']
            elif 'cash' in asset:
                base *= horizon_adj['cash_mult']
            base = max(0, min(1, base))
            allocation[asset] = base
            total += base

        # Normalize to 100%
        allocation = {k: v/total for k, v in allocation.items()}

        # Expected returns based on profile
        return_ranges = {
            'conservative': (0.03, 0.06),
            'moderate': (0.06, 0.10),
            'aggressive': (0.08, 0.15)
        }
        exp_low, exp_high = return_ranges[risk]
        expected_return = random.uniform(exp_low, exp_high)

        # Risk score (1-10, higher = riskier)
        risk_scores = {'conservative': (1, 3), 'moderate': (4, 6), 'aggressive': (7, 10)}
        risk_score = random.randint(risk_scores[risk][0], risk_scores[risk][1])

        # Goal-specific recommendations
        goal_recommendations = {
            'retirement': 'Consider tax-advantaged retirement accounts (401k, IRA). Focus on long-term growth with balanced exposure to equities and bonds.',
            'education': 'Look into education savings plans (529, ESA). Target medium-term with moderate allocation to growth assets while protecting principal near withdrawal date.',
            'wealth_building': 'Emphasize growth-oriented equities and real estate investment trusts (REITs). Rebalance annually to maintain desired risk profile.',
            'income_generation': 'Focus on dividend-paying stocks, corporate bonds, and income ETFs. Prioritize cash flow over capital appreciation.'
        }

        # Calculate future value with monthly contributions
        years = {'short_term': 2, 'medium_term': 5, 'long_term': 15}[horizon]
        monthly_rate = expected_return / 12
        n_months = years * 12
        future_value = amount * (1 + expected_return) ** years + monthly * (((1 + monthly_rate) ** n_months - 1) / monthly_rate)

        result = {
            'proposal_summary': {
                'investor_profile': risk.title(),
                'investment_amount': round(amount, 2),
                'monthly_contribution': round(monthly, 2) if monthly > 0 else None,
                'investment_horizon_years': years,
                'investment_goal': goal.replace('_', ' ').title()
            },
            'asset_allocation': {k: round(v * 100, 1) for k, v in sorted(allocation.items())},
            'expected_performance': {
                'expected_annual_return_low': round(exp_low * 100, 1),
                'expected_annual_return_high': round(exp_high * 100, 1),
                'expected_annual_return_point': round(expected_return * 100, 1),
                'projected_value_at_horizon': round(future_value, 2),
                'risk_score': risk_score,
                'volatility_category': 'Low' if risk_score <= 3 else ('Medium' if risk_score <= 6 else 'High')
            },
            'recommended_instruments': [
                {'type': 'Index_Fund', 'example': 'S&P 500 Index Fund', 'recommended_weight': round(allocation.get('large_cap_equities', 0) * 100, 1)},
                {'type': 'Bond_Fund', 'example': 'US Aggregate Bond Fund', 'recommended_weight': round(allocation.get('bonds', 0) * 100, 1)},
                {'type': 'Money_Market_Fund', 'example': 'Government Money Market Fund', 'recommended_weight': round(allocation.get('cash', 0) * 100, 1)}
            ],
            'goal_specific_advice': goal_recommendations[goal],
            'disclaimer': 'This is an automated proposal for informational purposes only. Consult a licensed financial advisor before making investment decisions.'
        }

        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "investment_proposal_generator",
    "description": "Generate a personalized investment proposal based on risk profile (conservative, moderate, aggressive), investment amount, investment horizon (short_term, medium_term, long_term), and investment goal (retirement, education, wealth_building, income_generation). Returns a structured proposal with asset allocation breakdown, expected returns range, recommended instruments, and risk assessment summary.",
    "category": "generate",
    "domain": "finance",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "risk_profile": {
            "type": "string",
            "description": "Investor risk tolerance level: conservative (low risk/low return), moderate (balanced risk/return), aggressive (high risk/high return)",
            "enum": [
                "conservative",
                "moderate",
                "aggressive"
            ]
        },
        "investment_amount": {
            "type": "number",
            "description": "Total amount to invest in base currency units (e.g., USD). Must be positive and at least 1000.",
            "minimum": 1000
        },
        "investment_horizon": {
            "type": "string",
            "description": "Duration of investment: short_term (0-2 years, typically low volatility instruments), medium_term (2-5 years, balanced growth), long_term (5+ years, growth-oriented)",
            "enum": [
                "short_term",
                "medium_term",
                "long_term"
            ]
        },
        "investment_goal": {
            "type": "string",
            "description": "Primary financial objective: retirement, education, wealth_building, income_generation (monthly/cash flow)",
            "enum": [
                "retirement",
                "education",
                "wealth_building",
                "income_generation"
            ]
        },
        "monthly_contribution": {
            "type": "number",
            "description": "Optional: Additional monthly contribution to the investment (0 or positive number). Defaults to 0 if not provided.",
            "default": 0,
            "minimum": 0
        }
    },
    "required": [
        "risk_profile",
        "investment_amount",
        "investment_horizon",
        "investment_goal"
    ]
},
}
