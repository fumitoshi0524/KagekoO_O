"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    import random
    from datetime import datetime, timedelta

    try:
        data = json.loads(payload)
        
        # Validate required fields
        if 'username' not in data or 'platform' not in data:
            return json.dumps({'error': 'Missing required fields: username, platform'})
        
        username = data['username']
        platform = data['platform']
        inactivity_days = data.get('inactivity_days', 90)
        min_followers = data.get('min_followers', 0)
        include_spam = data.get('include_spam', False)
        
        # Validate username format
        if not (3 <= len(username) <= 30 and username.replace('_', '').isalnum()):
            return json.dumps({'error': 'Invalid username format (3-30 chars, alphanumeric with underscores only)'})
        
        # Validate platform
        valid_platforms = ['twitter', 'instagram', 'linkedin', 'facebook', 'reddit']
        if platform not in valid_platforms:
            return json.dumps({'error': f'Invalid platform. Must be one of: {valid_platforms}'})
        
        # Simulate analysis based on platform-specific patterns
        # In production, this would call actual social media APIs
        analysis_time = datetime.now()
        
        # Generate mock connections data
        possible_connections = [
            {'username': 'user_' + str(i), 'display_name': f'User {i}', 'last_active': (analysis_time - timedelta(days=random.randint(1, 365))).isoformat(), 'followers': random.randint(0, 5000), 'following': random.randint(0, 2000), 'is_spam': random.random() < 0.1, 'is_duplicate': random.random() < 0.05}
            for i in range(50)
        ]
        
        # Categorize connections
        stale = []
        spam = []
        duplicates = []
        low_engagement = []
        
        for conn in possible_connections:
            last_active = datetime.fromisoformat(conn['last_active'])
            days_inactive = (analysis_time - last_active).days
            
            if conn['is_spam']:
                spam.append(conn)
            elif conn['is_duplicate']:
                duplicates.append(conn)
            elif days_inactive > inactivity_days:
                stale.append(conn)
            elif conn['followers'] < min_followers:
                low_engagement.append(conn)
        
        # Build prioritized cleanup list
        cleanup_list = []
        
        # Highest priority: spam if included
        if include_spam:
            for conn in spam:
                cleanup_list.append({
                    'username': conn['username'],
                    'display_name': conn['display_name'],
                    'reason': 'spam_or_bot',
                    'priority': 'high'
                })
        
        # Second priority: duplicate accounts
        for conn in duplicates:
            cleanup_list.append({
                'username': conn['username'],
                'display_name': conn['display_name'],
                'reason': 'duplicate_profile',
                'priority': 'high'
            })
        
        # Third priority: stale accounts
        for conn in stale[:10]:  # Limit to 10 for sanity
            cleanup_list.append({
                'username': conn['username'],
                'display_name': conn['display_name'],
                'reason': f'inactive_{inactivity_days}_days',
                'priority': 'medium'
            })
        
        # Low priority: low followers
        if min_followers > 0:
            for conn in low_engagement[:5]:  # Limit to 5
                cleanup_list.append({
                    'username': conn['username'],
                    'display_name': conn['display_name'],
                    'reason': 'low_followers',
                    'priority': 'low'
                })
        
        # Sort by priority
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        cleanup_list.sort(key=lambda x: priority_order.get(x['priority'], 3))
        
        # Build summary
        result = {
            'analysis_time': analysis_time.isoformat(),
            'platform': platform,
            'username': username,
            'total_connections_analyzed': len(possible_connections),
            'recommended_actions': len(cleanup_list),
            'breakdown': {
                'spam_or_bot': len(spam),
                'duplicate': len(duplicates),
                'stale': len(stale),
                'low_engagement': len(low_engagement)
            },
            'cleanup_suggestions': cleanup_list
        }
        
        return json.dumps(result, ensure_ascii=False, default=str)
        
    except json.JSONDecodeError:
        return json.dumps({'error': 'Invalid JSON payload'})
    except Exception as e:
        return json.dumps({'error': str(e)})


TOOL_SPEC = {
    "name": "social_account_cleanup",
    "description": "Analyze a social media account's connections and suggest cleanup actions based on inactivity, duplicate profiles, and engagement patterns, returning a prioritized list of accounts to unfollow or remove.",
    "category": "system",
    "domain": "social",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "username": {
            "type": "string",
            "description": "The social media username to analyze for cleanup recommendations (must match platform's username format, alphanumeric with underscores, 3-30 characters)"
        },
        "platform": {
            "type": "string",
            "description": "The social media platform to analyze",
            "enum": [
                "twitter",
                "instagram",
                "linkedin",
                "facebook",
                "reddit"
            ]
        },
        "inactivity_days": {
            "type": "integer",
            "description": "Optional: Number of days of inactivity to consider an account stale (default: 90, min: 1, max: 365)",
            "default": 90
        },
        "min_followers": {
            "type": "integer",
            "description": "Optional: Minimum followers count for accounts to keep (default: 0, meaning no minimum)",
            "default": 0
        },
        "include_spam": {
            "type": "boolean",
            "description": "Optional: Whether to include accounts flagged as spam or bots in recommendations (default: False)",
            "default": False
        }
    },
    "required": [
        "username",
        "platform"
    ]
},
}
