"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate portfolio risk contribution heatmap."""
    import json
    import numpy as np
    import yfinance as yf
    from scipy.stats import pearsonr

    try:
        data = json.loads(payload)
        tickers = data['tickers']
        weights = np.array(data['weights'])
        lookback = data.get('lookback_days', 252)
        risk_free = data.get('risk_free_rate', 0.05)
        granularity = data.get('granularity', 'daily')

        if len(tickers) != len(weights):
            return json.dumps({'error': 'tickers and weights must have same length'})

        if abs(np.sum(weights) - 1.0) > 1e-6:
            return json.dumps({'error': 'weights must sum to 1.0'})

        # Fetch historical data
        adj_close = yf.download(tickers, period=f'{lookback}d', interval='1d')['Adj Close']
        if adj_close.empty or len(adj_close.columns) < len(tickers):
            return json.dumps({'error': 'Failed to fetch price data for all tickers'})

        # Calculate returns based on granularity
        if granularity == 'daily':
            returns = adj_close.pct_change().dropna()
        elif granularity == 'weekly':
            returns = adj_close.resample('W').last().pct_change().dropna()
        elif granularity == 'monthly':
            returns = adj_close.resample('ME').last().pct_change().dropna()
        else:
            return json.dumps({'error': 'Invalid granularity'})

        # Covariance matrix and portfolio variance
        cov_matrix = returns.cov() * (252 if granularity == 'daily' else 52 if granularity == 'weekly' else 12)
        port_var = weights @ cov_matrix @ weights
        port_vol = np.sqrt(port_var)

        # Individual asset contributions
        marginal_contrib = (cov_matrix @ weights) / port_vol
        component_contrib = weights * marginal_contrib
        risk_contrib_pct = component_contrib / port_vol

        # Correlation matrix
        corr_matrix = returns.corr().values

        # Build heatmap data
        heatmap_data = []
        for i, t1 in enumerate(tickers):
            row = []
            for j, t2 in enumerate(tickers):
                risk_contrib = risk_contrib_pct[i] if j == 0 else 0  # only diagonal shows risk contrib
                cell = {
                    'asset_i': t1,
                    'asset_j': t2,
                    'value': round(risk_contrib_pct[i], 4) if i == j else round(corr_matrix[i][j], 4),
                    'type': 'risk_contribution' if i == j else 'correlation',
                    'volatility': round(np.sqrt(cov_matrix.iloc[i,i]), 4),
                    'weight': round(weights[i], 4),
                    'return': round(returns[t1].mean() * 252, 4)  # annualized return
                }
                row.append(cell)
            heatmap_data.append(row)

        # Sharpe ratio
        port_return = (returns.mean() * 252) @ weights
        sharpe = (port_return - risk_free) / port_vol

        result = {
            'tickers': tickers,
            'weights': weights.tolist(),
            'portfolio_return': round(port_return, 4),
            'portfolio_volatility': round(port_vol, 4),
            'sharpe_ratio': round(sharpe, 4),
            'heatmap': heatmap_data,
            'summary': {
                'total_risk_contrib': round(float(np.sum(risk_contrib_pct)), 4),
                'largest_risk_contributor': tickers[np.argmax(risk_contrib_pct)],
                'average_correlation': round(float(np.mean(corr_matrix[np.triu_indices_from(corr_matrix, k=1)])), 4)
            }
        }
        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        return json.dumps({'error': str(e)})


TOOL_SPEC = {
    "name": "portfolio_heatmap_generator",
    "description": "Generate a financial portfolio risk contribution heatmap visualising asset-level value, volatility, and correlation to total portfolio risk for a given list of tickers.",
    "category": "visualization",
    "domain": "finance",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "tickers": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "List of stock ticker symbols (e.g., AAPL, MSFT, TSLA) representing the assets in the portfolio."
        },
        "weights": {
            "type": "array",
            "items": {
                "type": "number"
            },
            "description": "Portfolio weight for each ticker (same order as tickers), must sum to 1.0."
        },
        "lookback_days": {
            "type": "integer",
            "description": "Optional: number of historical trading days for return calculation (default 252).",
            "default": 252
        },
        "risk_free_rate": {
            "type": "number",
            "description": "Optional: annual risk-free rate as decimal, e.g., 0.05 for 5% (default 0.05).",
            "default": 0.05
        },
        "granularity": {
            "type": "string",
            "enum": [
                "daily",
                "weekly",
                "monthly"
            ],
            "description": "Optional: return frequency for covariance calculation (default daily).",
            "default": "daily"
        }
    },
    "required": [
        "tickers",
        "weights"
    ]
},
}
