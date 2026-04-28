"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    import uuid
    from datetime import datetime
    try:
        data = json.loads(payload)
        required = ['festival_id', 'entry_title', 'category', 'artist_name', 'artist_email', 'description', 'media_type']
        for field in required:
            if field not in data or not data[field]:
                return json.dumps({'error': f'Missing required field: {field}'}, ensure_ascii=False)
        valid_categories = ['visual_arts', 'performing_arts', 'literature', 'music', 'film', 'crafts']
        if data['category'] not in valid_categories:
            return json.dumps({'error': f'Invalid category. Must be one of {valid_categories}'}, ensure_ascii=False)
        valid_media = ['image', 'audio', 'video', 'document', 'other']
        if data['media_type'] not in valid_media:
            return json.dumps({'error': f'Invalid media_type. Must be one of {valid_media}'}, ensure_ascii=False)
        submission_id = 'SUB-' + uuid.uuid4().hex[:8].upper()
        result = {
            'submission_id': submission_id,
            'festival_id': data['festival_id'],
            'entry_title': data['entry_title'],
            'category': data['category'],
            'artist_name': data['artist_name'],
            'artist_email': data['artist_email'],
            'artist_phone': data.get('artist_phone', ''),
            'description': data['description'],
            'media_type': data['media_type'],
            'media_url': data.get('media_url', ''),
            'status': 'submitted',
            'submitted_at': datetime.utcnow().isoformat() + 'Z'
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "cultural_festival_submissions",
    "description": "Manage and track submissions for cultural festival events, including entry details, artist information, media files, and festival categories. Returns the submitted entry record with a submission ID for reference and confirmation.",
    "category": "system",
    "domain": "culture",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "festival_id": {
            "type": "string",
            "description": "Unique identifier of the cultural festival (e.g., 'FEST2025-01')."
        },
        "entry_title": {
            "type": "string",
            "description": "Title of the artistic entry (e.g., painting, performance, installation)."
        },
        "category": {
            "type": "string",
            "enum": [
                "visual_arts",
                "performing_arts",
                "literature",
                "music",
                "film",
                "crafts"
            ],
            "description": "Festival category the entry belongs to."
        },
        "artist_name": {
            "type": "string",
            "description": "Full name of the artist or creator submitting the entry."
        },
        "artist_email": {
            "type": "string",
            "format": "email",
            "description": "Email address of the artist for notifications."
        },
        "artist_phone": {
            "type": "string",
            "description": "Optional: Phone number of the artist for urgent contact."
        },
        "description": {
            "type": "string",
            "description": "Description or artist statement for the entry (up to 2000 characters)."
        },
        "media_type": {
            "type": "string",
            "enum": [
                "image",
                "audio",
                "video",
                "document",
                "other"
            ],
            "description": "Type of media file being submitted."
        },
        "media_url": {
            "type": "string",
            "format": "uri",
            "description": "Optional: URL to the uploaded media file (e.g., Dropbox, Google Drive, direct link). If not provided, a placeholder will be used."
        }
    },
    "required": [
        "festival_id",
        "entry_title",
        "category",
        "artist_name",
        "artist_email",
        "description",
        "media_type"
    ]
},
}
