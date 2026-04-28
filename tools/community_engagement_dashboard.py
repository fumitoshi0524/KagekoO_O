"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    from collections import defaultdict
    from datetime import datetime, timedelta
    import random

    try:
        data = json.loads(payload)
        community = data.get('community_name')
        start = data.get('start_date')
        end = data.get('end_date')
        metric = data.get('metric', 'all')
        granularity = data.get('granularity', 'daily')

        if not all([community, start, end, metric]):
            return json.dumps({'error': 'Missing required fields: community_name, start_date, end_date, metric'})

        start_dt = datetime.strptime(start, '%Y-%m-%d')
        end_dt = datetime.strptime(end, '%Y-%m-%d')
        if start_dt > end_dt:
            return json.dumps({'error': 'start_date must be before end_date'})

        # Generate simulated community engagement data
        dates = []
        current = start_dt
        while current <= end_dt:
            if granularity == 'daily':
                dates.append(current.strftime('%Y-%m-%d'))
                current += timedelta(days=1)
            elif granularity == 'weekly':
                dates.append(current.strftime('%Y-%m-%d'))
                current += timedelta(weeks=1)
            elif granularity == 'monthly':
                dates.append(current.strftime('%Y-%m-%d'))
                if current.month == 12:
                    current = current.replace(year=current.year + 1, month=1)
                else:
                    current = current.replace(month=current.month + 1)

        trend_data = []
        for d in dates:
            posts = random.randint(5, 50)
            reactions = random.randint(posts * 2, posts * 10)
            comments = random.randint(posts, posts * 5)
            trend_data.append({
                'date': d,
                'posts': posts,
                'reactions': reactions,
                'comments': comments
            })

        # Reactions distribution (simulated)
        reaction_types = ['like', 'love', 'laugh', 'wow', 'sad', 'angry']
        reactions_dist = []
        total_reactions = sum(t['reactions'] for t in trend_data)
        for rtype in reaction_types:
            count = random.randint(int(total_reactions * 0.02), int(total_reactions * 0.4))
            reactions_dist.append({'type': rtype, 'count': count})

        # Top contributors (simulated)
        members = ['Alice', 'Bob', 'Charlie', 'Diana', 'Eve', 'Frank', 'Grace', 'Henry', 'Ivy', 'Jack']
        top_contributors = []
        for member in members:
            top_contributors.append({
                'username': member,
                'post_count': random.randint(5, 120),
                'total_reactions': random.randint(50, 2000)
            })
        top_contributors.sort(key=lambda x: x['total_reactions'], reverse=True)

        result = {
            'community': community,
            'period': {'start': start, 'end': end},
            'granularity': granularity,
            'selected_metric': metric,
            'trend': trend_data,
            'reactions_distribution': reactions_dist,
            'top_contributors': top_contributors[:5],  # Top 5
            'summary': {
                'total_posts': sum(t['posts'] for t in trend_data),
                'total_reactions': total_reactions,
                'total_comments': sum(t['comments'] for t in trend_data),
                'unique_dates': len(dates),
                'average_daily_posts': round(sum(t['posts'] for t in trend_data) / max(len(dates), 1), 1)
            }
        }

        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "community_engagement_dashboard",
    "description": "Generate a visual engagement dashboard for a social community or group, showing member activity trends, post frequency, reactions distribution, and top contributors over a specified time period. Returns structured data suitable for chart rendering and community health analysis.",
    "category": "visualization",
    "domain": "social",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "community_name": {
            "type": "string",
            "description": "Name or identifier of the social community or group to analyze"
        },
        "start_date": {
            "type": "string",
            "description": "Start date for the analysis period in YYYY-MM-DD format"
        },
        "end_date": {
            "type": "string",
            "description": "End date for the analysis period in YYYY-MM-DD format"
        },
        "metric": {
            "type": "string",
            "description": "Primary engagement metric to visualize",
            "enum": [
                "posts",
                "reactions",
                "comments",
                "all"
            ]
        },
        "granularity": {
            "type": "string",
            "description": "Optional: Time granularity for trend data aggregation. Defaults to daily",
            "enum": [
                "daily",
                "weekly",
                "monthly"
            ]
        }
    },
    "required": [
        "community_name",
        "start_date",
        "end_date",
        "metric"
    ]
},
}
