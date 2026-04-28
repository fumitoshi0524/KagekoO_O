"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Calculate portfolio risk-adjusted performance metrics."""
    import json
    import math
    from statistics import mean, stdev

    try:
        data = json.loads(payload)
        returns = data.get("returns", [])
        if not returns:
            return json.dumps({"error": "returns list is required"})
        if len(returns) < 10:
            return json.dumps({"error": "At least 10 periods of returns required"})

        benchmark = data.get("benchmark_returns", None)
        if benchmark is not None and len(benchmark) != len(returns):
            return json.dumps({"error": "benchmark_returns must match length of returns"})

        risk_free_rate = data.get("risk_free_rate", 0.03)
        periods_per_year = data.get("periods_per_year", 252)
        conf_var = data.get("confidence_level_var", 0.95)

        n = len(returns)
        avg_return = mean(returns)
        std_return = stdev(returns)

        # Annualize
        annual_return = (1 + avg_return) ** periods_per_year - 1
        annual_std = std_return * math.sqrt(periods_per_year)

        # Sharpe ratio
        sharpe = (annual_return - risk_free_rate) / annual_std if annual_std > 0 else 0.0

        # Sortino ratio (downside deviation)
        downside_returns = [r for r in returns if r < 0]
        if downside_returns:
            downside_std = stdev(downside_returns) * math.sqrt(periods_per_year)
            sortino = (annual_return - risk_free_rate) / downside_std if downside_std > 0 else 0.0
        else:
            sortino = float('inf') if annual_return > risk_free_rate else 0.0

        # Max drawdown
        portfolio_value = 1000.0
        peak = portfolio_value
        max_dd = 0.0
        for r in returns:
            portfolio_value *= (1 + r)
            if portfolio_value > peak:
                peak = portfolio_value
            dd = (portfolio_value - peak) / peak
            if dd < max_dd:
                max_dd = dd

        # Value at Risk (parametric normal)
        import statistics
        z_score = {0.90: 1.2816, 0.95: 1.645, 0.99: 2.3263, 0.999: 3.0902}
        z = z_score.get(conf_var, 1.645)
        var_95 = - (avg_return - z * std_return) * 100  # in percent

        # Beta if benchmark provided
        if benchmark is not None:
            avg_bm = mean(benchmark)
            cov = sum((returns[i] - avg_return) * (benchmark[i] - avg_bm) for i in range(n)) / (n - 1)
            var_bm = stdev(benchmark) ** 2
            beta = cov / var_bm if var_bm > 0 else 0.0
        else:
            beta = None

        result = {
            "sharpe_ratio": round(sharpe, 3),
            "sortino_ratio": round(sortino, 3),
            "annualized_return": round(annual_return * 100, 2),
            "annualized_volatility": round(annual_std * 100, 2),
            "max_drawdown_pct": round(max_dd * 100, 2),
            "value_at_risk": {
                f"var_{int(conf_var*100)}_pct": round(var_95, 2),
                "method": "parametric_normal"
            }
        }
        if beta is not None:
            result["beta"] = round(beta, 3)

        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": f"Processing error: {str(e)}"})


TOOL_SPEC = {
    "name": "portfolio_risk_metrics",
    "description": "Calculate risk-adjusted performance metrics for a financial portfolio including Sharpe ratio, Sortino ratio, Value at Risk (95% and 99%), maximum drawdown, and beta relative to a market benchmark.",
    "category": "analysis",
    "domain": "finance",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "returns": {
            "type": "array",
            "items": {
                "type": "number",
                "description": "Periodic portfolio returns (e.g., daily, monthly) as decimal values (e.g., 0.01 for 1%)"
            },
            "description": "Array of historical portfolio returns in chronological order"
        },
        "benchmark_returns": {
            "type": "array",
            "items": {
                "type": "number",
                "description": "Periodic benchmark returns (e.g., S&P 500) as decimal values, matching the period of portfolio returns"
            },
            "description": "Optional: Array of benchmark returns for beta calculation; must be same length as returns"
        },
        "risk_free_rate": {
            "type": "number",
            "description": "Annual risk-free rate as decimal (e.g., 0.03 for 3%), used for Sharpe and Sortino ratios",
            "default": 0.03
        },
        "periods_per_year": {
            "type": "integer",
            "description": "Optional: Number of periods per year for annualization (e.g., 252 for daily, 12 for monthly, 1 for yearly)",
            "default": 252,
            "minimum": 1
        },
        "confidence_level_var": {
            "type": "number",
            "description": "Optional: Confidence level for Value at Risk calculation as decimal (e.g., 0.95 for 95%)",
            "default": 0.95,
            "minimum": 0.9,
            "maximum": 0.999
        }
    },
    "required": [
        "returns"
    ]
},
}
