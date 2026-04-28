"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Analyze a social media community or group's health by evaluating member engagement, post frequency, toxic behavior reports, and growth trends to return a structured health score and actionable insights."""
    import json
    try:
        data = json.loads(payload)
        community_id = data['community_id']
        member_count = data['member_count']
        posts_last_week = data['posts_last_week']
        active_last_week = data['active_members_last_week']
        toxic_reports = data.get('toxic_reports_last_week', 0)
        joined = data['new_members_joined_last_week']
        left = data['members_left_last_week']

        if member_count == 0:
            return json.dumps({"error": "member_count must be greater than 0", "community_id": community_id})

        engagement_rate = (active_last_week / member_count) * 100
        post_intensity = posts_last_week / max(active_last_week, 1)
        churn_rate = (left / (member_count + joined)) * 100 if (member_count + joined) > 0 else 0
        growth_rate = ((joined - left) / member_count) * 100
        tox_per_1000 = (toxic_reports / member_count) * 1000

        # Score components (0-100 each)
        engagement_score = min(100, engagement_rate * 2)
        intensity_score = min(100, post_intensity * 10)
        churn_score = max(0, 100 - churn_rate * 10)
        growth_score = min(100, max(0, growth_rate * 5))
        tox_score = max(0, 100 - tox_per_1000 * 20)

        health_score = round((engagement_score * 0.25) + (intensity_score * 0.2) + (churn_score * 0.2) + (growth_score * 0.2) + (tox_score * 0.15), 2)

        if health_score >= 80:
            status = "healthy"
        elif health_score >= 50:
            status = "moderate"
        else:
            status = "critical"

        insights = []
        if engagement_rate < 10:
            insights.append("Low member engagement: consider interactive events or Q&A sessions.")
        if churn_rate > 20:
            insights.append("High churn rate: investigate member satisfaction via polls or feedback.")
        if growth_rate < -5:
            insights.append("Negative growth: community is shrinking; check onboarding experience.")
        if tox_per_1000 > 5:
            insights.append("Elevated toxicity reports: strengthen moderation rules or auto-moderation.")
        if post_intensity < 0.5:
            insights.append("Low posting frequency per active member: encourage content creation or prompts.")

        result = {
            "community_id": community_id,
            "health_score": health_score,
            "status": status,
            "metrics": {
                "engagement_rate_pct": round(engagement_rate, 2),
                "post_intensity": round(post_intensity, 2),
                "churn_rate_pct": round(churn_rate, 2),
                "growth_rate_pct": round(growth_rate, 2),
                "toxicity_rate_per_1000": round(tox_per_1000, 2)
            },
            "insights": insights
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})



TOOL_SPEC = {
    "name": "community_health_check",
    "description": "Analyze a social media community or group's health by evaluating member engagement, post frequency, toxic behavior reports, and growth trends to return a structured health score and actionable insights.",
    "category": "system",
    "domain": "social",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "community_id": {
            "type": "string",
            "description": "Unique identifier for the social community or group to be analyzed (e.g., Discord server ID, Telegram group ID, subreddit name)."
        },
        "member_count": {
            "type": "integer",
            "description": "Current total number of members in the community.",
            "minimum": 0
        },
        "posts_last_week": {
            "type": "integer",
            "description": "Number of posts or messages sent in the last 7 days.",
            "minimum": 0
        },
        "active_members_last_week": {
            "type": "integer",
            "description": "Number of unique members who posted or reacted in the last 7 days.",
            "minimum": 0
        },
        "toxic_reports_last_week": {
            "type": "integer",
            "description": "Optional: Number of user reports flagged as toxic or spam in the last 7 days. If omitted, defaults to 0.",
            "minimum": 0
        },
        "new_members_joined_last_week": {
            "type": "integer",
            "description": "Number of new members who joined the community in the last 7 days.",
            "minimum": 0
        },
        "members_left_last_week": {
            "type": "integer",
            "description": "Number of members who left the community in the last 7 days.",
            "minimum": 0
        }
    },
    "required": [
        "community_id",
        "member_count",
        "posts_last_week",
        "active_members_last_week",
        "new_members_joined_last_week",
        "members_left_last_week"
    ]
},
}
