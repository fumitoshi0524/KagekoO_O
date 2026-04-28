"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    from datetime import datetime, timedelta
    import random
    try:
        data = json.loads(payload)
        community_id = data.get('community_id')
        date_range = data.get('date_range')
        user_segments = data.get('user_segments')
        metric = data.get('metric')
        normalize = data.get('normalize', False)
        
        if not community_id or not date_range or not user_segments or not metric:
            return json.dumps({'error': 'Missing required fields: community_id, date_range, user_segments, metric'})
        
        # Parse date range
        try:
            start_str, end_str = date_range.split('/')
            start_date = datetime.fromisoformat(start_str)
            end_date = datetime.fromisoformat(end_str)
        except:
            return json.dumps({'error': 'Invalid date_range format. Use ISO 8601: start_date/end_date'})
        
        if metric not in ['likes', 'comments', 'shares', 'mentions', 'total_interactions']:
            return json.dumps({'error': 'Invalid metric. Must be one of: likes, comments, shares, mentions, total_interactions'})
        
        # Generate heatmap data
        hours = list(range(24))
        heatmap_data = []
        
        # Seed random for reproducibility within session
        random.seed(hash(community_id + date_range + metric))
        
        global_max = 0
        for segment in user_segments:
            row = {'segment': segment, 'values': []}
            for hour in hours:
                # Simulate realistic engagement patterns
                base = 10
                if segment == 'power_users':
                    base = 50
                elif segment == 'inactive_users':
                    base = 3
                elif segment == 'new_users':
                    base = 20
                
                # Time-of-day pattern
                if 8 <= hour <= 10:
                    time_factor = 0.8
                elif 11 <= hour <= 14:
                    time_factor = 1.2
                elif 15 <= hour <= 18:
                    time_factor = 1.0
                elif 19 <= hour <= 22:
                    time_factor = 1.5
                elif 23 <= hour <= 5:
                    time_factor = 0.2
                else:
                    time_factor = 0.5
                
                value = int(base * time_factor * (1 + random.uniform(-0.3, 0.3)))
                row['values'].append(value)
                if value > global_max:
                    global_max = value
            heatmap_data.append(row)
        
        # Normalize if requested
        if normalize and global_max > 0:
            for row in heatmap_data:
                row['values'] = [int((v / global_max) * 100) for v in row['values']]
        
        result = {
            'community_id': community_id,
            'date_range': date_range,
            'metric': metric,
            'hours': hours,
            'normalized': normalize,
            'segments': heatmap_data,
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'row_count': len(heatmap_data),
                'column_count': len(hours)
            }
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "social_engagement_heatmap",
    "description": "Generate a structured engagement heatmap dataset from social community posts, showing interaction density across user segments and time periods. Returns a matrix of engagement scores by user cohort and hour-of-day for visualization in dashboard tools.",
    "category": "visualization",
    "domain": "social",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "community_id": {
            "type": "string",
            "description": "Unique identifier for the social community or group to analyze"
        },
        "date_range": {
            "type": "string",
            "description": "Date range for analysis in ISO 8601 period format (e.g. '2024-01-01/2024-01-07')"
        },
        "user_segments": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "List of user segment labels to include in the heatmap rows (e.g. ['new_users', 'power_users', 'inactive_users'])"
        },
        "metric": {
            "type": "string",
            "enum": [
                "likes",
                "comments",
                "shares",
                "mentions",
                "total_interactions"
            ],
            "description": "Type of engagement metric to aggregate in the heatmap cells"
        },
        "normalize": {
            "type": "boolean",
            "description": "Optional: Whether to normalize scores to 0-100 scale for cross-segment comparison",
            "default": false
        }
    },
    "required": [
        "community_id",
        "date_range",
        "user_segments",
        "metric"
    ]
},
}
