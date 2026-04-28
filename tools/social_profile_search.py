"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Search for social media profiles by username, display name, or bio keywords across multiple platforms."""
    import json
    try:
        data = json.loads(payload)
        query = data.get('query')
        if not query or not query.strip():
            return json.dumps({'error': 'Missing required parameter: query'})
        platform = data.get('platform', 'all')
        verified_only = data.get('verified_only', False)
        max_results = min(max(data.get('max_results', 20), 1), 100)
        # Simulated search over a mock database
        mock_profiles = [
            {'username': 'john_doe', 'display_name': 'John Doe', 'platform': 'twitter', 'bio': 'Software developer | Coffee lover', 'verified': True, 'profile_url': 'https://twitter.com/john_doe'},
            {'username': 'jane_doe', 'display_name': 'Jane Doe', 'platform': 'linkedin', 'bio': 'Marketing professional', 'verified': False, 'profile_url': 'https://linkedin.com/in/jane_doe'},
            {'username': 'tech_guru', 'display_name': 'Tech Guru', 'platform': 'instagram', 'bio': 'Tech reviews and tutorials', 'verified': True, 'profile_url': 'https://instagram.com/tech_guru'},
            {'username': 'social_bee', 'display_name': 'Social Bee', 'platform': 'facebook', 'bio': 'Community manager | Events', 'verified': False, 'profile_url': 'https://facebook.com/social_bee'},
            {'username': 'ai_explorer', 'display_name': 'AI Explorer', 'platform': 'twitter', 'bio': 'Exploring AI and machine learning', 'verified': False, 'profile_url': 'https://twitter.com/ai_explorer'}
        ]
        results = []
        q_lower = query.lower()
        for prof in mock_profiles:
            if platform != 'all' and prof['platform'] != platform:
                continue
            if verified_only and not prof['verified']:
                continue
            match = (q_lower in prof['username'].lower() or
                     q_lower in prof['display_name'].lower() or
                     q_lower in prof['bio'].lower())
            if match:
                results.append(prof)
            if len(results) >= max_results:
                break
        return json.dumps({'query': query, 'count': len(results), 'results': results}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)})


TOOL_SPEC = {
    "name": "social_profile_search",
    "description": "Search for social media profiles by username, display name, or bio keywords across multiple platforms, returning matching profiles with platform, account ID, profile URL, and verification status.",
    "category": "search",
    "domain": "social",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "The search term to match against usernames, display names, or bio content (case-insensitive, partial match)."
        },
        "platform": {
            "type": "string",
            "description": "Optional: Filter to one specific platform, e.g. 'twitter', 'facebook', 'linkedin', 'instagram'. If omitted, search across all platforms.",
            "enum": [
                "twitter",
                "facebook",
                "linkedin",
                "instagram",
                "all"
            ]
        },
        "verified_only": {
            "type": "boolean",
            "description": "Optional: If true, return only verified/authenticated accounts."
        },
        "max_results": {
            "type": "integer",
            "description": "Optional: Maximum number of results to return (1-100, default 20).",
            "minimum": 1,
            "maximum": 100
        }
    },
    "required": [
        "query"
    ]
},
}
