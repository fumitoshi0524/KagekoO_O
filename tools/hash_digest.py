"""Auto-generated tool module."""

from __future__ import annotations

import json
import hashlib


def run(payload: str) -> str:
    """Compute hash digest of input text."""
    try:
        data = json.loads(payload)
        text = str(data.get("text", ""))
        algorithm = str(data.get("algorithm", "sha256")).lower().strip()
    except (json.JSONDecodeError, TypeError):
        text = payload
        algorithm = "sha256"

    if not text:
        return "error: no text provided"

    algorithms = {
        "md5": hashlib.md5,
        "sha1": hashlib.sha1,
        "sha224": hashlib.sha224,
        "sha256": hashlib.sha256,
        "sha384": hashlib.sha384,
        "sha512": hashlib.sha512,
    }
    if algorithm not in algorithms:
        return f"error: unsupported algorithm '{algorithm}'. Use: {', '.join(algorithms.keys())}"

    digest = algorithms[algorithm](text.encode("utf-8")).hexdigest()
    return json.dumps({
        "algorithm": algorithm,
        "digest": digest,
        "text_length": len(text),
    }, indent=2, ensure_ascii=False)


TOOL_SPEC = {
    "name": "hash_digest",
    "description": "Compute a cryptographic hash digest (MD5, SHA1, SHA256, SHA384, SHA512) of input text and return the hex digest.",
    "category": "operations",
    "domain": "technology",
    "risk_level": "read",
    "schema": {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "The text to compute hash for."
            },
            "algorithm": {
                "type": "string",
                "description": "Hash algorithm: md5, sha1, sha256 (default), sha384, or sha512.",
                "enum": ["md5", "sha1", "sha256", "sha384", "sha512"],
                "default": "sha256"
            }
        },
        "required": ["text"]
    }
}
