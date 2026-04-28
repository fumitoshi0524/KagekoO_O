"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        asset_id = data.get('asset_id')
        asset_type = data.get('asset_type')
        territory = data.get('territory')
        if not asset_id or not asset_type:
            return json.dumps({'error': 'asset_id and asset_type are required'})
        # Built-in rights database (simulated for demo)
        rights_db = {
            'US123456789': {
                'type': 'music',
                'title': 'Sunset Boulevard',
                'artist': 'The Horizons',
                'licensing_status': 'active',
                'allowed_uses': ['streaming', 'broadcast', 'sync'],
                'territorial_restrictions': {'US': {'streaming': True, 'broadcast': True}, 'DE': {'streaming': True, 'broadcast': False}},
                'expiration': '2026-12-31'
            },
            'DE987654321': {
                'type': 'video',
                'title': 'Neon Nights',
                'director': 'Elena Voss',
                'licensing_status': 'active',
                'allowed_uses': ['streaming', 'download'],
                'territorial_restrictions': {'DE': {'streaming': True, 'download': True}, 'US': {'streaming': False}},
                'expiration': '2025-06-30'
            },
            'GAME001': {
                'type': 'game_asset',
                'title': 'Dragon Sword Model',
                'licensing_status': 'expired',
                'allowed_uses': [],
                'territorial_restrictions': {},
                'expiration': '2023-03-15'
            }
        }
        if asset_id not in rights_db:
            return json.dumps({'error': 'Asset not found in rights database', 'asset_id': asset_id})
        record = rights_db[asset_id]
        if record['type'] != asset_type:
            return json.dumps({'error': 'Asset type mismatch', 'expected': record['type'], 'provided': asset_type})
        result = {
            'asset_id': asset_id,
            'asset_type': record['type'],
            'title': record.get('title', record.get('director', 'Unknown')),
            'licensing_status': record['licensing_status'],
            'allowed_uses': record['allowed_uses'],
            'expiration': record['expiration'],
            'territory_checked': territory if territory else 'global',
            'territorial_allowed': record['territorial_restrictions'].get(territory, {}) if territory else record['territorial_restrictions']
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)})


TOOL_SPEC = {
    "name": "media_license_checker",
    "description": "Verifies the licensing status and rights management of digital media assets (music tracks, video content, game assets) against a built-in rights database, returning licensing status, allowed use types, territorial restrictions, and expiration dates for compliance auditing.",
    "category": "system",
    "domain": "entertainment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "asset_id": {
            "type": "string",
            "description": "Unique identifier of the media asset (e.g., ISRC for music, EIDR for video, or internal asset code)."
        },
        "asset_type": {
            "type": "string",
            "enum": [
                "music",
                "video",
                "game_asset",
                "image"
            ],
            "description": "Category of the media asset to check licensing for."
        },
        "territory": {
            "type": "string",
            "description": "Optional: ISO 3166-1 alpha-2 country code to filter territorial license restrictions (e.g., 'US', 'DE', 'JP'). If omitted, returns global status."
        }
    },
    "required": [
        "asset_id",
        "asset_type"
    ]
},
}
