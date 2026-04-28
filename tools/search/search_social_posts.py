"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Search across social media posts by keyword, author, or date range."""
    import json
    from datetime import datetime

    try:
        data = json.loads(payload)
        query = data.get('query', '').strip()
        author = data.get('author', '').strip() or None
        start_date = data.get('start_date', '').strip() or None
        end_date = data.get('end_date', '').strip() or None
        sort_by = data.get('sort_by', 'relevance').strip()
        limit = data.get('limit', 20)

        if not query or len(query) < 2:
            return json.dumps({'error': 'Query must be at least 2 characters'}, ensure_ascii=False)

        if start_date:
            try:
                datetime.strptime(start_date, '%Y-%m-%d')
            except ValueError:
                return json.dumps({'error': 'start_date must be in YYYY-MM-DD format'}, ensure_ascii=False)

        if end_date:
            try:
                datetime.strptime(end_date, '%Y-%m-%d')
            except ValueError:
                return json.dumps({'error': 'end_date must be in YYYY-MM-DD format'}, ensure_ascii=False)

        if sort_by not in ['relevance', 'date_desc', 'date_asc', 'engagement']:
            sort_by = 'relevance'

        if not isinstance(limit, int) or limit < 1:
            limit = 20
        limit = min(limit, 100)

        # Mock data for demonstration (in production, query a real database or API)
        mock_posts = [
            {"id": "post_001", "author": "john_doe", "content": "Exploring new #AI tools for social media marketing", "timestamp": "2025-04-10T14:23:00", "hashtags": ["AI", "marketing"], "likes": 45, "shares": 12, "engagement_score": 57},
            {"id": "post_002", "author": "jane_smith", "content": "Just finished reading a great book on #community building", "timestamp": "2025-04-09T09:15:00", "hashtags": ["community", "books"], "likes": 30, "shares": 8, "engagement_score": 38},
            {"id": "post_003", "author": "tech_guru", "content": "Our new AI #chatbot just launched! Try it now", "timestamp": "2025-04-08T18:45:00", "hashtags": ["AI", "chatbot", "launch"], "likes": 120, "shares": 45, "engagement_score": 165},
            {"id": "post_004", "author": "social_media_pro", "content": "5 tips for increasing #engagement on your timeline", "timestamp": "2025-04-07T11:30:00", "hashtags": ["engagement", "socialmedia"], "likes": 67, "shares": 22, "engagement_score": 89},
            {"id": "post_005", "author": "john_doe", "content": "Behind the scenes of our #AI project #teamwork", "timestamp": "2025-04-06T20:00:00", "hashtags": ["AI", "teamwork"], "likes": 89, "shares": 30, "engagement_score": 119},
        ]

        # Filter by query (case-insensitive content or hashtag match)
        query_lower = query.lower()
        results = []
        for post in mock_posts:
            if query_lower in post["content"].lower():
                matches_query = True
            elif any(query_lower in tag.lower() for tag in post["hashtags"]):
                matches_query = True
            else:
                matches_query = False

            if not matches_query:
                continue

            if author and post["author"] != author:
                continue

            post_date = post["timestamp"][:10]
            if start_date and post_date < start_date:
                continue
            if end_date and post_date > end_date:
                continue

            results.append(post)

        # Sort results
        if sort_by == 'date_desc':
            results.sort(key=lambda x: x['timestamp'], reverse=True)
        elif sort_by == 'date_asc':
            results.sort(key=lambda x: x['timestamp'])
        elif sort_by == 'engagement':
            results.sort(key=lambda x: x['engagement_score'], reverse=True)
        else:  # relevance - keep original order (mock relevance scoring)
            pass

        # Apply limit
        results = results[:limit]

        return json.dumps({
            "query": query,
            "total_found": len(results),
            "results": results
        }, ensure_ascii=False)

    except json.JSONDecodeError:
        return json.dumps({'error': 'Invalid JSON payload'}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': f'Internal error: {str(e)}'}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "search_social_posts",
    "description": "Search across social media posts by keyword, author, or date range, returning matching posts with metadata such as timestamp, like count, and engagement score for content discovery and trend analysis.",
    "category": "search",
    "domain": "social",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Keyword or phrase to search for in post content and hashtags (minimum 2 characters)."
        },
        "author": {
            "type": "string",
            "description": "Optional: Filter posts by author username or user ID (case-sensitive exact match)."
        },
        "start_date": {
            "type": "string",
            "description": "Optional: Earliest post date to include, format YYYY-MM-DD."
        },
        "end_date": {
            "type": "string",
            "description": "Optional: Latest post date to include, format YYYY-MM-DD."
        },
        "sort_by": {
            "type": "string",
            "enum": [
                "relevance",
                "date_desc",
                "date_asc",
                "engagement"
            ],
            "description": "Optional: Sort order for results - relevance (default), date_desc, date_asc, or engagement (by like count descending)."
        },
        "limit": {
            "type": "integer",
            "description": "Optional: Maximum number of results to return (between 1 and 100, default 20).",
            "minimum": 1,
            "maximum": 100
        }
    },
    "required": [
        "query"
    ]
},
}
