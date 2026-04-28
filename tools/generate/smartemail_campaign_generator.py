"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        name = data.get('campaign_name', '')
        audience = data.get('target_audience', '')
        goal = data.get('goal', '')
        tone = data.get('tone', 'professional')
        n_emails = data.get('number_of_emails', 3)
        ab_test = data.get('include_ab_test', False)

        if not name or not audience or not goal:
            return json.dumps({'error': 'Missing required parameters: campaign_name, target_audience, goal'})

        # Business logic: generate email sequence
        email_parts = []
        for i in range(1, n_emails + 1):
            subject_prefix = ''
            if i == 1:
                subject_prefix = 'Welcome / First touch'
            elif i == n_emails:
                subject_prefix = 'Final push'
            else:
                subject_prefix = f'Follow-up {i}'
            email = {
                'email_number': i,
                'subject': f'{subject_prefix}: {name} - great offer inside',
                'body_preview': f'Dear {audience}, we are excited to share our latest {goal.replace("_", " ")} with you...',
                'cta_button': 'Shop Now' if 'promote' in goal else 'Learn More',
                'send_delay_days': 2 if i == 1 else 3
            }
            email_parts.append(email)

        result = {
            'campaign_name': name,
            'audience': audience,
            'goal': goal,
            'tone': tone,
            'total_emails': n_emails,
            'emails': email_parts
        }

        if ab_test:
            variants = []
            for i in range(1, 4):
                variants.append({
                    'variant': f'Variant {i}',
                    'subject_line_a': f'{name} - exclusive deal just for you',
                    'subject_line_b': f'Don\'t miss out: {name} inside'
                })
            result['ab_test_variants'] = variants

        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "smartemail_campaign_generator",
    "description": "Generate a complete multi-step email marketing campaign for a target audience, including subject lines, body content, call-to-action buttons, send schedule, and A/B test variants, typically used for lead nurturing or product launches.",
    "category": "generate",
    "domain": "business",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "campaign_name": {
            "type": "string",
            "description": "Name or title for the campaign (e.g., 'Winter Sale')",
            "examples": [
                "Winter Sale 2025"
            ]
        },
        "target_audience": {
            "type": "string",
            "description": "Description of the target recipient segment (e.g., 'existing customers', 'new leads', 'VIP clients')",
            "examples": [
                "existing customers who purchased in last 6 months"
            ]
        },
        "goal": {
            "type": "string",
            "description": "Primary campaign goal (e.g., 'promote product', 're-engage inactive users', 'announce feature')",
            "enum": [
                "promote_product",
                "re_engage_users",
                "announce_feature",
                "nurture_leads",
                "event_invite"
            ]
        },
        "tone": {
            "type": "string",
            "description": "Optional: Tone or voice of the emails. Default: 'professional'",
            "enum": [
                "professional",
                "friendly",
                "humorous",
                "urgent",
                "inspirational"
            ]
        },
        "number_of_emails": {
            "type": "integer",
            "description": "Optional: Number of emails in the sequence. Minimum 1, maximum 10. Default: 3.",
            "minimum": 1,
            "maximum": 10
        },
        "include_ab_test": {
            "type": "boolean",
            "description": "Optional: Whether to generate A/B test variants for subject lines. Default: False."
        }
    },
    "required": [
        "campaign_name",
        "target_audience",
        "goal"
    ]
},
}
