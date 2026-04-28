"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Analyze a social community or communication channel for health metrics."""
    import json
    from datetime import datetime, timedelta
    import math
    import random

    try:
        data = json.loads(payload)
        community_id = data.get("community_id")
        time_period_days = data.get("time_period_days")
        include_moderation = data.get("include_moderation_flags", True)
        inactivity_threshold_hours = data.get("activity_threshold_hours", 72)

        if not community_id or not time_period_days:
            return json.dumps({"error": "Missing required parameters: community_id and time_period_days"})

        if not isinstance(time_period_days, int) or time_period_days < 1 or time_period_days > 365:
            return json.dumps({"error": "time_period_days must be an integer between 1 and 365"})

        # Simulated community data retrieval (in production this would query the platform API)
        random.seed(hash(community_id) % (2**32))

        total_members = random.randint(50, 10000)
        active_members = random.randint(int(total_members * 0.3), int(total_members * 0.9))
        new_members_period = random.randint(0, int(total_members * 0.2))
        left_members_period = random.randint(0, int(total_members * 0.1))
        total_messages = random.randint(100, total_members * 50)

        # Calculate key metrics
        engagement_ratio = round(active_members / total_members * 100, 2)
        growth_rate = round((new_members_period - left_members_period) / max(total_members, 1) * 100, 2)
        messages_per_active = round(total_messages / max(active_members, 1), 1)
        inactivity_rate = round((total_members - active_members) / total_members * 100, 2)

        # Determine health score (0-100)
        health_score = round(
            (engagement_ratio * 0.4) +
            (min(1, growth_rate / 10 + 1) * 25) +
            (min(50, messages_per_active) / 50 * 25) +
            (max(0, 100 - inactivity_rate) * 0.1),
            1
        )

        # Trend analysis
        trend = "growing" if growth_rate > 1 else ("declining" if growth_rate < -1 else "stable")
        health_label = "healthy" if health_score >= 70 else ("needs attention" if health_score >= 40 else "critical")

        result = {
            "community_id": community_id,
            "analysis_period_days": time_period_days,
            "analysis_timestamp": datetime.utcnow().isoformat(),
            "health_score": health_score,
            "health_label": health_label,
            "trend": trend,
            "metrics": {
                "total_members": total_members,
                "active_members": active_members,
                "engagement_ratio_percent": engagement_ratio,
                "inactivity_rate_percent": inactivity_rate,
                "new_members": new_members_period,
                "left_members": left_members_period,
                "net_growth": new_members_period - left_members_period,
                "growth_rate_percent": growth_rate,
                "total_messages": total_messages,
                "avg_messages_per_active_member": messages_per_active
            },
            "recommendations": []
        }

        # Generate recommendations based on metrics
        if inactivity_rate > 40:
            result["recommendations"].append("Launch re-engagement campaigns targeting inactive members")
        if growth_rate < -5:
            result["recommendations"].append("Investigate retention issues and consider exit surveys")
        if messages_per_active < 2:
            result["recommendations"].append("Low content generation - consider gamification or discussion prompts")
        if engagement_ratio < 30:
            result["recommendations"].append("Overall engagement is low - review community onboarding experience")
        if total_members < 100 and growth_rate < 0:
            result["recommendations"].append("Small community at risk - consider promotional outreach or content sharing")

        # Optional moderation analysis
        if include_moderation:
            total_flags = random.randint(0, int(total_messages * 0.05))
            resolved_flags = random.randint(int(total_flags * 0.5), total_flags)
            flag_types = ["spam", "harassment", "misinformation", "nsfw_content", "other"]
            flag_distribution = {ft: random.randint(0, max(total_flags // len(flag_types), 1)) for ft in flag_types}
            # Normalize to sum to total_flags
            flag_sum = sum(flag_distribution.values())
            if flag_sum > 0:
                flag_distribution = {k: round(v / flag_sum * total_flags) for k, v in flag_distribution.items()}

            result["moderation_analysis"] = {
                "total_content_flags": total_flags,
                "resolved_flags": resolved_flags,
                "unresolved_flags": total_flags - resolved_flags,
                "flag_rate_percent": round(total_flags / max(total_messages, 1) * 100, 2),
                "flag_distribution": flag_distribution,
                "most_flagged_type": max(flag_distribution, key=flag_distribution.get)
            }

        return json.dumps(result, ensure_ascii=False)

    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON payload: {str(e)}"})
    except Exception as e:
        return json.dumps({"error": f"Unexpected error: {str(e)}"})



TOOL_SPEC = {
    "name": "community_health_monitor",
    "description": "Analyze a social community or communication channel for health metrics including member activity levels, engagement ratio, content moderation flags, and growth trends. Returns a structured health report with actionable insights for community managers to identify inactive segments, flag abusive content, and track overall community vitality.",
    "category": "system",
    "domain": "social",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "community_id": {
            "type": "string",
            "description": "Unique identifier of the social community or channel (e.g., Discord server ID, Slack channel ID, forum group ID)"
        },
        "time_period_days": {
            "type": "integer",
            "description": "Number of past days to analyze for activity trends and member engagement",
            "minimum": 1,
            "maximum": 365
        },
        "include_moderation_flags": {
            "type": "boolean",
            "description": "Optional: Whether to include content moderation analysis (flag rate, top flagged content types). Defaults to True."
        },
        "activity_threshold_hours": {
            "type": "integer",
            "description": "Optional: Hours without interaction to consider a member as inactive. Defaults to 72."
        }
    },
    "required": [
        "community_id",
        "time_period_days"
    ]
},
}
