"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Analyze sentiment trends in social media posts over time."""
    import json
    from datetime import datetime, timedelta
    from collections import defaultdict
    import math

    try:
        data = json.loads(payload)
        texts = data.get("texts", [])
        granularity = data.get("granularity", "daily")

        if not texts:
            return json.dumps({"error": "No texts provided"}, ensure_ascii=False)

        # Simple keyword-based sentiment analysis (simulating NLP)
        positive_words = {"good", "great", "excellent", "amazing", "love", "wonderful", "fantastic", "happy", "positive", "best", "awesome", "beautiful"}
        negative_words = {"bad", "terrible", "awful", "hate", "horrible", "worst", "ugly", "sad", "angry", "disappointed", "poor", "negative"}

        # Parse timestamps and group by granularity
        grouped = defaultdict(lambda: {"positive": 0, "negative": 0, "neutral": 0, "count": 0, "total_score": 0.0})

        for item in texts:
            content = item.get("content", "").lower()
            ts_str = item.get("timestamp", "")

            try:
                ts = datetime.fromisoformat(ts_str)
            except (ValueError, TypeError):
                continue

            # Normalize timestamp to granularity period
            if granularity == "hourly":
                period = ts.replace(minute=0, second=0, microsecond=0).isoformat()
            elif granularity == "daily":
                period = ts.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
            elif granularity == "weekly":
                # Align to start of week (Monday)
                start = ts - timedelta(days=ts.weekday())
                period = start.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
            elif granularity == "monthly":
                period = ts.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
            else:
                period = ts.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

            # Analyze sentiment
            words = content.split()
            score = 0.0
            for word in words:
                if word in positive_words:
                    score += 1.0
                elif word in negative_words:
                    score -= 1.0

            if score > 0:
                grouped[period]["positive"] += 1
            elif score < 0:
                grouped[period]["negative"] += 1
            else:
                grouped[period]["neutral"] += 1

            grouped[period]["count"] += 1
            grouped[period]["total_score"] += score

        # Build time-ordered results
        sorted_periods = sorted(grouped.keys())
        trend_data = []
        for period in sorted_periods:
            g = grouped[period]
            total = g["count"]
            avg_score = round(g["total_score"] / total, 2) if total > 0 else 0.0
            pos_pct = round((g["positive"] / total) * 100, 1) if total > 0 else 0.0
            neg_pct = round((g["negative"] / total) * 100, 1) if total > 0 else 0.0
            neu_pct = round((g["neutral"] / total) * 100, 1) if total > 0 else 0.0

            trend_data.append({
                "period": period,
                "total_posts": total,
                "positive_pct": pos_pct,
                "negative_pct": neg_pct,
                "neutral_pct": neu_pct,
                "average_sentiment_score": avg_score
            })

        # Calculate overall trend direction
        if len(trend_data) >= 2:
            first_score = trend_data[0]["average_sentiment_score"]
            last_score = trend_data[-1]["average_sentiment_score"]
            if last_score > first_score + 0.1:
                direction = "improving"
            elif last_score < first_score - 0.1:
                direction = "declining"
            else:
                direction = "stable"
        else:
            direction = "insufficient_data"

        # Find peak activity period
        max_posts = max(t["total_posts"] for t in trend_data) if trend_data else 0
        peak_periods = [t["period"] for t in trend_data if t["total_posts"] == max_posts]

        result = {
            "granularity": granularity,
            "trend_data": trend_data,
            "overall_trend_direction": direction,
            "peak_activity_periods": peak_periods,
            "total_analyzed": sum(t["total_posts"] for t in trend_data),
            "periods_analyzed": len(trend_data)
        }

        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "sentiment_trend_analysis",
    "description": "Analyze sentiment trends in social media posts or comments over a specified time period. Returns aggregated sentiment scores (positive, negative, neutral), trend direction, and peak activity periods for brand monitoring or community health assessment.",
    "category": "analysis",
    "domain": "social",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "texts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The text content of a social media post or comment to analyze."
                    },
                    "timestamp": {
                        "type": "string",
                        "description": "ISO 8601 datetime string representing when the content was posted."
                    }
                },
                "required": [
                    "content",
                    "timestamp"
                ]
            },
            "description": "Array of social media content items with their associated timestamps."
        },
        "granularity": {
            "type": "string",
            "enum": [
                "hourly",
                "daily",
                "weekly",
                "monthly"
            ],
            "description": "Time granularity for grouping sentiment analysis results."
        }
    },
    "required": [
        "texts",
        "granularity"
    ]
},
}
