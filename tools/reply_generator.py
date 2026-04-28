"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    import random
    try:
        data = json.loads(payload)
        original = data.get('original_message', '').strip()
        if not original:
            return 'error: original_message is required and cannot be empty'
        persona = data.get('persona', 'friendly')
        intent = data.get('intent', 'engage')
        platform = data.get('platform', 'twitter')
        max_suggestions = min(data.get('max_suggestions', 3), 5)
        language = data.get('language', 'en')
        
        # Simple rule-based reply templates
        templates = {
            'friendly': {
                'thank': [
                    f"Thanks so much for your kind words, really appreciate it! 🙏",
                    f"You're awesome, thank you for the support! 💙",
                    f"Glad you liked it! Thanks for sharing."
                ],
                'engage': [
                    f"That's a great question! What do you think?",
                    f"Love hearing your thoughts on this! 💬",
                    f"Interesting perspective — tell me more!"
                ],
                'support': [
                    f"Happy to help! Let me check on that for you.",
                    f"I understand, we'll get this sorted out quickly.",
                    f"No worries, I'm here to assist you 🙂"
                ]
            },
            'professional': {
                'thank': [
                    f"Thank you for your valuable feedback.",
                    f"We appreciate your business and your input.",
                    f"Thank you for reaching out to us."
                ],
                'clarify': [
                    f"Thank you for your question. Here are the details...",
                    f"Let me clarify: our policy states that...",
                    f"I would be happy to provide more information."
                ],
                'apologize': [
                    f"We sincerely apologize for any inconvenience caused.",
                    f"Please accept our apologies. We are looking into this.",
                    f"We regret the error and are taking steps to correct it."
                ]
            },
            'humorous': {
                'engage': [
                    f"Haha, you caught me! 😂",
                    f"That's one way to look at it! 🤣",
                    f"Ask me anything... as long as it's not about my cooking 🍳"
                ],
                'thank': [
                    f"You're too kind! My ego is now properly inflated 🎈",
                    f"Thank you! I'll be here all week (try the veal)."
                ]
            },
            'empathetic': {
                'support': [
                    f"I'm really sorry you're going through this. Let me help.",
                    f"That sounds frustrating — I want to make it right.",
                    f"Your feelings are completely valid. Let's find a solution."
                ],
                'apologize': [
                    f"We hear you and we're sorry. This isn't the experience we want for you.",
                    f"I understand your disappointment. We are working to improve."
                ]
            },
            'enthusiastic': {
                'thank': [
                    f"THANK YOU! Your support means the world to us! 🚀🔥",
                    f"We're so hyped you loved it! 🙌🙌🙌",
                    f"Amazing! You just made our day! 🌟"
                ],
                'promote': [
                    f"You won't want to miss what's coming next — stay tuned! 🎉",
                    f"We have something special just for our followers! Check it out!",
                    f"Big news dropping soon! Are you ready?"
                ]
            },
            'neutral': {
                'clarify': [
                    f"Thank you for your question. Here is the information you requested.",
                    f"Please refer to our FAQ for more details.",
                    f"We'll get back to you shortly with an answer."
                ],
                'thank': [
                    f"Thank you for your comment.",
                    f"We appreciate your feedback."
                ]
            }
        }
        
        # Fallback if persona/intent combo missing
        persona_templates = templates.get(persona, templates['neutral'])
        replies = persona_templates.get(intent, persona_templates.get('thank', templates['neutral']['thank']))
        
        # Adjust length for platform
        max_length = 280 if platform == 'twitter' else 500
        replies = [r[:max_length] for r in replies]
        
        # Return requested number of suggestions (only unique)
        suggestions = list(dict.fromkeys(replies))[:max_suggestions]
        if len(suggestions) < max_suggestions:
            # Fill with generics
            generics = [
                f"Thanks for the message!",
                f"Appreciate your input.",
                f"Good point!"
            ]
            for g in generics:
                if len(suggestions) < max_suggestions:
                    suggestions.append(g)
        
        result = {
            'original_message': original,
            'persona': persona,
            'intent': intent,
            'platform': platform,
            'language': language,
            'suggestions': suggestions
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "reply_generator",
    "description": "Generate contextual, stylistically appropriate social media reply suggestions based on an incoming message, user persona, and desired tone. Returns a list of reply text options for community managers, influencers, or brand accounts to quickly engage with their audience.",
    "category": "generate",
    "domain": "social",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "original_message": {
            "type": "string",
            "description": "The incoming social media message or comment that needs a reply."
        },
        "persona": {
            "type": "string",
            "description": "Optional: the user persona or brand voice (e.g., 'friendly', 'professional', 'humorous', 'empathetic').",
            "enum": [
                "friendly",
                "professional",
                "humorous",
                "empathetic",
                "enthusiastic",
                "neutral"
            ]
        },
        "intent": {
            "type": "string",
            "description": "Optional: the intended purpose of the reply (e.g., 'thank', 'clarify', 'support', 'promote', 'engage').",
            "enum": [
                "thank",
                "clarify",
                "support",
                "promote",
                "engage",
                "apologize"
            ]
        },
        "platform": {
            "type": "string",
            "description": "Optional: social platform context (adjusts length/style).",
            "enum": [
                "twitter",
                "linkedin",
                "instagram",
                "facebook",
                "tiktok",
                "youtube"
            ]
        },
        "max_suggestions": {
            "type": "integer",
            "description": "Optional: maximum number of reply suggestions to return (1-5, default 3).",
            "minimum": 1,
            "maximum": 5
        },
        "language": {
            "type": "string",
            "description": "Optional: ISO language code for the reply (default 'en').",
            "pattern": "^[a-z]{2}$"
        }
    },
    "required": [
        "original_message"
    ]
},
}
