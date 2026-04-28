"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        segment = data.get('segment_name', '').strip()
        goal = data.get('campaign_goal', '').strip()
        product = data.get('product_or_service', '').strip()
        tone = data.get('tone', 'professional').strip()
        include_discount = data.get('include_discount_code', False)

        if not segment:
            return json.dumps({'error': 'segment_name is required and cannot be empty'}, ensure_ascii=False)
        if not product:
            return json.dumps({'error': 'product_or_service is required and cannot be empty'}, ensure_ascii=False)

        if tone not in ['professional', 'friendly', 'urgent', 'inspirational']:
            tone = 'professional'

        # Generate personalized subject line based on segment and goal
        subjects = {
            ('loyal_customers', 'engagement'): f"Exclusive update for our valued customers: {product}",
            ('new_subscribers', 'awareness'): f"Welcome! Discover what {product} can do for you",
            ('inactive_users', 'retention'): f"We miss you! Come back to {product}",
            ('loyal_customers', 'conversion'): f"Special offer on {product} just for you",
            ('new_subscribers', 'conversion'): f"Start your journey with {product} today",
        }
        default_subject = f"{goal.capitalize()} campaign: {product}"
        subject = subjects.get((segment, goal), default_subject)

        if tone == 'urgent':
            subject = f"Limited time: {subject}"
        elif tone == 'friendly':
            subject = f"Hey there! {subject}"
        elif tone == 'inspirational':
            subject = f"Unlock your potential with {product}"

        # Generate body text based on goal and segment
        body_parts = {
            'awareness': f"We are excited to introduce {product} to you. Learn how it can benefit your business and streamline your operations.",
            'engagement': f"As a valued member of our community, we want to share the latest updates about {product}. Let us know what you think!",
            'conversion': f"Ready to take the next step? {product} is designed to help you achieve more. Act now and see the difference.",
            'retention': f"We value your relationship with us. Here is why {product} continues to be the best choice for your needs.",
        }
        body = body_parts.get(goal, f"Check out {product} and see how it can help you.")
        if tone == 'friendly':
            body = f"Hi! {body} We would love to hear from you."
        elif tone == 'urgent':
            body = f"Don't miss out! {body} This offer expires soon."
        elif tone == 'inspirational':
            body = f"Imagine what you can accomplish with {product}. {body} Start your transformation today."

        # Generate call-to-action
        cta_map = {
            'awareness': 'Learn More',
            'engagement': 'Share Feedback',
            'conversion': 'Buy Now',
            'retention': 'Rejoin Us'
        }
        cta = cta_map.get(goal, 'Get Started')

        # Optional discount code
        discount = None
        if include_discount:
            import random
            import string
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            discount = f"DISCOUNT{code}"

        result = {
            'segment': segment,
            'goal': goal,
            'product': product,
            'tone': tone,
            'subject': subject,
            'body': body,
            'call_to_action': cta,
        }
        if discount:
            result['discount_code'] = discount

        return json.dumps(result, ensure_ascii=False)
    except json.JSONDecodeError as e:
        return json.dumps({'error': f'Invalid JSON input: {str(e)}'}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': f'Unexpected error: {str(e)}'}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "email_campaign_generator",
    "description": "Generate a personalized email marketing campaign for a target customer segment, producing subject lines, body text, and call-to-action recommendations based on campaign objectives and audience profile.",
    "category": "generate",
    "domain": "business",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "segment_name": {
            "type": "string",
            "description": "Name of the customer segment (e.g., 'loyal_customers', 'new_subscribers', 'inactive_users'). Must be non-empty.",
            "minLength": 1
        },
        "campaign_goal": {
            "type": "string",
            "description": "Primary goal of the campaign. One of: 'awareness', 'engagement', 'conversion', 'retention'.",
            "enum": [
                "awareness",
                "engagement",
                "conversion",
                "retention"
            ]
        },
        "product_or_service": {
            "type": "string",
            "description": "Name of the product or service being promoted (e.g., 'Premium Subscription Plan', 'Office 365 Bundle'). Must be non-empty.",
            "minLength": 1
        },
        "tone": {
            "type": "string",
            "description": "Optional: Desired tone of the email content. One of: 'professional', 'friendly', 'urgent', 'inspirational'. Default is 'professional'.",
            "enum": [
                "professional",
                "friendly",
                "urgent",
                "inspirational"
            ]
        },
        "include_discount_code": {
            "type": "boolean",
            "description": "Optional: Whether to include a discount code in the campaign. If True, a code is auto-generated. Default is False."
        }
    },
    "required": [
        "segment_name",
        "campaign_goal",
        "product_or_service"
    ]
},
}
