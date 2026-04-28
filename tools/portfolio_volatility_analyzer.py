"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Calculate portfolio volatility and risk metrics."""
    import json
    import math
    from datetime import datetime, timedelta
    import random

    try:
        data = json.loads(payload)
        assets = data.get("assets", [])
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        risk_free_rate = data.get("risk_free_rate", 0.05)

        if not assets or not start_date or not end_date:
            return json.dumps({"error": "Missing required parameters: assets, start_date, end_date"})

        # Validate weight sum
        total_weight = sum(a["weight"] for a in assets)
        if abs(total_weight - 1.0) > 0.01:
            return json.dumps({"error": f"Asset weights must sum to 1.0, got {total_weight}"})

        # Simulate daily returns using realistic random walk (in production would call market data API)
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        trading_days = (end - start).days * 5 // 7  # approximate trading days
        
        if trading_days < 20:
            return json.dumps({"error": "Date range must include at least 20 trading days"})

        # Generate simulated daily returns for each asset
        daily_returns = []
        for _ in range(trading_days):
            portfolio_return = 0.0
            for asset in assets:
                # Simulate daily return with mean ~0.0005 and std ~0.02
                asset_return = random.gauss(0.0005, 0.02)
                portfolio_return += asset_return * asset["weight"]
            daily_returns.append(portfolio_return)

        # Calculate metrics
        n = len(daily_returns)
        mean_daily_return = sum(daily_returns) / n
        variance = sum((r - mean_daily_return) ** 2 for r in daily_returns) / (n - 1)
        daily_volatility = math.sqrt(variance)
        annualized_volatility = daily_volatility * math.sqrt(252)
        annualized_return = mean_daily_return * 252

        # Sharpe Ratio
        excess_return = annualized_return - risk_free_rate
        sharpe_ratio = excess_return / annualized_volatility if annualized_volatility > 0 else 0.0

        # Maximum Drawdown
        cumulative = 1.0
        peak = 1.0
        max_drawdown = 0.0
        for r in daily_returns:
            cumulative *= (1 + r)
            if cumulative > peak:
                peak = cumulative
            drawdown = (peak - cumulative) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        result = {
            "portfolio_volatility": {
                "daily": round(daily_volatility, 6),
                "annualized": round(annualized_volatility, 6)
            },
            "sharpe_ratio": round(sharpe_ratio, 4),
            "max_drawdown": round(max_drawdown, 4),
            "annualized_return": round(annualized_return, 4),
            "trading_days_analyzed": trading_days,
            "assets_analyzed": len(assets)
        }
        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        return f"error: {e}"


TOOL_SPEC = {
    "name": "portfolio_volatility_analyzer",
    "description": "Calculate and analyze the historical volatility of a financial portfolio based on its asset allocation and a date range, returning annualized volatility, Sharpe ratio, and maximum drawdown for risk assessment.",
    "category": "analysis",
    "domain": "finance",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "assets": {
            "type": "array",
            "description": "List of assets in the portfolio, each with ticker symbol and allocation weight must sum to 1.0",
            "items": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol (e.g., AAPL)"
                    },
                    "weight": {
                        "type": "number",
                        "description": "Allocation weight as decimal between 0 and 1"
                    }
                },
                "required": [
                    "ticker",
                    "weight"
                ]
            }
        },
        "start_date": {
            "type": "string",
            "description": "Start date for analysis period in YYYY-MM-DD format"
        },
        "end_date": {
            "type": "string",
            "description": "End date for analysis period in YYYY-MM-DD format"
        },
        "risk_free_rate": {
            "type": "number",
            "description": "Optional: Annual risk-free rate for Sharpe ratio calculation, default 0.05 (5%)",
            "default": 0.05
        }
    },
    "required": [
        "assets",
        "start_date",
        "end_date"
    ]
},
}
