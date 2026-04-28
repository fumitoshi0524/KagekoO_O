"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Count words, characters, or lines in text, or count items in a list."""
    try:
        data = json.loads(payload)
        text = str(data.get("text", ""))
        mode = str(data.get("mode", "words")).lower().strip()
    except (json.JSONDecodeError, TypeError):
        text = payload
        mode = "words"

    if not text:
        return json.dumps({"mode": mode, "count": 0}, indent=2)

    if mode == "words":
        count = len(text.split())
    elif mode == "chars":
        count = len(text)
    elif mode == "chars_no_spaces":
        count = len(text.replace(" ", "").replace("\n", "").replace("\t", ""))
    elif mode == "lines":
        count = len(text.splitlines())
    elif mode == "sentences":
        import re
        count = len([s for s in re.split(r"[.!?]+", text) if s.strip()])
    elif mode == "paragraphs":
        count = len([p for p in text.split("\n\n") if p.strip()])
    else:
        return f"error: unknown mode '{mode}'. Use: words, chars, chars_no_spaces, lines, sentences, paragraphs"

    return json.dumps({"mode": mode, "count": count}, indent=2, ensure_ascii=False)


TOOL_SPEC = {
    "name": "counter",
    "description": "Count words, characters, lines, sentences, or paragraphs in input text.",
    "category": "analysis",
    "domain": "technology",
    "risk_level": "read",
    "schema": {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "The text content to count."
            },
            "mode": {
                "type": "string",
                "description": "What to count: words, chars, chars_no_spaces, lines, sentences, paragraphs.",
                "enum": ["words", "chars", "chars_no_spaces", "lines", "sentences", "paragraphs"],
                "default": "words"
            }
        },
        "required": ["text"]
    }
}
