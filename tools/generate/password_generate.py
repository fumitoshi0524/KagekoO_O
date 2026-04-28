"""Auto-generated tool module."""

from __future__ import annotations

import json
import hashlib
import secrets
import string


def run(payload: str) -> str:
    """Generate a secure password or token."""
    try:
        data = json.loads(payload)
    except (json.JSONDecodeError, TypeError):
        data = {}
    length = max(8, min(128, int(data.get("length", 16))))
    use_upper = bool(data.get("uppercase", True))
    use_lower = bool(data.get("lowercase", True))
    use_digits = bool(data.get("digits", True))
    use_symbols = bool(data.get("symbols", False))

    char_pool = ""
    if use_lower:
        char_pool += string.ascii_lowercase
    if use_upper:
        char_pool += string.ascii_uppercase
    if use_digits:
        char_pool += string.digits
    if use_symbols:
        char_pool += "!@#$%^&*()-_=+"
    if not char_pool:
        return "error: at least one character set must be enabled"

    password = "".join(secrets.choice(char_pool) for _ in range(length))
    return password


TOOL_SPEC = {
    "name": "password_generate",
    "description": "Generate a cryptographically secure random password with configurable length and character sets.",
    "category": "generate",
    "domain": "technology",
    "risk_level": "read",
    "schema": {
        "type": "object",
        "properties": {
            "length": {
                "type": "integer",
                "description": "Password length (8-128, default 16).",
                "default": 16,
                "minimum": 8,
                "maximum": 128
            },
            "uppercase": {
                "type": "boolean",
                "description": "Include uppercase letters (default True).",
                "default": True
            },
            "lowercase": {
                "type": "boolean",
                "description": "Include lowercase letters (default True).",
                "default": True
            },
            "digits": {
                "type": "boolean",
                "description": "Include digits (default True).",
                "default": True
            },
            "symbols": {
                "type": "boolean",
                "description": "Include special symbols (default False).",
                "default": False
            }
        },
        "required": []
    }
}
