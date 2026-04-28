"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Search for influencers by niche, follower count range, and optional engagement rate and platform."""
    import json
    try:
        data = json.loads(payload)
        niche = data.get('niche')
        min_followers = data.get('min_followers')
        max_followers = data.get('max_followers')
        min_engagement_rate = data.get('min_engagement_rate')
        platform = data.get('platform')

        if not niche or not isinstance(niche, str) or not niche.strip():
            return json.dumps({'error': 'Missing or invalid required field: niche (must be non-empty string)'})
        if min_followers is None or not isinstance(min_followers, int) or min_followers < 0:
            return json.dumps({'error': 'Missing or invalid required field: min_followers (must be non-negative integer)'})
        if max_followers is None or not isinstance(max_followers, int) or max_followers < 0:
            return json.dumps({'error': 'Missing or invalid required field: max_followers (must be non-negative integer)'})
        if max_followers < min_followers:
            return json.dumps({'error': 'max_followers must be >= min_followers'})
        if min_engagement_rate is not None:
            if not isinstance(min_engagement_rate, (int, float)) or min_engagement_rate < 0 or min_engagement_rate > 100:
                return json.dumps({'error': 'min_engagement_rate must be between 0 and 100'})
        if platform is not None and platform not in ['instagram', 'youtube', 'tiktok', 'twitter', 'linkedin']:
            return json.dumps({'error': 'Invalid platform. Must be one of: instagram, youtube, tiktok, twitter, linkedin'})

        # Simulated data store (in real scenario, query an API or database)
        mock_influencers = [
            {'username': '@styleguru', 'niche': 'fashion', 'followers': 25000, 'avg_engagement': 4.2, 'platform': 'instagram'},
            {'username': '@fitlife', 'niche': 'fitness', 'followers': 120000, 'avg_engagement': 3.8, 'platform': 'instagram'},
            {'username': '@techreviewer', 'niche': 'tech', 'followers': 500000, 'avg_engagement': 2.1, 'platform': 'youtube'},
            {'username': '@travelbug', 'niche': 'travel', 'followers': 8000, 'avg_engagement': 6.5, 'platform': 'tiktok'},
            {'username': '@codebytes', 'niche': 'tech', 'followers': 15000, 'avg_engagement': 5.0, 'platform': 'twitter'},
            {'username': '@vintagevibes', 'niche': 'fashion', 'followers': 35000, 'avg_engagement': 3.2, 'platform': 'instagram'},
            {'username': '@yogawithjane', 'niche': 'fitness', 'followers': 60000, 'avg_engagement': 4.7, 'platform': 'youtube'},
            {'username': '@adventuresinc', 'niche': 'travel', 'followers': 200000, 'avg_engagement': 1.9, 'platform': 'instagram'},
        ]

        results = []
        for inf in mock_influencers:
            if inf['niche'].lower() != niche.lower():
                continue
            if not (min_followers <= inf['followers'] <= max_followers):
                continue
            if min_engagement_rate is not None and inf['avg_engagement'] < min_engagement_rate:
                continue
            if platform is not None and inf['platform'] != platform:
                continue
            results.append(inf)

        # Sort by followers descending, then by engagement descending
        results.sort(key=lambda x: (-x['followers'], -x['avg_engagement']))

        return json.dumps({'influencers': results, 'count': len(results)}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)})


TOOL_SPEC = {
    "name": "find_influencers",
    "description": "Search for social media influencers based on niche, follower count range, and engagement rate threshold, returning a ranked list of matching profiles with key metrics for campaign outreach.",
    "category": "search",
    "domain": "social",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "niche": {
            "type": "string",
            "description": "Primary content category or industry (e.g., 'fashion', 'fitness', 'tech', 'travel')"
        },
        "min_followers": {
            "type": "integer",
            "description": "Minimum number of followers (must be >= 0)",
            "minimum": 0
        },
        "max_followers": {
            "type": "integer",
            "description": "Maximum number of followers (must be >= min_followers)",
            "minimum": 0
        },
        "min_engagement_rate": {
            "type": "number",
            "description": "Optional: Minimum engagement rate as a percentage (e.g., 3.5 for 3.5%). Must be between 0 and 100.",
            "minimum": 0,
            "maximum": 100
        },
        "platform": {
            "type": "string",
            "description": "Optional: Social media platform to search within",
            "enum": [
                "instagram",
                "youtube",
                "tiktok",
                "twitter",
                "linkedin"
            ]
        }
    },
    "required": [
        "niche",
        "min_followers",
        "max_followers"
    ]
},
}
