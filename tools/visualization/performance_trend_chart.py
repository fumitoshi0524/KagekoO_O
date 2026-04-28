"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generates a performance trend chart for an athlete."""
    import json
    import base64
    import io
    from datetime import datetime, timedelta
    import random
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    try:
        data = json.loads(payload)

        athlete_id = data.get('athlete_id')
        sport = data.get('sport')
        metric = data.get('metric')
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        chart_type = data.get('chart_type', 'line')

        if not all([athlete_id, sport, metric, start_date_str, end_date_str]):
            return json.dumps({'error': 'Missing required fields: athlete_id, sport, metric, start_date, end_date'})

        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        num_days = (end_date - start_date).days

        if num_days < 0:
            return json.dumps({'error': 'start_date must be before end_date'})

        # Generate synthetic performance data for demo
        random.seed(hash(athlete_id + sport + metric) % (2**31))
        dates = [start_date + timedelta(days=i) for i in range(num_days + 1)]
        base_value = 70 + random.uniform(-10, 10)
        values = []
        for i in range(len(dates)):
            trend = (i / max(1, len(dates))) * random.uniform(5, 15)
            noise = random.gauss(0, 5)
            val = base_value + trend + noise
            val = max(0, min(100, val))  # Clamp between 0 and 100
            values.append(round(val, 2))

        # Compute summary statistics
        avg_val = sum(values) / len(values)
        max_val = max(values)
        min_val = min(values)
        improvement = values[-1] - values[0] if len(values) > 1 else 0

        # Generate chart
        plt.figure(figsize=(10, 6))
        date_labels = [d.strftime('%m/%d') for d in dates]

        if chart_type == 'line':
            plt.plot(date_labels, values, marker='o', linestyle='-', color='#1f77b4', linewidth=2)
        elif chart_type == 'bar':
            plt.bar(date_labels, values, color='#1f77b4', alpha=0.7)
        elif chart_type == 'scatter':
            plt.scatter(date_labels, values, color='#1f77b4', alpha=0.7)
            plt.plot(date_labels, values, linestyle='--', color='gray', alpha=0.3)

        plt.title(f'{metric.capitalize()} Trend for Athlete {athlete_id[:8]}... in {sport.capitalize()}', fontsize=14)
        plt.xlabel('Date', fontsize=12)
        plt.ylabel(f'{metric.capitalize()} Score (0-100)', fontsize=12)
        plt.xticks(rotation=45)
        plt.grid(True, alpha=0.3)

        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        plt.close()
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')

        result = {
            'chart_base64': img_base64,
            'summary': {
                'athlete_id': athlete_id,
                'sport': sport,
                'metric': metric,
                'period': f'{start_date_str} to {end_date_str}',
                'data_points': len(values),
                'average': round(avg_val, 2),
                'maximum': round(max_val, 2),
                'minimum': round(min_val, 2),
                'improvement': round(improvement, 2),
                'trend': 'improving' if improvement > 2 else ('declining' if improvement < -2 else 'stable')
            }
        }
        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "performance_trend_chart",
    "description": "Generates a visualization of an athlete's performance trends over a specified time period, including metrics like speed, endurance, and accuracy, and returns a base64-encoded PNG chart along with summary statistics for coaching analysis.",
    "category": "visualization",
    "domain": "sports",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "athlete_id": {
            "type": "string",
            "description": "Unique identifier for the athlete (e.g., UUID or player ID)."
        },
        "sport": {
            "type": "string",
            "description": "Sport discipline (e.g., sprinting, swimming, basketball).",
            "enum": [
                "sprinting",
                "swimming",
                "basketball",
                "soccer",
                "tennis",
                "cycling"
            ]
        },
        "metric": {
            "type": "string",
            "description": "Performance metric to visualize (e.g., speed, endurance, accuracy).",
            "enum": [
                "speed",
                "endurance",
                "accuracy",
                "strength",
                "agility"
            ]
        },
        "start_date": {
            "type": "string",
            "description": "Start date for trend analysis in YYYY-MM-DD format."
        },
        "end_date": {
            "type": "string",
            "description": "End date for trend analysis in YYYY-MM-DD format."
        },
        "chart_type": {
            "type": "string",
            "description": "Optional: Type of chart to generate (default is line).",
            "enum": [
                "line",
                "bar",
                "scatter"
            ],
            "default": "line"
        }
    },
    "required": [
        "athlete_id",
        "sport",
        "metric",
        "start_date",
        "end_date"
    ]
},
}
