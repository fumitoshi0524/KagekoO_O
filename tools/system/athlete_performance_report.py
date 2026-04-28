"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a structured performance report for an athlete."""
    import json
    from datetime import datetime
    try:
        data = json.loads(payload)
        athlete_id = data['athlete_id']
        start_date = data['start_date']
        end_date = data['end_date']
        include_logs = data.get('include_logs', False)

        # Validate date format
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        if end < start:
            return json.dumps({'error': 'end_date must be after or equal to start_date'}, ensure_ascii=False)

        # Simulate data retrieval (in production, query a database)
        # For demonstration, we generate synthetic daily logs for the period.
        from collections import defaultdict
        import random
        random.seed(hash(athlete_id) % 2**32)

        daily_logs = []
        total_events = 0
        total_score = 0
        best_score = None
        worst_score = None
        current = start
        while current <= end:
            date_str = current.strftime('%Y-%m-%d')
            # Simulate 0-3 events per day
            num_events = random.randint(0, 3)
            for _ in range(num_events):
                score = round(random.uniform(50, 100), 2)
                total_events += 1
                total_score += score
                if best_score is None or score > best_score:
                    best_score = score
                if worst_score is None or score < worst_score:
                    worst_score = score
                daily_logs.append({
                    'date': date_str,
                    'event_type': random.choice(['running', 'swimming', 'cycling', 'strength']),
                    'performance_score': score
                })
            current += __import__('datetime').timedelta(days=1)

        # Sort logs by date
        daily_logs.sort(key=lambda x: x['date'])

        avg_score = round(total_score / total_events, 2) if total_events > 0 else 0.0

        result = {
            'athlete_id': athlete_id,
            'report_period': {'start_date': start_date, 'end_date': end_date},
            'summary': {
                'total_events': total_events,
                'average_performance_score': avg_score,
                'best_score': best_score,
                'worst_score': worst_score
            }
        }

        if include_logs:
            result['daily_logs'] = daily_logs

        return json.dumps(result, ensure_ascii=False)

    except KeyError as e:
        return json.dumps({'error': f'Missing required field: {e}'}, ensure_ascii=False)
    except ValueError as e:
        return json.dumps({'error': f'Invalid date format: {e}'}, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "athlete_performance_report",
    "description": "Generate a structured performance report for an athlete over a specified time period, aggregating training logs and event results. Returns a JSON object with summary statistics (average performance score, total events, best/worst score) and detailed daily logs for audit and coaching review.",
    "category": "system",
    "domain": "sports",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "athlete_id": {
            "type": "string",
            "description": "Unique identifier of the athlete (e.g., UUID or user ID)."
        },
        "start_date": {
            "type": "string",
            "description": "Start date of the reporting period in YYYY-MM-DD format.",
            "format": "date"
        },
        "end_date": {
            "type": "string",
            "description": "End date of the reporting period in YYYY-MM-DD format. Must be after start_date.",
            "format": "date"
        },
        "include_logs": {
            "type": "boolean",
            "description": "Optional: If True, include daily training and event logs in the report. Defaults to False.",
            "default": False
        }
    },
    "required": [
        "athlete_id",
        "start_date",
        "end_date"
    ]
},
}
