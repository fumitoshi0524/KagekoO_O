"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    import datetime
    import random

    try:
        data = json.loads(payload)
        entity_id = data.get('entity_id')
        entity_type = data.get('entity_type')
        metrics = data.get('metrics', [])
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        aggregation = data.get('aggregation', 'daily')
        chart_type = data.get('chart_type', 'line')

        # Validate required fields
        if not all([entity_id, entity_type, metrics, start_date, end_date]):
            return json.dumps({'error': 'Missing required fields'})

        if entity_type not in ['athlete', 'team']:
            return json.dumps({'error': 'Invalid entity_type, must be athlete or team'})

        # Validate metrics against allowed set
        allowed_metrics = {'points', 'assists', 'rebounds', 'steals', 'blocks', 'turnovers', 'speed_kmh', 'accuracy_pct', 'distance_km'}
        for m in metrics:
            if m not in allowed_metrics:
                return json.dumps({'error': f'Unsupported metric: {m}'})

        # Parse dates
        try:
            start = datetime.datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            return json.dumps({'error': 'Invalid date format, use YYYY-MM-DD'})

        if start > end:
            return json.dumps({'error': 'start_date must be before end_date'})

        # Generate mock performance data (simulate real data source)
        # In production, this would query a database or API
        date_range = (end - start).days + 1
        if aggregation == 'weekly':
            date_range = max(1, date_range // 7)
        elif aggregation == 'monthly':
            date_range = max(1, date_range // 30)

        data_points = []
        current_date = start
        for i in range(date_range):
            point = {'date': current_date.strftime('%Y-%m-%d')}
            for metric in metrics:
                # Simulate realistic values based on metric type
                if metric in ['points', 'assists', 'rebounds', 'steals', 'blocks', 'turnovers']:
                    base_value = 10 if metric == 'points' else 5
                    point[metric] = round(max(0, base_value + random.gauss(0, 3)), 1)
                elif metric == 'speed_kmh':
                    point[metric] = round(max(0, 25 + random.gauss(0, 5)), 2)
                elif metric == 'accuracy_pct':
                    point[metric] = round(min(100, max(0, 70 + random.gauss(0, 10))), 1)
                elif metric == 'distance_km':
                    point[metric] = round(max(0, 10 + random.gauss(0, 3)), 2)
            data_points.append(point)
            # Increment date based on aggregation
            if aggregation == 'daily':
                current_date += datetime.timedelta(days=1)
            elif aggregation == 'weekly':
                current_date += datetime.timedelta(weeks=1)
            elif aggregation == 'monthly':
                current_date += datetime.timedelta(days=30)

        result = {
            'entity_id': entity_id,
            'entity_type': entity_type,
            'aggregation': aggregation,
            'chart_type': chart_type,
            'metrics': metrics,
            'data_points': data_points
        }
        return json.dumps(result, ensure_ascii=False)

    except json.JSONDecodeError:
        return json.dumps({'error': 'Invalid JSON payload'})
    except Exception as e:
        return json.dumps({'error': f'Internal error: {str(e)}'})


TOOL_SPEC = {
    "name": "sport_performance_dashboard",
    "description": "Generates a performance dashboard visualization for an athlete or team across multiple metrics (e.g., points, assists, rebounds, speed, accuracy) over a specified date range, returning structured data suitable for chart rendering.",
    "category": "visualization",
    "domain": "sports",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "entity_id": {
            "type": "string",
            "description": "Unique identifier for the athlete or team (e.g., player ID, team code)."
        },
        "entity_type": {
            "type": "string",
            "enum": [
                "athlete",
                "team"
            ],
            "description": "Whether the entity is an athlete or a team."
        },
        "metrics": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "List of performance metrics to include (e.g., points, assists, rebounds, speed, accuracy). Must be from allowed set: points, assists, rebounds, steals, blocks, turnovers, speed_kmh, accuracy_pct, distance_km."
        },
        "start_date": {
            "type": "string",
            "format": "date",
            "description": "Start date for the data range (inclusive) in YYYY-MM-DD format."
        },
        "end_date": {
            "type": "string",
            "format": "date",
            "description": "End date for the data range (inclusive) in YYYY-MM-DD format."
        },
        "aggregation": {
            "type": "string",
            "enum": [
                "daily",
                "weekly",
                "monthly"
            ],
            "description": "Optional: Aggregation period for data points. Default is daily."
        },
        "chart_type": {
            "type": "string",
            "enum": [
                "line",
                "bar",
                "radar"
            ],
            "description": "Optional: Preferred chart type for visualization. Default is line."
        }
    },
    "required": [
        "entity_id",
        "entity_type",
        "metrics",
        "start_date",
        "end_date"
    ]
},
}
