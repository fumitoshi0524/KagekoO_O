"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Register a new user in the Learning Management System."""
    import json
    import re
    import random
    import string
    from datetime import datetime

    try:
        data = json.loads(payload)

        # Required fields validation
        required = ["username", "email", "full_name", "role"]
        for field in required:
            if field not in data:
                return json.dumps({"error": f"Missing required field: {field}"})

        username = data["username"]
        email = data["email"]
        full_name = data["full_name"]
        role = data["role"]

        # Validate username
        if not re.match(r'^[a-zA-Z0-9_]{3,20}$', username):
            return json.dumps({"error": "Username must be 3-20 alphanumeric characters or underscores."})

        # Validate email format (basic check)
        if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
            return json.dumps({"error": "Invalid email format."})

        # Validate role
        valid_roles = ["student", "instructor", "admin", "auditor"]
        if role not in valid_roles:
            return json.dumps({"error": f"Invalid role '{role}'. Must be one of {valid_roles}"})

        # Validate full_name
        if len(full_name.strip()) < 2 or len(full_name) > 100:
            return json.dumps({"error": "Full name must be between 2 and 100 characters."})

        # Generate user ID (unique identifier, simulated)
        user_id = f"LMS-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"

        # Generate temporary password if not provided
        password = data.get("password")
        if not password:
            temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
            password = temp_password
        elif len(password) < 8:
            return json.dumps({"error": "Password must be at least 8 characters."})

        # Department handling
        department = data.get("department", "General")

        # Default course enrollment
        default_course_id = data.get("default_course_id")
        enrollment = []
        if default_course_id:
            enrollment.append({
                "course_id": default_course_id,
                "enrolled_at": datetime.now().isoformat(),
                "role": role if role != "admin" else "instructor"
            })

        # Account status
        is_active = data.get("is_active", True)
        if not isinstance(is_active, bool):
            return json.dumps({"error": "is_active must be a boolean."})

        # Settings validation
        settings = data.get("settings", {})
        if not isinstance(settings, dict):
            return json.dumps({"error": "settings must be a JSON object."})

        # Build result
        result = {
            "status": "success",
            "message": f"User '{full_name}' registered successfully in LMS.",
            "user_id": user_id,
            "username": username,
            "email": email,
            "role": role,
            "department": department,
            "is_active": is_active,
            "enrolled_courses": enrollment,
            "registration_date": datetime.now().isoformat(),
            "password_set": data.get("password") is not None,
            "account_settings": settings
        }

        return json.dumps(result, ensure_ascii=False)

    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON payload: {str(e)}"})
    except Exception as e:
        return json.dumps({"error": f"Unexpected error: {str(e)}"})



TOOL_SPEC = {
    "name": "register_lms_user",
    "description": "Register a new user in the Learning Management System with role-based access, personal details, and enrollment defaults for academic course management.",
    "category": "system",
    "domain": "education",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "username": {
            "type": "string",
            "description": "Unique login identifier for the user, 3-20 alphanumeric characters."
        },
        "email": {
            "type": "string",
            "format": "email",
            "description": "Valid institutional email address for account communication and recovery."
        },
        "full_name": {
            "type": "string",
            "description": "User's full legal name as it appears on academic records."
        },
        "role": {
            "type": "string",
            "enum": [
                "student",
                "instructor",
                "admin",
                "auditor"
            ],
            "description": "Access level defining permissions within the LMS: student, instructor, admin, or auditor."
        },
        "department": {
            "type": "string",
            "description": "Optional: Academic department or faculty the user belongs to (e.g., 'Computer Science', 'Mathematics')."
        },
        "default_course_id": {
            "type": "string",
            "description": "Optional: Course ID to auto-enroll the user upon registration (e.g., 'CS101')."
        },
        "is_active": {
            "type": "boolean",
            "description": "Optional: Sets immediate account status. Defaults to true (active)."
        },
        "password": {
            "type": "string",
            "description": "Optional: Initial password for the account, at least 8 characters. If omitted, a temporary password is generated."
        },
        "settings": {
            "type": "object",
            "description": "Optional: JSON object with user preferences (e.g., notification settings, timezone, language).",
            "properties": {
                "notifications": {
                    "type": "boolean",
                    "description": "Enable/disable email notifications."
                },
                "timezone": {
                    "type": "string",
                    "description": "IANA timezone string (e.g., 'America/New_York')."
                },
                "language": {
                    "type": "string",
                    "enum": [
                        "en",
                        "es",
                        "fr",
                        "de",
                        "zh"
                    ],
                    "description": "Preferred interface language code."
                }
            },
            "required": []
        }
    },
    "required": [
        "username",
        "email",
        "full_name",
        "role"
    ]
},
}
