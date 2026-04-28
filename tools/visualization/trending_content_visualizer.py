"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    import random
    from datetime import datetime, timedelta
    try:
        data = json.loads(payload)
        content_type = data.get('content_type')
        content_identifier = data.get('content_identifier')
        platform = data.get('platform')
        metric = data.get('metric')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        interval = data.get('interval', 'weekly')
        chart_type = data.get('chart_type', 'line')
        
        if not all([content_type, content_identifier, platform, metric, start_date, end_date]):
            return json.dumps({'error': 'Missing required fields: content_type, content_identifier, platform, metric, start_date, end_date'})
        
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            return json.dumps({'error': 'Invalid date format. Use YYYY-MM-DD.'})
        
        if start >= end:
            return json.dumps({'error': 'start_date must be before end_date.'})
        
        if interval not in ['daily', 'weekly', 'monthly']:
            return json.dumps({'error': 'Invalid interval. Must be daily, weekly, or monthly.'})
        if chart_type not in ['line', 'bar', 'area']:
            return json.dumps({'error': 'Invalid chart_type. Must be line, bar, or area.'})
        if metric not in ['views', 'likes', 'shares', 'comments']:
            return json.dumps({'error': 'Invalid metric. Must be views, likes, shares, or comments.'})
        
        # Simulate realistic trend data with seasonal patterns and random noise
        data_points = []
        current = start
        base_value = random.randint(1000, 100000)
        while current <= end:
            days_diff = (current - start).days
            # Add a sine wave for trend pattern (popularity peak mid-range)
            season = (days_diff / 365.0) * 6.283
            trend_factor = 1.0 + 0.3 * (season * 0.5) ** 2
            # Add weekend boost for entertainment content
            weekend_boost = 1.2 if current.weekday() >= 5 else 1.0
            value = int(base_value * (1 + 0.01 * days_diff) * trend_factor * weekend_boost * random.uniform(0.85, 1.15))
            data_points.append({
                'date': current.strftime('%Y-%m-%d'),
                'value': value
            })
            if interval == 'daily':
                current += timedelta(days=1)
            elif interval == 'weekly':
                current += timedelta(weeks=1)
            else:
                current += timedelta(days=30)
        
        result = {
            'chart_type': chart_type,
            'title': f"{metric.capitalize()} Trend for {content_type}: {content_identifier} on {platform}",
            'x_axis': {'label': 'Date', 'unit': interval},
            'y_axis': {'label': metric.capitalize()},
            'data': data_points,
            'summary': {
                'total_' + metric: sum(p['value'] for p in data_points),
                'peak_value': max(p['value'] for p in data_points),
                'average_value': int(sum(p['value'] for p in data_points) / len(data_points))
            },
            'metadata': {
                'content_type': content_type,
                'content_identifier': content_identifier,
                'platform': platform,
                'period': f"{start_date} to {end_date}",
                'generated_at': datetime.utcnow().isoformat() + 'Z'
            }
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {str(e)}'


TOOL_SPEC = {
    "name": "trending_content_visualizer",
    "description": "Generates a visual trend chart showing popularity metrics (views, likes, shares, or comments) over time for specified entertainment content (movies, TV shows, music tracks, or games) across defined platforms and date ranges.",
    "category": "visualization",
    "domain": "entertainment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "content_type": {
            "type": "string",
            "enum": [
                "movie",
                "tv_show",
                "music_track",
                "game"
            ],
            "description": "The type of entertainment content to analyze for trending data."
        },
        "content_identifier": {
            "type": "string",
            "description": "Unique identifier or title slug for the content (e.g., movie IMDb ID, track ISRC, game title)."
        },
        "platform": {
            "type": "string",
            "enum": [
                "netflix",
                "spotify",
                "youtube",
                "twitch",
                "steam"
            ],
            "description": "The entertainment platform from which to retrieve popularity metrics."
        },
        "metric": {
            "type": "string",
            "enum": [
                "views",
                "likes",
                "shares",
                "comments"
            ],
            "description": "The specific popularity metric to visualize across the time range."
        },
        "start_date": {
            "type": "string",
            "format": "date",
            "description": "Start date for the trend analysis period in YYYY-MM-DD format."
        },
        "end_date": {
            "type": "string",
            "format": "date",
            "description": "End date for the trend analysis period in YYYY-MM-DD format."
        },
        "interval": {
            "type": "string",
            "enum": [
                "daily",
                "weekly",
                "monthly"
            ],
            "description": "Optional: Time interval for aggregating data points in the chart. Defaults to weekly.",
            "default": "weekly"
        },
        "chart_type": {
            "type": "string",
            "enum": [
                "line",
                "bar",
                "area"
            ],
            "description": "Optional: Visual chart type for the trend representation. Defaults to line.",
            "default": "line"
        }
    },
    "required": [
        "content_type",
        "content_identifier",
        "platform",
        "metric",
        "start_date",
        "end_date"
    ]
},
}
