"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Encode or decode text between common formats."""
    try:
        data = json.loads(payload)
        text = str(data.get("text", ""))
        operation = str(data.get("operation", "base64_encode")).lower().strip()
    except (json.JSONDecodeError, TypeError):
        return "error: invalid payload — provide JSON with 'text' and 'operation'"

    if not text:
        return "error: no text provided"

    import base64

    if operation == "base64_encode":
        result = base64.b64encode(text.encode("utf-8")).decode("ascii")
    elif operation == "base64_decode":
        try:
            result = base64.b64decode(text.encode("ascii")).decode("utf-8")
        except Exception as e:
            return f"error: invalid base64 input — {e}"
    elif operation == "url_encode":
        import urllib.parse
        result = urllib.parse.quote(text, safe="")
    elif operation == "url_decode":
        import urllib.parse
        result = urllib.parse.unquote(text)
    elif operation == "hex_encode":
        result = text.encode("utf-8").hex()
    elif operation == "hex_decode":
        try:
            result = bytes.fromhex(text).decode("utf-8")
        except Exception as e:
            return f"error: invalid hex input — {e}"
    else:
        return f"error: unknown operation '{operation}'. Use: base64_encode, base64_decode, url_encode, url_decode, hex_encode, hex_decode"

    return json.dumps({"operation": operation, "result": result}, indent=2, ensure_ascii=False)


TOOL_SPEC = {
    "name": "encode_decode",
    "description": "Encode or decode text between common formats: Base64 (encode/decode), URL encoding (encode/decode), and Hex (encode/decode).",
    "category": "operations",
    "domain": "technology",
    "risk_level": "read",
    "schema": {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "The text to encode or decode."
            },
            "operation": {
                "type": "string",
                "description": "Operation: base64_encode, base64_decode, url_encode, url_decode, hex_encode, hex_decode.",
                "enum": ["base64_encode", "base64_decode", "url_encode", "url_decode", "hex_encode", "hex_decode"]
            }
        },
        "required": ["text", "operation"]
    }
}
