"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Search for potential friends in a social network based on shared interests, location proximity, and common connections."""
    import json
    try:
        data = json.loads(payload)
        user_id = data.get('current_user_id')
        if not user_id:
            return json.dumps({'error': 'current_user_id is required'})
        interests = data.get('interests', None)
        radius = data.get('location_radius_km', 50)
        min_mutual = data.get('min_mutual_friends', 1)
        max_results = min(data.get('max_results', 10), 50)
        
        # Simulate a database of users (in production, this would query a real DB)
        all_users = [
            {'id': 'u2', 'name': 'Alice', 'interests': ['hiking', 'photography', 'cooking'], 'location': {'lat': 40.7128, 'lng': -74.0060}, 'friends': ['u3', 'u4']},
            {'id': 'u3', 'name': 'Bob', 'interests': ['photography', 'gaming'], 'location': {'lat': 40.7282, 'lng': -73.7949}, 'friends': ['u2']},
            {'id': 'u4', 'name': 'Charlie', 'interests': ['cooking', 'reading'], 'location': {'lat': 34.0522, 'lng': -118.2437}, 'friends': ['u2']},
            {'id': 'u5', 'name': 'Diana', 'interests': ['hiking', 'yoga'], 'location': {'lat': 40.7614, 'lng': -73.9776}, 'friends': []},
        ]
        current_user = None
        for u in all_users:
            if u['id'] == user_id:
                current_user = u
                break
        if not current_user:
            return json.dumps({'error': 'User not found'})
        
        target_interests = interests if interests else current_user.get('interests', [])
        current_user_friends = set(current_user.get('friends', []))
        
        results = []
        for candidate in all_users:
            if candidate['id'] == user_id:
                continue
            # Calculate interest match score
            common_interests = set(candidate.get('interests', [])) & set(target_interests)
            interest_score = len(common_interests) / max(len(target_interests), 1)
            
            # Calculate mutual friends count
            mutual_friends = len(current_user_friends & set(candidate.get('friends', [])))
            if mutual_friends < min_mutual:
                continue
            
            # Calculate location proximity (simple Manhattan distance for demo)
            loc_score = 0.0
            if 'location' in candidate and 'location' in current_user:
                lat_diff = abs(candidate['location']['lat'] - current_user['location']['lat'])
                lng_diff = abs(candidate['location']['lng'] - current_user['location']['lng'])
                # Rough conversion: 1 degree lat ~ 111km, 1 degree lng ~ 111*cos(40deg) ~ 85km
                dist_km = (lat_diff * 111) + (lng_diff * 85)
                if dist_km <= radius:
                    loc_score = 1.0 - (dist_km / radius)
                else:
                    continue
            
            # Combined score (weighted)
            total_score = interest_score * 0.5 + (mutual_friends / 10.0) * 0.3 + loc_score * 0.2
            recommendations = list(common_interests) if common_interests else []
            results.append({
                'user_id': candidate['id'],
                'name': candidate['name'],
                'match_score': round(total_score, 2),
                'shared_interests': recommendations,
                'mutual_friends_count': mutual_friends,
                'reason': f"Shares {len(common_interests)} interests and has {mutual_friends} mutual friend(s)" if common_interests or mutual_friends > 0 else "Based on general compatibility"
            })
        
        # Sort by match score descending and limit results
        results.sort(key=lambda x: x['match_score'], reverse=True)
        results = results[:max_results]
        
        return json.dumps({'status': 'success', 'recommendations': results, 'total_found': len(results)})
    except Exception as e:
        return json.dumps({'error': str(e)})


TOOL_SPEC = {
    "name": "social_friend_finder",
    "description": "Search for potential friends in a social network based on shared interests, location proximity, and common connections, returning a ranked list of user profiles with match scores and reasons for the recommendation.",
    "category": "search",
    "domain": "social",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "current_user_id": {
            "type": "string",
            "description": "Unique identifier of the user performing the search"
        },
        "interests": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "Optional: List of interests to match against (e.g., hiking, photography, cooking). If not provided, uses current user's profile interests."
        },
        "location_radius_km": {
            "type": "number",
            "description": "Optional: Maximum distance in kilometers from current user's location to filter potential friends. Default: 50"
        },
        "min_mutual_friends": {
            "type": "integer",
            "minimum": 0,
            "description": "Optional: Minimum number of mutual friends required for a match. Default: 1"
        },
        "max_results": {
            "type": "integer",
            "minimum": 1,
            "maximum": 50,
            "description": "Optional: Maximum number of friend recommendations to return. Default: 10, max 50."
        }
    },
    "required": [
        "current_user_id"
    ]
},
}
