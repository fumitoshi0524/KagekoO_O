"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Search for interactions between social platform users."""
    import json
    from datetime import datetime, timedelta

    try:
        data = json.loads(payload)
        if "user_handles" not in data or not isinstance(data["user_handles"], list) or len(data["user_handles"]) < 2:
            return json.dumps({"error": "At least 2 user handles are required."}, ensure_ascii=False)
        if len(data["user_handles"]) > 10:
            return json.dumps({"error": "Maximum 10 user handles allowed."}, ensure_ascii=False)

        interaction_type = data.get("interaction_type", "all")
        valid_types = ["all", "mentions", "replies", "direct_messages", "reposts"]
        if interaction_type not in valid_types:
            return json.dumps({"error": f"Invalid interaction_type. Must be one of {valid_types}"}, ensure_ascii=False)

        time_range_hours = data.get("time_range_hours", 168)
        if not isinstance(time_range_hours, int) or time_range_hours < 1 or time_range_hours > 720:
            return json.dumps({"error": "time_range_hours must be integer between 1 and 720."}, ensure_ascii=False)

        max_results = data.get("max_results", 50)
        if not isinstance(max_results, int) or max_results < 1 or max_results > 200:
            return json.dumps({"error": "max_results must be integer between 1 and 200."}, ensure_ascii=False)

        include_content = data.get("include_content", True)
        if not isinstance(include_content, bool):
            return json.dumps({"error": "include_content must be a boolean."}, ensure_ascii=False)

        users = data["user_handles"]
        now = datetime.utcnow()
        cutoff_time = now - timedelta(hours=time_range_hours)

        # Simulated interaction search logic
        interactions = []
        interaction_templates = {
            "mentions": {"content": "@{user2} interesting point!", "type": "mention"},
            "replies": {"content": "@{} I agree with your analysis.", "type": "reply"},
            "reposts": {"content": "", "type": "repost"},
            "direct_messages": {"content": "Let's discuss this in private.", "type": "dm"}
        }

        import random
        random.seed(hash(tuple(users)) % 2**31)
        
        for i in range(min(100, max_results * 4)):  # Generate some realistic interactions
            if len(interactions) >= max_results:
                break
                
            user_a = random.choice(users)
            user_b = random.choice([u for u in users if u != user_a])
            
            # Generate random timestamp in range
            time_delta = random.randint(0, time_range_hours * 3600)
            timestamp = (now - timedelta(seconds=time_delta)).isoformat()
            
            # Pick interaction type
            if interaction_type == "all":
                chosen_type = random.choice(list(interaction_templates.keys()))
            else:
                chosen_type = interaction_type
                if chosen_type == "all":
                    chosen_type = random.choice(list(interaction_templates.keys()))
            
            template = interaction_templates[chosen_type]
            content = template["content"]
            if content and "{}" in content:
                content = content.format(user_b)
            
            record = {
                "from_user": user_a,
                "to_user": user_b,
                "interaction_type": template["type"],
                "timestamp": timestamp,
                "reactions": random.randint(0, 100)
            }
            if include_content:
                record["content"] = content
            
            interactions.append(record)
        
        # Sort by timestamp descending
        interactions.sort(key=lambda x: x["timestamp"], reverse=True)
        
        result = {
            "query": {
                "users": users,
                "interaction_type": interaction_type,
                "time_range_hours": time_range_hours,
                "max_results": max_results,
                "include_content": include_content
            },
            "total_found": len(interactions),
            "interactions": interactions[:max_results]
        }
        
        return json.dumps(result, ensure_ascii=False)

    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON payload: {str(e)}"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Unexpected error: {str(e)}"}, ensure_ascii=False)



TOOL_SPEC = {
    "name": "find_user_interactions",
    "description": "Search for all public interactions between two or more social platform users based on their handles or IDs. Returns a list of interaction records including message content, timestamps, and reaction counts, used for relationship analysis and community monitoring.",
    "category": "search",
    "domain": "social",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "user_handles": {
            "type": "array",
            "items": {
                "type": "string",
                "pattern": "^@?[a-zA-Z0-9_]{3,30}$"
            },
            "description": "Array of user handles (e.g., @username) or user IDs to search interactions between. Accepts 2 to 10 users."
        },
        "interaction_type": {
            "type": "string",
            "enum": [
                "all",
                "mentions",
                "replies",
                "direct_messages",
                "reposts"
            ],
            "description": "Optional: Filter by type of interaction. Default is 'all'."
        },
        "time_range_hours": {
            "type": "integer",
            "minimum": 1,
            "maximum": 720,
            "description": "Optional: Time range in hours to search backwards from now (e.g., 24 for last day, 168 for last week). Default is 168 (1 week)."
        },
        "max_results": {
            "type": "integer",
            "minimum": 1,
            "maximum": 200,
            "description": "Optional: Maximum number of interaction records to return. Default is 50."
        },
        "include_content": {
            "type": "boolean",
            "description": "Optional: Whether to include full text/content of interactions. Default is true."
        }
    },
    "required": [
        "user_handles"
    ]
},
}
