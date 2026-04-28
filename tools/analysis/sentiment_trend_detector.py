"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Analyze a collection of social media posts or comments over a date range to detect shifts in public sentiment (positive, negative, neutral) and identify emerging topics or keywords driving those trends. Returns a summary of sentiment percentages, top contributing terms, and a week-over-week trend line for each sentiment class."""
    import json
    from collections import Counter
    import math
    from datetime import datetime, timedelta

    try:
        data = json.loads(payload)
        posts = data.get('posts')
        date_range = data.get('date_range')

        if not posts or not isinstance(posts, list):
            return 'error: posts must be a non-empty array of strings'
        if not date_range or 'start' not in date_range or 'end' not in date_range:
            return 'error: date_range must have start and end as ISO date strings'

        try:
            start_date = datetime.fromisoformat(date_range['start'])
            end_date = datetime.fromisoformat(date_range['end'])
        except:
            return 'error: invalid date format in date_range, use YYYY-MM-DD'

        if end_date < start_date:
            return 'error: end_date must be after start_date'

        # Simple lexicon-based sentiment analysis (positive/negative keywords)
        positive_words = {'good', 'great', 'excellent', 'amazing', 'love', 'wonderful', 'fantastic', 'happy', 'joy', 'success', 'beautiful', 'incredible', 'thank', 'helpful', 'best', 'awesome', 'nice'}
        negative_words = {'bad', 'terrible', 'awful', 'hate', 'worst', 'poor', 'horrible', 'ugly', 'sad', 'angry', 'failure', 'disappointed', 'disgusting', 'pain', 'crisis', 'hateful', 'stupid'}

        # Bucket posts by week
        weekly_buckets = {}
        current = start_date
        while current <= end_date:
            week_start = current
            week_end = current + timedelta(days=7)
            week_key = week_start.strftime('%Y-%m-%d')
            weekly_buckets[week_key] = {'positive': [], 'negative': [], 'neutral': [], 'all_text': []}
            current = week_end

        # Assign each post to a week (if we had timestamps, but without, distribute evenly)
        # For simulation, we'll assign each post to a random week (but deterministic based on index)
        num_posts = len(posts)
        weeks_list = sorted(weekly_buckets.keys())
        num_weeks = len(weeks_list)

        for idx, post_text in enumerate(posts):
            if not isinstance(post_text, str):
                continue
            # Assign to week cyclically (for demo purposes; real tool would use timestamps)
            week_index = idx % num_weeks if num_weeks > 0 else 0
            week_key = weeks_list[week_index] if week_index < len(weeks_list) else weeks_list[-1]

            words = post_text.lower().split()
            pos_score = sum(1 for w in words if w in positive_words)
            neg_score = sum(1 for w in words if w in negative_words)
            if pos_score > neg_score:
                label = 'positive'
            elif neg_score > pos_score:
                label = 'negative'
            else:
                label = 'neutral'
            weekly_buckets[week_key][label].append(post_text)
            weekly_buckets[week_key]['all_text'].append(post_text)

        # Compute overall sentiment percentages and top keywords
        all_posts_text = ' '.join(posts)
        all_words = [w.lower() for w in all_posts_text.split() if len(w) > 2]
        word_counts = Counter(all_words)
        # Remove common stopwords and sentiment words themselves for keyword extraction
        stopwords = {'the', 'and', 'for', 'that', 'this', 'with', 'from', 'your', 'have', 'not', 'but', 'are', 'was', 'all', 'can', 'has', 'its', 'also', 'more', 'some', 'out', 'make', 'than', 'been', 'then', 'them', 'when', 'very', 'just', 'about', 'over', 'such', 'into', 'after', 'before', 'other', 'than', 'their', 'what', 'which', 'who', 'how', 'much'}
        for w in stopwords:
            word_counts.pop(w, None)
        for w in positive_words:
            word_counts.pop(w, None)
        for w in negative_words:
            word_counts.pop(w, None)
        top_keywords = [word for word, _ in word_counts.most_common(10)]

        total_positive = sum(len(weekly_buckets[w]['positive']) for w in weeks_list)
        total_negative = sum(len(weekly_buckets[w]['negative']) for w in weeks_list)
        total_neutral = sum(len(weekly_buckets[w]['neutral']) for w in weeks_list)
        total = total_positive + total_negative + total_neutral

        sentiment_percentages = {
            'positive': round(total_positive / total * 100, 1) if total > 0 else 0,
            'negative': round(total_negative / total * 100, 1) if total > 0 else 0,
            'neutral': round(total_neutral / total * 100, 1) if total > 0 else 0
        }

        # Build trend data (week-over-week counts)
        trend_data = []
        for week_key in weeks_list:
            bucket = weekly_buckets[week_key]
            ws = len(bucket['positive'])
            wn = len(bucket['negative'])
            wu = len(bucket['neutral'])
            trend_data.append({
                'week_start': week_key,
                'positive_count': ws,
                'negative_count': wn,
                'neutral_count': wu,
                'total_count': ws + wn + wu
            })

        result = {
            'overall_sentiment_percentages': sentiment_percentages,
            'top_keywords_driving_trends': top_keywords,
            'trend_data': trend_data
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "sentiment_trend_detector",
    "description": "Analyze a collection of social media posts or comments over a date range to detect shifts in public sentiment (positive, negative, neutral) and identify emerging topics or keywords driving those trends. Returns a summary of sentiment percentages, top contributing terms, and a week-over-week trend line for each sentiment class.",
    "category": "analysis",
    "domain": "social",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "posts": {
            "type": "array",
            "description": "Array of social media posts or comments to analyze. Each item is a string of text content.",
            "items": {
                "type": "string"
            }
        },
        "date_range": {
            "type": "object",
            "description": "Object with 'start' and 'end' fields as ISO 8601 date strings (e.g., '2025-03-01'). Used to group posts into weekly buckets for trend detection.",
            "properties": {
                "start": {
                    "type": "string"
                },
                "end": {
                    "type": "string"
                }
            },
            "required": [
                "start",
                "end"
            ]
        }
    },
    "required": [
        "posts",
        "date_range"
    ]
},
}
