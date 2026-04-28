"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a detailed impact visualization of a social media post's reach and engagement across network layers."""
    import json
    try:
        data = json.loads(payload)
        post_id = data.get('post_id')
        platform = data.get('platform')
        initial_reach = data.get('initial_reach')
        share_rate = data.get('share_rate')
        engagement_type = data.get('engagement_type', 'share')
        max_layers = data.get('max_layers', 3)

        if not all([post_id, platform, initial_reach, share_rate]):
            return json.dumps({'error': 'Missing required fields: post_id, platform, initial_reach, share_rate'})

        if not isinstance(initial_reach, int) or initial_reach < 1:
            return json.dumps({'error': 'initial_reach must be a positive integer'})

        if not isinstance(share_rate, (int, float)) or not (0.0 <= share_rate <= 1.0):
            return json.dumps({'error': 'share_rate must be between 0.0 and 1.0'})

        if max_layers < 1 or max_layers > 5:
            max_layers = 3

        layers_data = []
        total_reach = 0
        cumulative_engagement = 0
        current_layer = initial_reach
        decay_factor = 0.7

        for layer in range(1, max_layers + 1):
            if layer == 1:
                layer_reach = current_layer
            else:
                layer_reach = int(current_layer * share_rate * (decay_factor ** (layer - 2)))

            if layer_reach == 0:
                break

            if engagement_type == 'like':
                layer_engagement = int(layer_reach * 0.3)
            elif engagement_type == 'comment':
                layer_engagement = int(layer_reach * 0.1)
            elif engagement_type == 'repost':
                layer_engagement = int(layer_reach * 0.15)
            else:  # share
                layer_engagement = int(layer_reach * 0.4)

            layers_data.append({
                'layer': layer,
                'reach': layer_reach,
                'engagement_count': layer_engagement,
                'network_spread': [{'node': f'user_{i}', 'engaged': i % 3 == 0} for i in range(min(layer_reach, 100))]
            })
            total_reach += layer_reach
            cumulative_engagement += layer_engagement

        result = {
            'post_id': post_id,
            'platform': platform,
            'total_reach': total_reach,
            'total_engagement': cumulative_engagement,
            'engagement_rate': round((cumulative_engagement / total_reach) * 100, 2) if total_reach > 0 else 0.0,
            'layers': layers_data,
            'impact_summary': f'Post {post_id} on {platform} reached {total_reach} users across {len(layers_data)} network layers, generating {cumulative_engagement} {engagement_type}s.'
        }

        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "social_network_impact_visualizer",
    "description": "Generate a detailed impact visualization of a social media post's reach and engagement across network layers (direct followers, secondary shares, tertiary mentions). Returns a structured summary with engagement metrics and a simulated network spread map.",
    "category": "visualization",
    "domain": "social",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "post_id": {
            "type": "string",
            "description": "Unique identifier of the social media post to analyze"
        },
        "platform": {
            "type": "string",
            "enum": [
                "twitter",
                "facebook",
                "linkedin",
                "instagram"
            ],
            "description": "Social media platform where the post was published"
        },
        "initial_reach": {
            "type": "integer",
            "description": "Number of direct followers who saw the post initially",
            "minimum": 1
        },
        "share_rate": {
            "type": "number",
            "description": "Fraction of viewers who share the post (0.0 to 1.0)",
            "minimum": 0.0,
            "maximum": 1.0
        },
        "engagement_type": {
            "type": "string",
            "enum": [
                "like",
                "comment",
                "share",
                "repost"
            ],
            "description": "Primary type of engagement to visualize"
        },
        "max_layers": {
            "type": "integer",
            "description": "Optional: Maximum number of network layers to calculate (default: 3, min: 1, max: 5)",
            "minimum": 1,
            "maximum": 5,
            "default": 3
        }
    },
    "required": [
        "post_id",
        "platform",
        "initial_reach",
        "share_rate"
    ]
},
}
