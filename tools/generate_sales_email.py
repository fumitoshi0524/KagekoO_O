"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a personalized sales outreach email."""
    import json
    try:
        data = json.loads(payload)
        
        # Validate required inputs
        required = ['prospect_company', 'prospect_industry', 'product_name', 'product_value_prop']
        for r in required:
            if r not in data or not data[r]:
                return json.dumps({'error': f'Missing required field: {r}'})
        
        company = data['prospect_company']
        industry = data['prospect_industry']
        product = data['product_name']
        value_prop = data['product_value_prop']
        tone = data.get('tone', 'professional')
        cta = data.get('call_to_action', 'schedule a quick call')
        
        # Generate subject line based on tone
        subjects = {
            'professional': f'Idea to help {company} in the {industry} space',
            'casual': f'Quick thought for {company}',
            'urgent': f'Time-sensitive opportunity for {company}'
        }
        subject = subjects.get(tone, subjects['professional'])
        
        # Generate opening based on tone
        openings = {
            'professional': f'Dear {company} Team,',
            'casual': f'Hi there 👋,',
            'urgent': f'To the decision-makers at {company}:'
        }
        opening = openings.get(tone, openings['professional'])
        
        # Generate body
        body_templates = {
            'professional': [
                f'I am reaching out because we have helped several companies in the {industry} sector achieve better results.',
                f'Our product, {product}, {value_prop}.',
                f'I believe this could be particularly valuable for {company} given your position in the {industry} market.'
            ],
            'casual': [
                f'I saw that {company} is doing some interesting things in {industry}.',
                f'We built {product} specifically to {value_prop}.',
                f'Thought it might be a fit for what you are working on.'
            ],
            'urgent': [
                f'The {industry} industry is changing rapidly, and we have identified a critical need that {product} addresses.',
                f'{value_prop}.',
                f'We are currently offering a limited-time opportunity for companies like {company} to get early access.'
            ]
        }
        body_lines = body_templates.get(tone, body_templates['professional'])
        
        # Generate call-to-action
        cta_line = f'Would you be open to {cta} next week to discuss this further?'
        
        # Generate closing
        closings = {
            'professional': 'Best regards,',
            'casual': 'Cheers,',
            'urgent': 'Looking forward to your prompt response,'
        }
        closing = closings.get(tone, closings['professional'])
        
        # Construct email
        email_body = f'''{opening}

{' '.join(body_lines)}

{cta_line}

{closing}'''
        
        result = {
            'subject': subject,
            'body': email_body,
            'metadata': {
                'target_company': company,
                'industry': industry,
                'product': product,
                'tone': tone
            }
        }
        
        return json.dumps(result, ensure_ascii=False)
        
    except json.JSONDecodeError:
        return json.dumps({'error': 'Invalid JSON payload'})
    except Exception as e:
        return json.dumps({'error': str(e)})


TOOL_SPEC = {
    "name": "generate_sales_email",
    "description": "Generate a personalized sales outreach email for a prospect based on their company name, industry, and the product/service being offered. Returns a draft email body with subject line, opening, value proposition, and call-to-action.",
    "category": "generate",
    "domain": "business",
    "risk_level": "informational",
    "schema": {
    "type": "object",
    "properties": {
        "prospect_company": {
            "type": "string",
            "description": "The name of the target company the email is addressed to."
        },
        "prospect_industry": {
            "type": "string",
            "description": "The industry sector of the prospect company (e.g., healthcare, finance, retail)."
        },
        "product_name": {
            "type": "string",
            "description": "The name of the product or service being offered."
        },
        "product_value_prop": {
            "type": "string",
            "description": "A brief description of how the product helps the customer (benefit, not features)."
        },
        "tone": {
            "type": "string",
            "description": "Optional: The desired tone of the email (e.g., professional, casual, urgent).",
            "enum": [
                "professional",
                "casual",
                "urgent"
            ]
        },
        "call_to_action": {
            "type": "string",
            "description": "Optional: Specific desired next step for the recipient (e.g., schedule a demo, download a whitepaper)."
        }
    },
    "required": [
        "prospect_company",
        "prospect_industry",
        "product_name",
        "product_value_prop"
    ]
},
}
