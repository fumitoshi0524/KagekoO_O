"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate social media post content for multiple platforms."""
    import json
    import random
    from datetime import datetime, timedelta

    try:
        data = json.loads(payload)
        
        # Validate required inputs
        required_fields = ["topic", "tone", "platforms"]
        for field in required_fields:
            if field not in data:
                return json.dumps({"error": f"Missing required field: {field}"}, ensure_ascii=False)
        
        if not isinstance(data["platforms"], list) or len(data["platforms"]) == 0:
            return json.dumps({"error": "At least one platform must be specified"}, ensure_ascii=False)
        
        # Get optional parameters
        target_audience = data.get("target_audience", "general audience")
        key_points = data.get("key_points", [])
        call_to_action = data.get("call_to_action", "")
        
        # Template-based content generation engine
        tone_templates = {
            "professional": {
                "openers": ["Based on recent developments in {topic}, ", "In the context of {topic}, ", "Analysis of {topic} reveals that "],
                "bodies": ["key stakeholders should consider the implications for their operations.", "significant opportunities exist for organizations to leverage these insights.", "the data indicates a strategic shift in how we approach this area."],
                "closers": ["These findings suggest actionable next steps for industry leaders.", "We recommend further exploration of this trend.", "This information provides a foundation for informed decision-making."]
            },
            "casual": {
                "openers": ["Just thinking about {topic} and ", "Can't stop thinking about {topic} - ", "So, about {topic}... "],
                "bodies": ["it's really changing the game for so many people.", "there's so much to explore and discover.", "it's honestly mind-blowing what's happening."],
                "closers": ["What do you think about this?", "Would love to hear your thoughts!", "Anyone else feeling excited about this?"]
            },
            "humorous": {
                "openers": ["Trying to explain {topic} to my friends like... ", "When someone asks about {topic} and ", "Plot twist: {topic} is actually "],
                "bodies": ["it's a whole mood.", "the struggle is real but the payoff is worth it.", "95% of people don't know this secret."],
                "closers": ["You're welcome for this wisdom.", "Share if you relate!", "I'll be here all week, folks."]
            },
            "inspirational": {
                "openers": ["The journey through {topic} teaches us that ", "In the world of {topic}, ", "Every day with {topic} reminds us that "],
                "bodies": ["growth happens outside our comfort zone.", "the best results come from persistence and passion.", "small steps lead to remarkable transformations."],
                "closers": ["Keep pushing forward. Your breakthrough is coming.", "Believe in the process, and trust the journey.", "You have everything you need to succeed."]
            },
            "educational": {
                "openers": ["Did you know that {topic} ", "Let's break down {topic}: ", "Here's what you need to know about {topic}: "],
                "bodies": ["involves several key concepts that are essential to understand.", "has evolved significantly over the past few years.", "requires a systematic approach to master effectively."],
                "closers": ["Follow for more educational content on this topic.", "Save this post for future reference.", "Tag someone who needs to learn about this."]
            },
            "urgent": {
                "openers": ["URGENT: Regarding {topic}, ", "Important update on {topic}: ", "Breaking news in {topic}: "],
                "bodies": ["immediate attention is required from all stakeholders.", "new information has come to light that changes everything.", "deadlines are approaching faster than expected."],
                "closers": ["Take action now. Time is of the essence.", "Don't wait. This is time-sensitive.", "Share this alert with your network."]
            }
        }

        # Platform-specific constraints
        platform_limits = {
            "twitter": {"max_chars": 280, "hashtags_limit": 3},
            "linkedin": {"max_chars": 3000, "hashtags_limit": 5},
            "instagram": {"max_chars": 2200, "hashtags_limit": 30},
            "facebook": {"max_chars": 63206, "hashtags_limit": 10},
            "tiktok": {"max_chars": 150, "hashtags_limit": 5}
        }

        # Generate hashtags based on topic
        def generate_hashtags(topic, count):
            words = topic.lower().split()
            base_tags = [f"#{word}" for word in words[:3]]
            additional_tags = ["#trending", "#viral", "#new", "#insights", "#learn", "#share", "#community", "#update", "#tips", "#ideas"]
            random.shuffle(additional_tags)
            return base_tags + additional_tags[:max(0, count - len(base_tags))]

        # Generate optimal posting time based on platform
        def generate_optimal_times(platform, tone):
            base_time_offsets = {
                "twitter": {"hour": 8, "minute": 0},
                "linkedin": {"hour": 10, "minute": 30},
                "instagram": {"hour": 11, "minute": 0},
                "facebook": {"hour": 13, "minute": 0},
                "tiktok": {"hour": 19, "minute": 0}
            }
            
            time_offset = base_time_offsets.get(platform, {"hour": 12, "minute": 0})
            now = datetime.now()
            optimal_time = now.replace(hour=time_offset["hour"], minute=time_offset["minute"], second=0, microsecond=0)
            
            if optimal_time < now:
                optimal_time += timedelta(days=1)
            
            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            return {
                "day": days[optimal_time.weekday()],
                "time": optimal_time.strftime("%I:%M %p")
            }

        # Generate content for each platform
        generated_content = []
        
        for platform in data["platforms"]:
            if platform not in platform_limits:
                continue
                
            limits = platform_limits[platform]
            template = tone_templates.get(data["tone"], tone_templates["casual"])
            
            # Build post content
            opener = random.choice(template["openers"]).format(topic=data["topic"])
            body = random.choice(template["bodies"])
            closer = random.choice(template["closers"])
            
            post_content = opener + body + " " + closer
            
            # Add key points if provided
            if key_points:
                points_text = "\n" + "\n".join([f"- {point}" for point in key_points[:3]])
                if len(post_content + points_text) <= limits["max_chars"]:
                    post_content += points_text
            
            # Add call to action if provided
            if call_to_action:
                cta_text = f"\n\n{call_to_action}"
                if len(post_content + cta_text) <= limits["max_chars"]:
                    post_content += cta_text
            
            # Generate hashtags
            hashtags = generate_hashtags(data["topic"], limits["hashtags_limit"])
            hashtag_text = " " + " ".join(hashtags[:limits["hashtags_limit"]])
            
            # Truncate content to fit within limits with hashtags
            max_content_length = limits["max_chars"] - len(hashtag_text) - 10  # 10 chars buffer
            if len(post_content) > max_content_length:
                post_content = post_content[:max_content_length-3] + "..."
            
            final_post = post_content + "\n\n" + hashtag_text if hashtags else post_content
            
            # Generate optimal posting time
            optimal_time = generate_optimal_times(platform, data["tone"])
            
            generated_content.append({
                "platform": platform,
                "content": final_post.strip(),
                "character_count": len(final_post.strip()),
                "hashtags_used": hashtags[:limits["hashtags_limit"]],
                "optimal_posting_time": optimal_time,
                "character_limit": limits["max_chars"]
            })
        
        # Add audience targeting note
        if target_audience and target_audience != "general audience":
            for content in generated_content:
                content["targeting_note"] = f"This content is optimized for {target_audience}. Adjust hashtags and tone for different segments."
        
        result = {
            "status": "success",
            "generated_posts": generated_content,
            "summary": f"Generated {len(generated_content)} post(s) on '{data['topic']}' with {data['tone']} tone",
            "total_posts": len(generated_content),
            "generated_at": datetime.now().isoformat()
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({"error": f"Failed to generate social post: {str(e)}"}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "social_post_generator",
    "description": "Generate engaging social media post content for multiple platforms based on topic, tone, and target audience. Returns formatted post text, suggested hashtags, and optimal posting time for each platform.",
    "category": "generate",
    "domain": "social",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "topic": {
            "type": "string",
            "description": "The main subject or theme for the social media post"
        },
        "tone": {
            "type": "string",
            "description": "The emotional tone or style of the post",
            "enum": [
                "professional",
                "casual",
                "humorous",
                "inspirational",
                "educational",
                "urgent"
            ]
        },
        "platforms": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [
                    "twitter",
                    "linkedin",
                    "instagram",
                    "facebook",
                    "tiktok"
                ]
            },
            "description": "Social media platforms to generate content for. At least one platform required."
        },
        "target_audience": {
            "type": "string",
            "description": "Optional: Description of the target audience (e.g., 'tech professionals', 'small business owners', 'college students')"
        },
        "key_points": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "Optional: List of key points or messages to include in the post"
        },
        "call_to_action": {
            "type": "string",
            "description": "Optional: Specific call-to-action for the post (e.g., 'sign up now', 'learn more', 'share your thoughts')"
        }
    },
    "required": [
        "topic",
        "tone",
        "platforms"
    ]
},
}
