"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Search for social media posts by keyword, author, hashtags, and date range."""
    import json
    import datetime
    import random

    try:
        data = json.loads(payload)

        # Validate required keyword
        keyword = data.get('keyword')
        if not keyword or not isinstance(keyword, str):
            return json.dumps({'error': 'Missing or invalid required parameter: keyword must be a non-empty string'})

        # Default platform list if not provided
        all_platforms = ['twitter', 'reddit', 'linkedin', 'instagram', 'facebook', 'tiktok', 'youtube']
        platforms = data.get('platforms', all_platforms)
        if not isinstance(platforms, list):
            return json.dumps({'error': 'platforms must be a list of strings'})
        # Validate each platform
        for p in platforms:
            if p not in all_platforms:
                return json.dumps({'error': f'Invalid platform: {p}. Must be one of {all_platforms}'})
        if not platforms:
            return json.dumps({'error': 'platforms list cannot be empty'})

        # Validate optional author
        author = data.get('author')
        if author is not None and not isinstance(author, str):
            return json.dumps({'error': 'author must be a string'})

        # Validate optional hashtags
        hashtags = data.get('hashtags')
        if hashtags is not None:
            if not isinstance(hashtags, list):
                return json.dumps({'error': 'hashtags must be a list of strings'})
            for h in hashtags:
                if not isinstance(h, str):
                    return json.dumps({'error': 'Each hashtag must be a string'})

        # Validate optional date_from and date_to
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        if date_from is not None:
            try:
                datetime.datetime.strptime(date_from, '%Y-%m-%d')
            except ValueError:
                return json.dumps({'error': 'date_from must be in YYYY-MM-DD format'})
        if date_to is not None:
            try:
                datetime.datetime.strptime(date_to, '%Y-%m-%d')
            except ValueError:
                return json.dumps({'error': 'date_to must be in YYYY-MM-DD format'})

        # Validate max_results
        max_results = data.get('max_results', 20)
        if not isinstance(max_results, int) or max_results < 1 or max_results > 100:
            return json.dumps({'error': 'max_results must be an integer between 1 and 100'})

        # Simulated search logic: generate realistic fake posts matching criteria
        sample_authors = {
            'twitter': ['@techguru', '@datawhisperer', '@ai_enthusiast', '@devlife', '@socialanalyst'],
            'reddit': ['u/deep_learner', 'u/data_scientist_42', 'u/ml_ninja', 'u/pythoneer', 'u/stat_kid'],
            'linkedin': ['Dr. Jane Smith', 'Alex Johnson', 'Maria Garcia', 'Chris Lee', 'Samira Patel'],
            'instagram': ['@travel_bug', '@foodie_jen', '@fitness_freak', '@art_lover', '@coder_life'],
            'facebook': ['John Doe', 'Emily White', 'David Brown', 'Sophia Miller', 'James Wilson'],
            'tiktok': ['@dance_queen', '@comedy_king', '@tech_tips', '@pet_lover', '@cook_master'],
            'youtube': ['TechReviewer', 'CookingWithAnna', 'FitnessGuru', 'TravelVlogger', 'DiYPro']
        }

        # Generate posts
        posts = []
        for platform in platforms:
            # Generate a random number of posts per platform (1 to 10)
            count = random.randint(1, min(10, max_results - len(posts) + 1))
            for _ in range(count):
                if len(posts) >= max_results:
                    break
                # Random date in last 30 days
                days_ago = random.randint(0, 30)
                post_date = datetime.datetime.now() - datetime.timedelta(days=days_ago)
                # Apply date filters if provided
                if date_from:
                    date_from_dt = datetime.datetime.strptime(date_from, '%Y-%m-%d')
                    if post_date < date_from_dt:
                        continue
                if date_to:
                    date_to_dt = datetime.datetime.strptime(date_to, '%Y-%m-%d') + datetime.timedelta(days=1)
                    if post_date >= date_to_dt:
                        continue

                # Random author from platform
                authors = sample_authors.get(platform, ['unknown'])
                post_author = random.choice(authors)
                # Filter by author if specified
                if author and author.lower() not in post_author.lower():
                    continue

                # Generate a post snippet containing keyword
                snippet_templates = [
                    f"Just discovered an interesting topic about {keyword}. Really insightful!",
                    f"Anyone else following the latest developments in {keyword}?",
                    f"My take on {keyword}: it's transformative for our industry.",
                    f"Excited to share my new article about {keyword}. Check it out!",
                    f"Can't believe how much {keyword} is changing the way we work.",
                    f"Asked a question about {keyword} — looking for expert opinions.",
                    f"{keyword} is trending! Here's what you need to know.",
                    f"Honest review: {keyword} tools after 6 months of use.",
                    f"Thread: Breaking down the impact of {keyword} on society.",
                    f"Day 30 of learning about {keyword}. Here's my summary."
                ]
                snippet = random.choice(snippet_templates)

                # Random hashtags (may include user-provided hashtags)
                post_hashtags = []
                if hashtags:
                    # Include provided hashtags
                    for h in hashtags:
                        if random.random() > 0.5:
                            post_hashtags.append(h)
                # Generate additional random hashtags
                for _ in range(random.randint(0, 3)):
                    random_tags = ['tech', 'innovation', 'data', 'AI', 'future', 'learning', 'community', 'trending']
                    tag = random.choice(random_tags)
                    if random.random() > 0.7 and tag not in post_hashtags:
                        post_hashtags.append(tag)

                # Engagement metrics
                likes = random.randint(0, 5000)
                shares = random.randint(0, 1000)
                comments = random.randint(0, 500)

                post = {
                    'platform': platform,
                    'author': post_author,
                    'snippet': snippet,
                    'timestamp': post_date.strftime('%Y-%m-%d %H:%M:%S'),
                    'hashtags': post_hashtags,
                    'engagement': {
                        'likes': likes,
                        'shares': shares,
                        'comments': comments
                    },
                    'url': f"https://{platform}.com/post/{random.randint(100000, 999999)}"
                }
                posts.append(post)

        # If no posts generated, return empty list
        result = {
            'query': {
                'keyword': keyword,
                'platforms': platforms,
                'author': author,
                'hashtags': hashtags,
                'date_from': date_from,
                'date_to': date_to,
                'max_results': max_results
            },
            'total_results': len(posts),
            'posts': posts
        }

        return json.dumps(result, ensure_ascii=False)

    except json.JSONDecodeError as e:
        return json.dumps({'error': f'Invalid JSON payload: {str(e)}'})
    except Exception as e:
        return json.dumps({'error': f'Unexpected error: {str(e)}'})


TOOL_SPEC = {
    "name": "social_media_post_finder",
    "description": "Search for social media posts across multiple platforms by keyword, author, date range, and hashtag. Returns a list of matching posts with platform, author, content snippet, timestamp, and engagement metrics (likes, shares, comments). Used for social listening, trend analysis, and content discovery.",
    "category": "search",
    "domain": "social",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "keyword": {
            "type": "string",
            "description": "The search term or phrase to match in post content, title, or description."
        },
        "platforms": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [
                    "twitter",
                    "reddit",
                    "linkedin",
                    "instagram",
                    "facebook",
                    "tiktok",
                    "youtube"
                ]
            },
            "description": "Optional: List of social media platforms to search. Defaults to all supported platforms."
        },
        "author": {
            "type": "string",
            "description": "Optional: Filter posts by a specific author username or handle."
        },
        "hashtags": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "Optional: List of hashtags to filter posts (without # symbol)."
        },
        "date_from": {
            "type": "string",
            "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
            "description": "Optional: Start date for filtering posts (ISO 8601 format, e.g., 2024-01-01)."
        },
        "date_to": {
            "type": "string",
            "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
            "description": "Optional: End date for filtering posts (ISO 8601 format, e.g., 2024-12-31)."
        },
        "max_results": {
            "type": "integer",
            "minimum": 1,
            "maximum": 100,
            "default": 20,
            "description": "Optional: Maximum number of posts to return (1-100, default 20)."
        }
    },
    "required": [
        "keyword"
    ]
},
}
