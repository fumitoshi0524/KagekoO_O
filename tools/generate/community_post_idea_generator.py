"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        topic = data.get('topic')
        platform = data.get('platform')
        brand_voice = data.get('brand_voice')
        count = data.get('count', 3)
        include_hashtags = data.get('include_hashtags', True)
        include_cta = data.get('include_cta', True)
        
        if not topic or not platform or not brand_voice:
            return json.dumps({'error': 'Missing required fields'}, ensure_ascii=False)
        
        # Simple deterministic generation based on inputs (for demo purposes)
        templates = {
            'professional': [
                'Discover how {topic} is transforming our industry.',
                'New insights on {topic}: What you need to know.',
                'We re proud to share our latest approach to {topic}.'
            ],
            'casual': [
                'Just dropped: Our take on {topic}.',
                'Anyone else obsessed with {topic}?',
                'Let s talk about {topic}: Your go-to guide.'
            ],
            'humorous': [
                '{topic} be like...',
                'Me explaining {topic} to my friends: A thread.',
                'POV: You finally understand {topic}.'
            ],
            'inspirational': [
                'Great things happen when we embrace {topic}.',
                'The future of {topic} starts with you.',
                'Dream big, start small, focus on {topic}.'
            ],
            'educational': [
                '{topic} 101: A quick guide.',
                '5 things you didn t know about {topic}.',
                'How to master {topic} in 3 steps.'
            ],
            'conversational': [
                'What s your biggest challenge with {topic}?',
                'We want to hear your stories about {topic}.',
                'Question for the community: How do you approach {topic}?'
            ]
        }
        
        selected_templates = templates.get(brand_voice, templates['casual'])
        
        hashtag_bank = ['#' + topic.replace(' ', ''), '#socialmedia', '#community', '#engagement', '#tips', '#insights']
        cta_bank = ['Share your thoughts below!', 'Tag a friend who needs to see this.', 'Double tap if you agree.', 'Comment your experience.', 'Save for later!']
        
        posts = []
        for i in range(min(count, len(selected_templates))):
            post_text = selected_templates[i].format(topic=topic)
            post = {'text': post_text}
            if include_hashtags:
                post['hashtags'] = hashtag_bank[:3]
            if include_cta:
                post['call_to_action'] = cta_bank[i % len(cta_bank)]
            posts.append(post)
        
        result = {
            'topic': topic,
            'platform': platform,
            'brand_voice': brand_voice,
            'posts': posts
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "community_post_idea_generator",
    "description": "Generate creative social media post ideas for community engagement based on topic, platform, and brand voice, returning a list of post concepts with suggested hashtags and call-to-action phrases.",
    "category": "generate",
    "domain": "social",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "topic": {
            "type": "string",
            "description": "The core theme or subject for the post ideas (e.g., product launch, holiday, awareness day)."
        },
        "platform": {
            "type": "string",
            "enum": [
                "twitter",
                "instagram",
                "linkedin",
                "facebook",
                "tiktok",
                "youtube"
            ],
            "description": "The social media platform the posts are intended for."
        },
        "brand_voice": {
            "type": "string",
            "enum": [
                "professional",
                "casual",
                "humorous",
                "inspirational",
                "educational",
                "conversational"
            ],
            "description": "The tone or personality style for the generated content."
        },
        "count": {
            "type": "integer",
            "description": "Optional: Number of post ideas to generate (default 3, max 10).",
            "minimum": 1,
            "maximum": 10
        },
        "include_hashtags": {
            "type": "boolean",
            "description": "Optional: Whether to include suggested hashtags in each post idea (default True)."
        },
        "include_cta": {
            "type": "boolean",
            "description": "Optional: Whether to include a call-to-action phrase for each post idea (default True)."
        }
    },
    "required": [
        "topic",
        "platform",
        "brand_voice"
    ]
},
}
