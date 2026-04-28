"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    import datetime
    try:
        data = json.loads(payload)
        asset_id = data.get("asset_id")
        platform = data.get("platform")
        region = data.get("region", "US")
        if not asset_id or not platform:
            return json.dumps({"error": "Missing required fields: asset_id and platform"})
        valid_platforms = ["Netflix", "Spotify", "Steam", "Apple_TV", "HBO_Max", "Amazon_Prime"]
        if platform not in valid_platforms:
            return json.dumps({"error": f"Invalid platform '{platform}'. Must be one of {valid_platforms}"})
        # Simulate DRM license lookup (real system would query external service)
        # For demonstration, generate deterministic but realistic-looking data
        seed = hash(asset_id + platform + region)
        is_licensed = (seed % 100) > 20  # 80% chance licensed for demo
        if not is_licensed:
            result = {
                "asset_id": asset_id,
                "platform": platform,
                "region": region,
                "clearance": False,
                "message": "No valid license found for this asset on the specified platform.",
                "checked_at": datetime.datetime.utcnow().isoformat() + "Z"
            }
        else:
            # Generate plausible expiration date 6-36 months from now
            days_valid = 180 + (seed % 540)
            expiry = datetime.datetime.utcnow() + datetime.timedelta(days=days_valid)
            result = {
                "asset_id": asset_id,
                "platform": platform,
                "region": region,
                "clearance": True,
                "expires_at": expiry.isoformat() + "Z",
                "license_type": "global",
                "message": "License is valid and active.",
                "checked_at": datetime.datetime.utcnow().isoformat() + "Z"
            }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "drm_license_clearance",
    "description": "Verifies and reports on DRM licensing status for digital media assets (movies, music, games) across configured distribution platforms, returning clearance flags and expiration dates.",
    "category": "system",
    "domain": "entertainment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "asset_id": {
            "type": "string",
            "description": "Unique identifier for the media asset (e.g., movie UUID, music ISRC, game Steam AppID)."
        },
        "platform": {
            "type": "string",
            "description": "Distribution platform to check (e.g., Netflix, Spotify, Steam, Apple TV). Enum values represent supported platforms.",
            "enum": [
                "Netflix",
                "Spotify",
                "Steam",
                "Apple_TV",
                "HBO_Max",
                "Amazon_Prime"
            ]
        },
        "region": {
            "type": "string",
            "description": "Optional: ISO 3166-1 alpha-2 country code (e.g., 'US', 'DE') to check region-specific licensing.",
            "default": "US"
        }
    },
    "required": [
        "asset_id",
        "platform"
    ]
},
}
