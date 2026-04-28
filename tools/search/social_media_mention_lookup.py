"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    from datetime import datetime, timedelta
    import random
    try:
        data = json.loads(payload)
        query = data.get('query')
        if not query or len(str(query)) < 2:
            return json.dumps({'error': 'Query must be between 2 and 100 characters.'})
        platform = data.get('platform', 'all')
        max_results = data.get('max_results', 10)
        sort_by = data.get('sort_by', 'relevance')
        if not isinstance(max_results, int) or max_results < 1 or max_results > 100:
            return json.dumps({'error': 'max_results must be an integer between 1 and 100.'})
        platforms = ['twitter', 'reddit', 'instagram', 'facebook', 'linkedin'] if platform == 'all' else [platform]
        posts = []
        for i in range(min(max_results, 20)):
            plat = random.choice(platforms)
            base_time = datetime.now() - timedelta(hours=random.randint(1, 168))
            post = {
                'post_id': f'{plat}_{random.randint(10000,99999)}',
                'author': f'user_{random.randint(1000,9999)}',
                'content': f'Check out {query} — interesting discussion happening!',
                'platform': plat,
                'timestamp': base_time.isoformat(),
                'likes': random.randint(0, 500),
                'shares': random.randint(0, 100),
                'comments': random.randint(0, 50)
            }
            posts.append(post)
        if sort_by == 'date_desc':
            posts.sort(key=lambda x: x['timestamp'], reverse=True)
        elif sort_by == 'date_asc':
            posts.sort(key=lambda x: x['timestamp'])
        elif sort_by == 'engagement_desc':
            posts.sort(key=lambda x: x['likes'] + x['shares'] + x['comments'], reverse=True)
        result = {
            'query': query,
            'results_count': len(posts),
            'platforms_searched': platforms,
            'posts': posts[:max_results]
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "social_media_mention_lookup",
    "description": "Search for mentions of a specified user or keyword across social media posts, returning a list of matching posts with authors, timestamps, and engagement metrics for social listening and trend analysis.",
    "category": "search",
    "domain": "social",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Keyword, hashtag, or @username to search for (e.g. '@john_doe', '#AI', 'product launch'). Must be between 2 and 100 characters."
        },
        "platform": {
            "type": "string",
            "description": "Optional: Social media platform to search on. Supported: twitter, reddit, instagram, facebook, linkedin. Default is all platforms.",
            "enum": [
                "twitter",
                "reddit",
                "instagram",
                "facebook",
                "linkedin",
                "all"
            ]
        },
        "max_results": {
            "type": "integer",
            "description": "Optional: Maximum number of matching posts to return. Must be between 1 and 100. Default is 10.",
            "minimum": 1,
            "maximum": 100
        },
        "sort_by": {
            "type": "string",
            "description": "Optional: Sort order for results. Options: relevance (default), date_desc, date_asc, engagement_desc.",
            "enum": [
                "relevance",
                "date_desc",
                "date_asc",
                "engagement_desc"
            ]
        }
    },
    "required": [
        "query"
    ]
},
}
