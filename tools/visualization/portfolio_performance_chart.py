"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generates a portfolio performance line chart as a base64 PNG image."""
    import json
    try:
        data = json.loads(payload)
        portfolio_id = data.get('portfolio_id')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        benchmark = data.get('benchmark', 'none')
        chart_width = data.get('chart_width', 800)
        chart_height = data.get('chart_height', 600)

        if not portfolio_id or not start_date or not end_date:
            return json.dumps({'error': 'Missing required parameters: portfolio_id, start_date, end_date'})

        # Simulate fetching portfolio performance data (in production, this would be from a database/API)
        import random
        from datetime import datetime, timedelta

        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        num_days = (end_dt - start_dt).days

        if num_days < 1:
            return json.dumps({'error': 'end_date must be after start_date'})

        # Generate mock portfolio returns (cumulative percentage) based on random walk
        random.seed(hash(portfolio_id) % (2**31))
        portfolio_returns = [random.gauss(0.0003, 0.01) for _ in range(num_days)]
        portfolio_cumulative = [0.0]
        for r in portfolio_returns:
            portfolio_cumulative.append(portfolio_cumulative[-1] + r)

        # Generate mock benchmark returns if specified
        benchmark_cumulative = None
        if benchmark != 'none':
            random.seed(hash(benchmark) % (2**31))
            benchmark_returns = [random.gauss(0.0002, 0.008) for _ in range(num_days)]
            benchmark_cumulative = [0.0]
            for r in benchmark_returns:
                benchmark_cumulative.append(benchmark_cumulative[-1] + r)

        # Generate chart using matplotlib
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        import base64
        from io import BytesIO

        # Create date labels
        date_labels = [start_dt + timedelta(days=i) for i in range(num_days + 1)]

        # Plot chart
        fig, ax = plt.subplots(figsize=(chart_width/100, chart_height/100), dpi=100)
        ax.plot(date_labels, [p * 100 for p in portfolio_cumulative], label=f'Portfolio {portfolio_id}', color='#1f77b4', linewidth=2)
        if benchmark_cumulative:
            ax.plot(date_labels, [b * 100 for b in benchmark_cumulative], label=benchmark, color='#ff7f0e', linewidth=2, linestyle='--')

        ax.set_title('Portfolio Performance Comparison', fontsize=14, fontweight='bold')
        ax.set_xlabel('Date')
        ax.set_ylabel('Cumulative Return (%)')
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        fig.autofmt_xdate(rotation=45)
        plt.tight_layout()

        # Convert plot to base64 PNG
        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        plt.close(fig)
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode('utf-8')

        result = {
            'status': 'success',
            'chart_title': f'Portfolio {portfolio_id} vs {benchmark}' if benchmark != 'none' else f'Portfolio {portfolio_id} Performance',
            'image_base64': image_base64,
            'image_format': 'png',
            'chart_dimensions': {'width': chart_width, 'height': chart_height},
            'metadata': {
                'portfolio_id': portfolio_id,
                'start_date': start_date,
                'end_date': end_date,
                'benchmark': benchmark if benchmark != 'none' else None,
                'total_days_analyzed': num_days,
                'portfolio_final_return_pct': round(portfolio_cumulative[-1] * 100, 2),
                'benchmark_final_return_pct': round(benchmark_cumulative[-1] * 100, 2) if benchmark_cumulative else None
            }
        }
        return json.dumps(result, ensure_ascii=False, default=str)

    except ValueError as e:
        return json.dumps({'error': f'Invalid date format: {str(e)}'})
    except Exception as e:
        return json.dumps({'error': f'An unexpected error occurred: {str(e)}'})


TOOL_SPEC = {
    "name": "portfolio_performance_chart",
    "description": "Generates a line chart visualization of portfolio performance over time, comparing actual returns against a benchmark index, and returns the chart as a base64-encoded PNG image for embedding in reports or dashboards.",
    "category": "visualization",
    "domain": "finance",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "portfolio_id": {
            "type": "string",
            "description": "Unique identifier for the investment portfolio to analyze."
        },
        "start_date": {
            "type": "string",
            "description": "Start date for the performance period in YYYY-MM-DD format."
        },
        "end_date": {
            "type": "string",
            "description": "End date for the performance period in YYYY-MM-DD format."
        },
        "benchmark": {
            "type": "string",
            "description": "Optional: Name of a benchmark index to compare against (e.g., S&P 500, FTSE 100). If not provided, only portfolio returns are shown.",
            "enum": [
                "S&P 500",
                "FTSE 100",
                "Nikkei 225",
                "NASDAQ Composite",
                "Dow Jones Industrial Average",
                "none"
            ]
        },
        "chart_width": {
            "type": "integer",
            "description": "Optional: Width of the output chart image in pixels. Default is 800.",
            "minimum": 400,
            "maximum": 1600
        },
        "chart_height": {
            "type": "integer",
            "description": "Optional: Height of the output chart image in pixels. Default is 600.",
            "minimum": 300,
            "maximum": 1200
        }
    },
    "required": [
        "portfolio_id",
        "start_date",
        "end_date"
    ]
},
}
