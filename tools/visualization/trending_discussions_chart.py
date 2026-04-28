"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        platforms = data.get('platforms', [])
        time_range = data.get('time_range', '24h')
        topic_keywords = data.get('topic_keywords', [])
        
        if not platforms:
            return 'error: platforms must be a non-empty list'
        
        # Simulate fetching trending data (in production, call APIs for each platform)
        # For demonstration, generate mock data
        import random
        topics = ['#AI', '#ClimateChange', '#Election2024', '#StreamingWars', '#RemoteWork', '#Cryptocurrency']
        if topic_keywords:
            topics = [t for t in topics if any(k.lower() in t.lower() for k in topic_keywords)]
            if not topics:
                topics = ['#General']
        
        chart_data = []
        for topic in topics:
            for platform in platforms:
                frequency = random.randint(100, 10000)
                chart_data.append({
                    'topic': topic,
                    'platform': platform,
                    'frequency': frequency,
                    'time_range': time_range
                })
        
        # Sort by frequency descending
        chart_data.sort(key=lambda x: x['frequency'], reverse=True)
        
        # Generate a dummy chart URL (in real scenario, use matplotlib or similar to render and upload)
        chart_url = 'https://charts.example.com/trending_' + str(hash(str(chart_data)) % 10000) + '.png'
        
        result = {
            'chart_url': chart_url,
            'data': chart_data,
            'summary': {
                'total_topics': len(set(d['topic'] for d in chart_data)),
                'total_platforms': len(platforms),
                'time_range': time_range
            }
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "trending_discussions_chart",
    "description": "Generate a bar chart visualization comparing trending discussion topics across social platforms, returning the chart image URL and topic frequency data for community trend analysis.",
    "category": "visualization",
    "domain": "social",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "platforms": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [
                    "twitter",
                    "reddit",
                    "facebook",
                    "linkedin",
                    "tiktok",
                    "discord"
                ]
            },
            "description": "List of social platforms to analyze for trending topics."
        },
        "time_range": {
            "type": "string",
            "enum": [
                "24h",
                "7d",
                "30d",
                "90d"
            ],
            "description": "Time window for trend aggregation."
        },
        "topic_keywords": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "Optional: List of keywords to filter trending discussions. If empty, returns overall top trends."
        }
    },
    "required": [
        "platforms",
        "time_range"
    ]
},
}
