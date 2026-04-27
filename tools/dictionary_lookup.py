"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Look up a word's definition, synonyms, or part of speech from a local dictionary."""
    try:
        data = json.loads(payload)
        word = str(data.get("word", "")).lower().strip()
        mode = str(data.get("mode", "define")).lower().strip()
    except (json.JSONDecodeError, TypeError):
        return "error: invalid payload — provide JSON with 'word'"

    if not word:
        return "error: 'word' is required"

    # Built-in mini dictionary of common words
    _dictionary = {
        "algorithm": {"pos": "noun", "definition": "A step-by-step procedure for solving a problem or accomplishing a task.", "synonyms": ["procedure", "method", "formula", "process"]},
        "api": {"pos": "noun", "definition": "Application Programming Interface; a set of defined rules that enable different software to communicate.", "synonyms": ["interface", "protocol", "contract"]},
        "data": {"pos": "noun", "definition": "Facts and statistics collected together for reference or analysis.", "synonyms": ["information", "facts", "statistics", "records"]},
        "function": {"pos": "noun", "definition": "A reusable block of code that performs a specific task.", "synonyms": ["routine", "subroutine", "method", "procedure"]},
        "python": {"pos": "noun", "definition": "A high-level, interpreted programming language known for readability.", "synonyms": []},
        "recursion": {"pos": "noun", "definition": "A technique where a function calls itself to solve a problem by breaking it into smaller subproblems.", "synonyms": ["self-reference", "recurrence"]},
        "variable": {"pos": "noun", "definition": "A named storage location in memory that holds a value which can change during program execution.", "synonyms": ["identifier", "symbol", "placeholder"]},
        "compile": {"pos": "verb", "definition": "To translate source code written in a high-level language into machine code.", "synonyms": ["build", "translate", "assemble"]},
        "debug": {"pos": "verb", "definition": "To identify and remove errors from computer software or hardware.", "synonyms": ["troubleshoot", "fix", "diagnose"]},
        "deploy": {"pos": "verb", "definition": "To release and install software to a production environment where users can access it.", "synonyms": ["release", "launch", "publish", "roll out"]},
    }

    if word not in _dictionary:
        return json.dumps({
            "word": word,
            "found": False,
            "message": f"Word '{word}' not found in the built-in dictionary. Try a common technical term.",
        }, indent=2)

    entry = _dictionary[word]
    if mode == "define":
        return json.dumps({"word": word, "pos": entry["pos"], "definition": entry["definition"]}, indent=2)
    elif mode == "synonyms":
        return json.dumps({"word": word, "synonyms": entry["synonyms"]}, indent=2)
    elif mode == "full":
        return json.dumps(entry, indent=2)
    else:
        return json.dumps(entry, indent=2)


TOOL_SPEC = {
    "name": "dictionary_lookup",
    "description": "Look up a word's definition, part of speech, and synonyms from a built-in dictionary of common technical terms.",
    "category": "search",
    "domain": "education",
    "risk_level": "read",
    "schema": {
        "type": "object",
        "properties": {
            "word": {
                "type": "string",
                "description": "The word to look up (lowercase, English)."
            },
            "mode": {
                "type": "string",
                "description": "Lookup mode: define (definition only), synonyms (synonyms only), or full (all info).",
                "enum": ["define", "synonyms", "full"],
                "default": "define"
            }
        },
        "required": ["word"]
    }
}
