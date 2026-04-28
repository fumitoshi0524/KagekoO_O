"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a professional marketing email draft based on campaign inputs."""
    import json
    import random
    try:
        data = json.loads(payload)
        required = ['product_name', 'target_audience', 'campaign_objective', 'brand_tone']
        for field in required:
            if field not in data or not data[field]:
                return json.dumps({'error': f'Missing required field: {field}'})
        name = data['product_name']
        audience = data['target_audience']
        objective = data['campaign_objective']
        tone = data['brand_tone']
        benefits = data.get('key_benefits', [])
        sender = data.get('sender_name', 'Marketing Team')
        lang = data.get('target_language', 'en')
        tone_adj = {'professional': 'compelling and data-driven', 'friendly': 'warm and approachable', 'urgent': 'time-sensitive and impactful', 'luxury': 'elegant and exclusive', 'playful': 'engaging and creative'}
        obj_adj = {'announcement': 'exciting update', 'promotion': 'exclusive offer', 'newsletter': 'latest insights', 'reengagement': 'special welcome back', 'event_invitation': 'personal invitation'}
        tone_desc = tone_adj.get(tone, 'professional')
        obj_desc = obj_adj.get(objective, 'special message')
        subject_line = f"{name}: An {obj_desc} for {audience}"
        if tone == 'urgent':
            subject_line = f"⏰ Last Chance: {subject_line}"
        elif tone == 'playful':
            subject_line = f"🎉 {subject_line}"
        body_parts = []
        body_parts.append(f"Dear valued {audience},")
        body_parts.append(f"")
        body_parts.append(f"We're thrilled to share a {tone_desc} {obj_desc} about {name}.")
        if benefits:
            body_parts.append(f"Here's what makes {name} special:")
            for b in benefits[:5]:
                body_parts.append(f"• {b}")
        body_parts.append(f"")
        body_parts.append(f"Don't miss this opportunity — act now to experience {name} firsthand.")
        body_parts.append(f"")
        body_parts.append(f"Best regards,")
        body_parts.append(f"{sender}")
        body_text = '\n'.join(body_parts)
        cta = f"Get started with {name} today" if objective != 'event_invitation' else f"RSVP for {name} event"
        result = {
            'subject_line': subject_line,
            'body_text': body_text,
            'call_to_action': cta,
            'sender_signature': sender,
            'language': lang,
            'generated_at': 'current'  # simplified time marker
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)})


TOOL_SPEC = {
    "name": "generate_marketing_email",
    "description": "Generate a professional marketing email draft for a product or service based on target audience, campaign objective, and brand tone. Returns the email subject line, body text, call-to-action, and sender signature for use in email marketing campaigns.",
    "category": "generate",
    "domain": "business",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "product_name": {
            "type": "string",
            "description": "The name of the product or service being promoted in the email"
        },
        "target_audience": {
            "type": "string",
            "description": "Description of the intended recipients (e.g. 'existing customers', 'small business owners', 'tech professionals')"
        },
        "campaign_objective": {
            "type": "string",
            "enum": [
                "announcement",
                "promotion",
                "newsletter",
                "reengagement",
                "event_invitation"
            ],
            "description": "The primary goal of the email campaign"
        },
        "brand_tone": {
            "type": "string",
            "enum": [
                "professional",
                "friendly",
                "urgent",
                "luxury",
                "playful"
            ],
            "description": "Desired tone and voice for the email content"
        },
        "key_benefits": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "Optional: List of key benefits or features to highlight in the email body",
            "optional": true
        },
        "sender_name": {
            "type": "string",
            "description": "Optional: Name of the sender for the signature block. Default is 'Marketing Team'",
            "optional": true
        },
        "target_language": {
            "type": "string",
            "description": "Optional: Language for the generated email (e.g. 'en', 'es', 'fr'). Default is 'en'",
            "optional": true
        }
    },
    "required": [
        "product_name",
        "target_audience",
        "campaign_objective",
        "brand_tone"
    ]
},
}
