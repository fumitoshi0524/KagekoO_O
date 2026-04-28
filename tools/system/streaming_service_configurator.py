"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Configure and manage streaming service user preferences."""
    import json
    try:
        data = json.loads(payload)
        required = ["user_id", "video_quality_limit", "subtitle_language", "audio_language"]
        for field in required:
            if field not in data or data[field] is None:
                return json.dumps({"error": f"Missing required field: {field}"}, ensure_ascii=False)

        user_id = data["user_id"]
        video_quality = data["video_quality_limit"]
        sub_lang = data["subtitle_language"]
        audio_lang = data["audio_language"]
        pc_rating = data.get("parental_control_max_rating", "")
        autoplay_ep = data.get("autoplay_next_episode", True)
        autoplay_pre = data.get("autoplay_previews", False)

        allowed_qualities = ["sd", "hd", "fhd", "uhd"]
        if video_quality not in allowed_qualities:
            return json.dumps({"error": f"Invalid video quality. Must be one of {allowed_qualities}"}, ensure_ascii=False)

        import re
        if not re.match(r'^[a-z]{2}$', sub_lang):
            return json.dumps({"error": "Subtitle language must be a 2-letter ISO code"}, ensure_ascii=False)
        if not re.match(r'^[a-z]{2}$', audio_lang):
            return json.dumps({"error": "Audio language must be a 2-letter ISO code"}, ensure_ascii=False)

        allowed_ratings = ["G", "PG", "PG-13", "R", "NC-17", ""]
        if pc_rating not in allowed_ratings:
            return json.dumps({"error": f"Invalid rating. Must be one of {allowed_ratings}"}, ensure_ascii=False)

        result = {
            "status": "success",
            "user_id": user_id,
            "configured_settings": {
                "video_quality_limit": video_quality,
                "subtitle_language": sub_lang,
                "audio_language": audio_lang,
                "parental_control_max_rating": pc_rating if pc_rating else "no_restriction",
                "autoplay_next_episode": autoplay_ep,
                "autoplay_previews": autoplay_pre
            }
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "streaming_service_configurator",
    "description": "Configure and manage streaming service user preferences, including video quality limits, subtitle defaults, language settings, and parental control restrictions for the specified user account.",
    "category": "system",
    "domain": "entertainment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "user_id": {
            "type": "string",
            "description": "Unique identifier for the user account to apply the configuration to."
        },
        "video_quality_limit": {
            "type": "string",
            "description": "Maximum allowed streaming video quality.",
            "enum": [
                "sd",
                "hd",
                "fhd",
                "uhd"
            ]
        },
        "subtitle_language": {
            "type": "string",
            "description": "Default subtitle language code (ISO 639-1, e.g. 'en', 'fr', 'es').",
            "pattern": "^[a-z]{2}$"
        },
        "audio_language": {
            "type": "string",
            "description": "Default audio language code (ISO 639-1, e.g. 'en', 'de', 'ja').",
            "pattern": "^[a-z]{2}$"
        },
        "parental_control_max_rating": {
            "type": "string",
            "description": "Optional: Maximum content age rating allowed for this account. Leave empty for no restriction.",
            "enum": [
                "G",
                "PG",
                "PG-13",
                "R",
                "NC-17",
                ""
            ]
        },
        "autoplay_next_episode": {
            "type": "boolean",
            "description": "Optional: Enable or disable automatic playback of the next episode in a series."
        },
        "autoplay_previews": {
            "type": "boolean",
            "description": "Optional: Enable or disable automatic preview playback while browsing content."
        }
    },
    "required": [
        "user_id",
        "video_quality_limit",
        "subtitle_language",
        "audio_language"
    ]
},
}
