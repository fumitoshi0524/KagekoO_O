"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a concise, inclusive community guideline summary for a social platform or group."""
    import json
    try:
        data = json.loads(payload)
        platform = data.get("platform_type", "community")
        values = data.get("core_values", [])
        rules = data.get("specific_rules", [])
        tone = data.get("tone", "balanced and inclusive")
        if not values:
            return json.dumps({"error": "At least one core value is required."}, ensure_ascii=False)
        tone_map = {
            "friendly and welcoming": "We warmly welcome everyone to our ",
            "professional and strict": "All members of our ",
            "playful": "Hey there, members of our awesome ",
            "balanced and inclusive": "Welcome to our "
        }
        opening = tone_map.get(tone, "Welcome to our ") + platform + "."
        values_text = "Our community is built on " + ", ".join(values) + "."
        if rules:
            rules_text = "Please remember: " + "; ".join(rules) + "."
        else:
            rules_text = "Be kind, stay respectful, and help us keep this space positive for everyone."
        closing = "Together, we make this community great!"
        summary = f"{opening} {values_text} {rules_text} {closing}"
        result = {
            "summary": summary,
            "character_count": len(summary),
            "sections": ["opening", "core_values", "rules", "closing"]
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "generate_community_guideline_summary",
    "description": "Generate a concise, inclusive community guideline summary for a social platform or group, based on provided core values, target audience, and specific rules or restrictions.",
    "category": "generate",
    "domain": "social",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "platform_type": {
            "type": "string",
            "description": "The type of social platform or community (e.g., 'professional network', 'gaming community', 'parenting forum', 'fan club').",
            "enum": [
                "professional network",
                "gaming community",
                "parenting forum",
                "fan club",
                "academic group",
                "local neighborhood",
                "hobby group",
                "other"
            ]
        },
        "core_values": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "List of 2-5 core values the community should uphold (e.g., 'respect', 'inclusivity', 'constructive feedback')."
        },
        "specific_rules": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "Optional: List of specific rules or restrictions to include (e.g., 'No self-promotion', 'No hate speech', 'Keep content family-friendly')."
        },
        "tone": {
            "type": "string",
            "description": "Optional: Desired tone for the guideline summary (e.g., 'friendly and welcoming', 'professional and strict', 'playful'). Default is 'balanced and inclusive'.",
            "default": "balanced and inclusive"
        }
    },
    "required": [
        "platform_type",
        "core_values"
    ]
},
}
