"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    import uuid

    try:
        data = json.loads(payload)
        required_fields = ["tournament_id", "participant_type", "age", "skill_level", "contact_email"]
        for field in required_fields:
            if field not in data:
                return json.dumps({"error": f"Missing required field: {field}"})

        tournament_id = data["tournament_id"]
        participant_type = data["participant_type"]
        age = data["age"]
        skill_level = data["skill_level"]
        contact_email = data["contact_email"]

        if participant_type == "team":
            if "team_name" not in data or not data["team_name"]:
                return json.dumps({"error": "team_name required for team registration"})
            participant_name = data["team_name"]
        else:
            if "player_name" not in data or not data["player_name"]:
                return json.dumps({"error": "player_name required for individual registration"})
            participant_name = data["player_name"]

        # Simple eligibility validation
        if age < 5 or age > 100:
            return json.dumps({"error": "Age out of acceptable range (5-100)"})

        allowed_skill = ["beginner", "intermediate", "advanced", "professional"]
        if skill_level not in allowed_skill:
            return json.dumps({"error": f"Invalid skill_level. Must be one of {allowed_skill}"})

        # Simulate tournament capacity check (always success)

        registration_id = str(uuid.uuid4())[:8].upper()
        result = {
            "status": "registered",
            "registration_id": registration_id,
            "tournament_id": tournament_id,
            "participant_type": participant_type,
            "participant_name": participant_name,
            "age": age,
            "skill_level": skill_level,
            "confirmation_sent_to": contact_email
        }
        return json.dumps(result, ensure_ascii=False)
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON payload"})
    except Exception as e:
        return json.dumps({"error": str(e)})


TOOL_SPEC = {
    "name": "sports_tournament_registration",
    "description": "Register a team or individual participant for a sports tournament, validate eligibility based on age and skill level categories, and return a registration confirmation with a unique identifier.",
    "category": "operations",
    "domain": "sports",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "tournament_id": {
            "type": "string",
            "description": "Unique identifier for the tournament (e.g., 'T-2025-001')."
        },
        "participant_type": {
            "type": "string",
            "enum": [
                "team",
                "individual"
            ],
            "description": "Whether the registration is for a team or an individual player."
        },
        "team_name": {
            "type": "string",
            "description": "Optional: Name of the team (required if participant_type is 'team')."
        },
        "player_name": {
            "type": "string",
            "description": "Optional: Full name of the individual participant (required if participant_type is 'individual')."
        },
        "age": {
            "type": "integer",
            "minimum": 5,
            "maximum": 100,
            "description": "Age of the participant (or average age of team members) to check against age category limits."
        },
        "skill_level": {
            "type": "string",
            "enum": [
                "beginner",
                "intermediate",
                "advanced",
                "professional"
            ],
            "description": "Skill level of the participant or team for category matching."
        },
        "contact_email": {
            "type": "string",
            "format": "email",
            "description": "Contact email for registration confirmation."
        }
    },
    "required": [
        "tournament_id",
        "participant_type",
        "age",
        "skill_level",
        "contact_email"
    ]
},
}
