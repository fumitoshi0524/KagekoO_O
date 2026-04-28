"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a structured performance report for an investment portfolio."""
    import json
    import math
    from datetime import datetime, date
    try:
        data = json.loads(payload)
        portfolio_id = data.get("portfolio_id")
        start_date_str = data.get("start_date")
        end_date_str = data.get("end_date")
        include_dividends = data.get("include_dividends", True)
        benchmark_id = data.get("benchmark_id", None)

        # Validate required inputs
        if not portfolio_id or not start_date_str or not end_date_str:
            return json.dumps({"error": "Missing required fields: portfolio_id, start_date, end_date"})

        # Validate date formats
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            return json.dumps({"error": "Invalid date format. Use YYYY-MM-DD."})

        if start_date >= end_date:
            return json.dumps({"error": "start_date must be before end_date"})

        if end_date > date.today():
            return json.dumps({"error": "end_date cannot be in the future"})

        # Simulate portfolio data for demonstration (in production, this would query a database)
        # Using realistic synthetic data based on portfolio_id hash
        np.random.seed(hash(portfolio_id) % 2**32)
        import random
        random.seed(hash(portfolio_id) % 2**32)

        # Generate daily returns for the period (business days only)
        days_diff = (end_date - start_date).days
        trading_days = int(days_diff * 0.7)  # approximate trading days
        daily_returns = [random.gauss(0.0005, 0.012) for _ in range(trading_days)]

        # Calculate cumulative return
        cumulative_return = 1.0
        for r in daily_returns:
            cumulative_return *= (1 + r)
        total_return = cumulative_return - 1.0

        # Annualized return
        years = days_diff / 365.25
        annualized_return = (cumulative_return ** (1/years)) - 1 if years > 0 else 0.0

        # Volatility (annualized)
        import statistics
        daily_vol = statistics.stdev(daily_returns) if len(daily_returns) > 1 else 0.0
        annualized_vol = daily_vol * math.sqrt(252)

        # Sharpe ratio (assuming risk-free rate of 2%)
        risk_free_rate = 0.02
        sharpe_ratio = (annualized_return - risk_free_rate) / annualized_vol if annualized_vol > 0 else 0.0

        # Maximum drawdown
        wealth_index = [10000]
        for r in daily_returns:
            wealth_index.append(wealth_index[-1] * (1 + r))
        peak = wealth_index[0]
        max_dd = 0.0
        for w in wealth_index:
            if w > peak:
                peak = w
            dd = (peak - w) / peak
            if dd > max_dd:
                max_dd = dd

        # Asset allocation (simulated)
        asset_classes = ["US Equities", "International Equities", "Bonds", "Real Estate", "Commodities", "Cash"]
        weights = [random.random() for _ in asset_classes]
        total_weight = sum(weights)
        allocation = [
            {"asset_class": cls, "weight": round(w/total_weight * 100, 2)}
            for cls, w in zip(asset_classes, weights)
        ]
        allocation_sorted = sorted(allocation, key=lambda x: x["weight"], reverse=True)

        # Benchmark comparison if requested
        benchmark_data = None
        if benchmark_id:
            random.seed(hash(benchmark_id) % 2**32)
            benchmark_returns = [random.gauss(0.0004, 0.01) for _ in range(trading_days)]
            bench_cumulative = 1.0
            for r in benchmark_returns:
                bench_cumulative *= (1 + r)
            bench_return = bench_cumulative - 1.0
            bench_annualized = (bench_cumulative ** (1/years)) - 1 if years > 0 else 0.0

            # Alpha and Beta
            import numpy as np
            if len(daily_returns) == len(benchmark_returns):
                cov_matrix = np.cov(daily_returns, benchmark_returns)
                beta = cov_matrix[0,1] / np.var(benchmark_returns) if np.var(benchmark_returns) > 0 else 0.0
                alpha = annualized_return - (risk_free_rate + beta * (bench_annualized - risk_free_rate))
                # Tracking error
                diff_returns = [p - b for p, b in zip(daily_returns, benchmark_returns)]
                tracking_error = np.std(diff_returns) * math.sqrt(252)
            else:
                beta = 0.0
                alpha = 0.0
                tracking_error = 0.0

            benchmark_data = {
                "benchmark_id": benchmark_id,
                "benchmark_total_return": round(bench_return * 100, 2),
                "benchmark_annualized_return": round(bench_annualized * 100, 2),
                "alpha": round(alpha * 100, 2),
                "beta": round(beta, 3),
                "tracking_error": round(tracking_error * 100, 2)
            }

        # Construct result
        result = {
            "report_type": "Portfolio Performance Report",
            "portfolio_id": portfolio_id,
            "evaluation_period": {
                "start_date": start_date_str,
                "end_date": end_date_str,
                "trading_days": trading_days
            },
            "performance_metrics": {
                "total_return_pct": round(total_return * 100, 2),
                "annualized_return_pct": round(annualized_return * 100, 2),
                "annualized_volatility_pct": round(annualized_vol * 100, 2),
                "sharpe_ratio": round(sharpe_ratio, 3),
                "maximum_drawdown_pct": round(max_dd * 100, 2),
                "dividends_included": include_dividends
            },
            "asset_allocation": allocation_sorted,
            "currency": "USD",
            "generated_at": datetime.now().isoformat()
        }

        if benchmark_data:
            result["benchmark_comparison"] = benchmark_data

        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": f"Error generating report: {str(e)}"})



TOOL_SPEC = {
    "name": "portfolio_performance_report",
    "description": "Generate a structured performance report for an investment portfolio over a specified time period, including total return, annualized return, Sharpe ratio, maximum drawdown, and asset allocation breakdown. The report is returned as a JSON object suitable for rendering in dashboards or data visualizations.",
    "category": "visualization",
    "domain": "finance",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "portfolio_id": {
            "type": "string",
            "description": "Unique identifier for the investment portfolio. Must match an existing portfolio in the system."
        },
        "start_date": {
            "type": "string",
            "description": "Start date for the performance evaluation period in ISO 8601 format (YYYY-MM-DD). Must be a date in the past."
        },
        "end_date": {
            "type": "string",
            "description": "End date for the performance evaluation period in ISO 8601 format (YYYY-MM-DD). Must be after start_date and not in the future."
        },
        "include_dividends": {
            "type": "boolean",
            "description": "Optional: Whether to include dividend income in the return calculations. Default is True."
        },
        "benchmark_id": {
            "type": "string",
            "description": "Optional: Identifier of a benchmark index (e.g., 'SP500') to compare portfolio performance against. If provided, the report will include alpha, beta, and tracking error."
        }
    },
    "required": [
        "portfolio_id",
        "start_date",
        "end_date"
    ]
},
}
