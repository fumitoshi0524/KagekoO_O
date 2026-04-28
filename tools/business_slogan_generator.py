"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        company_name = data.get('company_name')
        industry = data.get('industry')
        core_value = data.get('core_value')
        tone = data.get('tone')
        count = data.get('count', 5)

        if not company_name or not industry or not core_value or not tone:
            return json.dumps({'error': 'Missing required parameters: company_name, industry, core_value, tone'})

        tone_templates = {
            'professional': [
                "{company}: {core_value} {industry}",
                "Your {industry} Partner for {core_value}",
                "{industry} Excellence, {core_value} Focus",
                "{company} — Where {core_value} Meets {industry}",
                "Driving {core_value} in {industry}",
                "{core_value} First, {industry} Forward",
                "{company}: Redefining {industry} with {core_value}"
            ],
            'playful': [
                "{company}: {core_value} but Make it {industry}",
                "{industry} Witty? We Do {core_value} Too!",
                "{core_value} Your Way in {industry}",
                "{company} — {core_value} Level: {industry} Unlocked",
                "Don't Just {industry}, {core_value}!",
                "{core_value} Me if You Can — {company}",
                "{industry} Done {core_value} Style"
            ],
            'inspirational': [
                "{company}: Inspire {industry} Through {core_value}",
                "{core_value} Transforms {industry} — Start Here",
                "Building a Better {industry} with {core_value}",
                "{company} — The Heart of {core_value} in {industry}",
                "Empowering {industry} Through {core_value}",
                "{industry} Unites, {core_value} Leads — {company}",
                "Your Journey to {core_value} in {industry} Begins with {company}"
            ],
            'direct': [
                "{company}: {core_value} for {industry}",
                "{core_value} in {industry} — That's {company}",
                "{company} Does {core_value}. Period.",
                "Need {core_value} in {industry}? Choose {company}",
                "{industry} Solved. {core_value} Delivered. {company}.",
                "{core_value} is Our {industry} Promise",
                "{company} — Just {core_value}, No {industry} Fluff"
            ]
        }

        templates = tone_templates.get(tone.lower(), tone_templates['professional'])
        slogans = []
        for i in range(min(count, len(templates))):
            slogan = templates[i].format(company=company_name, industry=industry.lower(), core_value=core_value.lower())
            slogans.append(slogan)

        if count > len(templates):
            import random
            for i in range(len(templates), count):
                template = random.choice(templates)
                slogan = template.format(company=company_name, industry=industry.lower(), core_value=core_value.lower())
                slogans.append(slogan)

        result = {
            'slogans': slogans,
            'generated_count': len(slogans),
            'company': company_name,
            'industry': industry,
            'tone': tone
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "business_slogan_generator",
    "description": "Generate a set of creative and brandable business slogans based on a company's name, industry, and core value proposition. Returns a list of slogan options suitable for marketing campaigns, website headers, and brand identity development.",
    "category": "generate",
    "domain": "business",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "company_name": {
            "type": "string",
            "description": "The exact name of the business to personalize slogans around."
        },
        "industry": {
            "type": "string",
            "description": "The business industry or sector (e.g., technology, healthcare, finance, retail)."
        },
        "core_value": {
            "type": "string",
            "description": "The primary value proposition or brand message (e.g., innovation, trust, speed, sustainability)."
        },
        "tone": {
            "type": "string",
            "enum": [
                "professional",
                "playful",
                "inspirational",
                "direct"
            ],
            "description": "The desired tone for the generated slogans."
        },
        "count": {
            "type": "integer",
            "description": "Optional: Number of slogans to generate. Defaults to 5.",
            "minimum": 1,
            "maximum": 20
        }
    },
    "required": [
        "company_name",
        "industry",
        "core_value",
        "tone"
    ]
},
}
