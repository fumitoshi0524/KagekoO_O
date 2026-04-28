"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        if 'topic' not in data or 'platform' not in data:
            return 'error: required fields missing (topic, platform)'
        topic = data['topic']
        platform = data['platform']
        tone = data.get('tone', 'professional')
        keywords = data.get('keywords', [])
        target_audience = data.get('target_audience', 'general audience')
        max_chars = data.get('max_characters', 500)
        if platform == 'twitter' and max_chars > 280:
            max_chars = 280
        hashtags = [f'#{word.replace(" ", "").lower()}' for word in topic.split() if len(word) > 2]
        if keywords:
            hashtags.extend([f'#{kw.replace(" ", "").lower()}' for kw in keywords])
        hashtags = list(set(hashtags))[:5]
        tone_intro = {
            'professional': 'Here is an insightful post',
            'casual': 'Check this out',
            'inspirational': 'Let this inspire you',
            'humorous': 'A little humor for your day',
            'urgent': 'Don't miss this'
        }
        intro = tone_intro.get(tone, 'Here is a post')
        body = f"{intro} about {topic}. This content is tailored for {target_audience}."
        if keywords:
            body += f" Key points: {', '.join(keywords)}."
        body += f" Learn more and share your thoughts!"
        if len(body) > max_chars:
            body = body[:max_chars-3] + '...'
        result = {
            'post_text': body,
            'hashtags': ' '.join(hashtags),
            'character_count': len(body),
            'platform': platform,
            'tone': tone
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "social_media_post_generator",
    "description": "Generate a social media post from a topic or keywords, including suggested hashtags and an engaging caption, returning the post text, hashtags, and platform-specific formatting.",
    "category": "generate",
    "domain": "social",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "topic": {
            "type": "string",
            "description": "The main topic or theme for the social media post (e.g., 'new product launch', 'customer success story', 'industry tip')."
        },
        "keywords": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "Optional: A list of specific keywords or phrases to include in the post for SEO or emphasis."
        },
        "tone": {
            "type": "string",
            "enum": [
                "professional",
                "casual",
                "inspirational",
                "humorous",
                "urgent"
            ],
            "description": "The desired tone of the post (e.g., professional, casual, inspirational, humorous, urgent). Defaults to 'professional'."
        },
        "platform": {
            "type": "string",
            "enum": [
                "twitter",
                "linkedin",
                "facebook",
                "instagram"
            ],
            "description": "The target social media platform. Each platform has different character limits and style conventions."
        },
        "target_audience": {
            "type": "string",
            "description": "Optional: Describe the target audience for the post (e.g., 'small business owners', 'teenagers', 'healthcare professionals')."
        },
        "max_characters": {
            "type": "integer",
            "minimum": 50,
            "maximum": 5000,
            "description": "Optional: The maximum number of characters for the generated post. For Twitter, the tool will automatically cap at 280."
        }
    },
    "required": [
        "topic",
        "platform"
    ]
},
}
