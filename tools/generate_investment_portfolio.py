"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a diversified investment portfolio allocation."""
    import json
    import random
    
    try:
        data = json.loads(payload)
        
        # Validate required fields
        required = ["risk_tolerance", "investment_horizon_years", "target_asset_classes"]
        for field in required:
            if field not in data:
                return f'error: Missing required field \"{field}\"'
        
        risk = data["risk_tolerance"]
        horizon = data["investment_horizon_years"]
        asset_classes = data["target_asset_classes"]
        
        # Validate asset classes
        valid_assets = {"us_stocks", "international_stocks", "us_bonds", "international_bonds", "real_estate", "commodities", "cash"}
        for ac in asset_classes:
            if ac not in valid_assets:
                return f'error: Invalid asset class \"{ac}\"'
        
        # Core allocation templates based on risk profile (simplified Modern Portfolio Theory approach)
        allocations = {
            "conservative": {
                "us_stocks": 0.20,
                "international_stocks": 0.10,
                "us_bonds": 0.40,
                "international_bonds": 0.15,
                "real_estate": 0.05,
                "commodities": 0.05,
                "cash": 0.05
            },
            "moderate": {
                "us_stocks": 0.35,
                "international_stocks": 0.20,
                "us_bonds": 0.20,
                "international_bonds": 0.10,
                "real_estate": 0.07,
                "commodities": 0.05,
                "cash": 0.03
            },
            "aggressive": {
                "us_stocks": 0.50,
                "international_stocks": 0.25,
                "us_bonds": 0.10,
                "international_bonds": 0.05,
                "real_estate": 0.05,
                "commodities": 0.03,
                "cash": 0.02
            }
        }
        
        # Adjust allocation based on investment horizon (longer horizon = more stocks)
        base_alloc = allocations[risk].copy()
        if horizon >= 20:
            factor = 1.2
        elif horizon >= 15:
            factor = 1.1
        elif horizon >= 10:
            factor = 1.0
        elif horizon >= 5:
            factor = 0.9
        else:
            factor = 0.8
        
        # Apply horizon adjustment to equity components
        base_alloc["us_stocks"] = round(base_alloc["us_stocks"] * factor, 4)
        base_alloc["international_stocks"] = round(base_alloc["international_stocks"] * factor, 4)
        
        # Re-normalize to sum to 1.0
        total = sum(base_alloc.values())
        for key in base_alloc:
            base_alloc[key] = round(base_alloc[key] / total, 4)
        
        # Filter to only requested asset classes and normalize again
        filtered_alloc = {ac: base_alloc[ac] for ac in asset_classes}
        total_filtered = sum(filtered_alloc.values())
        if total_filtered <= 0:
            return f'error: Selected asset classes have zero allocation'
        for ac in filtered_alloc:
            filtered_alloc[ac] = round(filtered_alloc[ac] / total_filtered, 4)
        
        # Suggested ETFs for each asset class
        etf_suggestions = {
            "us_stocks": ["VOO", "IVV", "SPY"],
            "international_stocks": ["VXUS", "IXUS", "VEU"],
            "us_bonds": ["AGG", "BND", "GOVT"],
            "international_bonds": ["BNDX", "IGOV", "WIP"],
            "real_estate": ["VNQ", "IYR", "RWR"],
            "commodities": ["GSG", "DBC", "PDBC"],
            "cash": ["BIL", "SHV", "TBIL"]
        }
        
        # Build result
        portfolio = []
        for ac in asset_classes:
            allocation_pct = round(filtered_alloc[ac] * 100, 2)
            entry = {
                "asset_class": ac,
                "allocation_percentage": allocation_pct,
                "suggested_etfs": random.sample(etf_suggestions[ac], min(2, len(etf_suggestions[ac])))
            }
            if "initial_investment_amount" in data and data["initial_investment_amount"] > 0:
                amount = round(data["initial_investment_amount"] * filtered_alloc[ac], 2)
                entry["suggested_amount_usd"] = amount
            portfolio.append(entry)
        
        # Rebalance frequency
        rebalance = data.get("rebalance_frequency", "quarterly")
        
        result = {
            "portfolio": portfolio,
            "total_allocation_pct": round(sum(e["allocation_percentage"] for e in portfolio), 2),
            "risk_tolerance": risk,
            "investment_horizon_years": horizon,
            "rebalance_frequency": rebalance,
            "expected_annual_return_estimate_pct": round(3.0 + (5.0 if risk == "aggressive" else 3.0 if risk == "moderate" else 1.0), 2),
            "expected_volatility_estimate_pct": round(5.0 + (15.0 if risk == "aggressive" else 8.0 if risk == "moderate" else 3.0), 2),
            "disclaimer": "This is an automated portfolio suggestion for educational purposes only. Actual investment decisions should consider individual circumstances, tax implications, and professional advice."
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except json.JSONDecodeError:
        return 'error: Invalid JSON payload'
    except Exception as e:
        return f'error: {str(e)}'


TOOL_SPEC = {
    "name": "generate_investment_portfolio",
    "description": "Generate a diversified investment portfolio allocation based on user's risk tolerance, investment horizon, and target asset classes, returning a structured asset allocation plan with suggested ETFs or index funds for each category.",
    "category": "generate",
    "domain": "finance",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "risk_tolerance": {
            "type": "string",
            "description": "Investor's risk tolerance level",
            "enum": [
                "conservative",
                "moderate",
                "aggressive"
            ]
        },
        "investment_horizon_years": {
            "type": "integer",
            "description": "Investment time horizon in years",
            "minimum": 1,
            "maximum": 40
        },
        "target_asset_classes": {
            "type": "array",
            "description": "List of asset classes to include in the portfolio",
            "items": {
                "type": "string",
                "enum": [
                    "us_stocks",
                    "international_stocks",
                    "us_bonds",
                    "international_bonds",
                    "real_estate",
                    "commodities",
                    "cash"
                ]
            },
            "minItems": 1,
            "maxItems": 7
        },
        "initial_investment_amount": {
            "type": "number",
            "description": "Optional: Initial investment amount in USD to calculate suggested dollar allocations per asset class",
            "minimum": 0,
            "exclusiveMinimum": true
        },
        "rebalance_frequency": {
            "type": "string",
            "description": "Optional: How often the portfolio should be rebalanced",
            "enum": [
                "monthly",
                "quarterly",
                "annually"
            ],
            "default": "quarterly"
        }
    },
    "required": [
        "risk_tolerance",
        "investment_horizon_years",
        "target_asset_classes"
    ]
},
}
