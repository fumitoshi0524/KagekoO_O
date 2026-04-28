"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a portfolio allocation pie chart showing the distribution of investments across asset classes."""
    import json
    import random

    try:
        data = json.loads(payload)
        portfolio_id = data.get("portfolio_id")
        if not portfolio_id:
            return json.dumps({"error": "portfolio_id is required"}, ensure_ascii=False)
        account_number = data.get("account_number", "")
        chart_type = data.get("chart_type", "pie")
        include_cash = data.get("include_cash", True)

        # Simulate portfolio data retrieval - in real system this would query a database
        # Generate deterministic but varied allocation based on portfolio_id hash
        random.seed(hash(portfolio_id) % (2**31))

        asset_classes = ["Stocks", "Bonds", "Real Estate", "Commodities"]
        if include_cash:
            asset_classes.append("Cash & Equivalents")

        percentages = [random.uniform(5, 40) for _ in asset_classes]
        total = sum(percentages)
        percentages = [round(p / total * 100, 1) for p in percentages]

        allocation = []
        for i, asset_class in enumerate(asset_classes):
            allocation.append({
                "asset_class": asset_class,
                "percentage": percentages[i],
                "amount_usd": round(percentages[i] * 10000 / 100, 2)  # sample total of $10k
            })

        # Sort by percentage descending for better visualization
        allocation.sort(key=lambda x: x["percentage"], reverse=True)

        result = {
            "portfolio_id": portfolio_id,
            "account_number": account_number if account_number else None,
            "chart_type": chart_type,
            "total_value_usd": 10000.00,  # sample total
            "allocation": allocation,
            "chart_data": {
                "labels": [a["asset_class"] for a in allocation],
                "datasets": [{
                    "label": "Portfolio Allocation",
                    "data": [a["percentage"] for a in allocation],
                    "backgroundColor": [
                        "rgba(54, 162, 235, 0.7)",
                        "rgba(255, 99, 132, 0.7)",
                        "rgba(255, 206, 86, 0.7)",
                        "rgba(75, 192, 192, 0.7)",
                        "rgba(153, 102, 255, 0.7)"
                    ]
                }]
            },
            "status": "success"
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Failed to generate chart: {str(e)}"}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "portfolio_balance_chart",
    "description": "Generate a portfolio allocation pie chart showing the distribution of investments across asset classes (stocks, bonds, cash, real estate) for a given portfolio ID or account number, used for visualizing diversification and concentration risk in financial portfolios.",
    "category": "visualization",
    "domain": "finance",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "portfolio_id": {
            "type": "string",
            "description": "Unique identifier for the investment portfolio (alphanumeric, max 20 characters)"
        },
        "account_number": {
            "type": "string",
            "description": "Optional: account number associated with the portfolio, used as alternative lookup"
        },
        "chart_type": {
            "type": "string",
            "description": "Type of chart to generate (default is 'pie', alternative 'doughnut')",
            "enum": [
                "pie",
                "doughnut"
            ]
        },
        "include_cash": {
            "type": "boolean",
            "description": "Optional: whether to include cash and cash equivalents as a separate asset class (default True)"
        }
    },
    "required": [
        "portfolio_id"
    ]
},
}
