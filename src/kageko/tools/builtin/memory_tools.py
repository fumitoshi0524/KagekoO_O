"""Agent tools for memory management (Hermes-style single `memory` tool).

Design:
- ONE tool with `action` parameter: add, replace, remove
- replace/remove use substring matching (no IDs needed)
- Tool description itself acts as the guidance — tells the agent
  WHEN to save, WHAT to save, and what to SKIP.
"""

from __future__ import annotations

from typing import Any

_store: Any = None  # MemoryStore, wired at startup


def wire_memory_store(store) -> None:
    global _store
    _store = store


async def memory_handler(args: dict[str, Any]) -> str:
    """Dispatch memory tool actions: add, replace, remove."""
    if _store is None:
        return "[ERROR] Memory store not wired."
    action = args.get("action", "add")
    target = args.get("target", "memory")
    content = args.get("content", "")
    old_text = args.get("old_text", "")

    if action == "add":
        if not content:
            return "[ERROR] 'content' required for add action"
        f = await _store.add(content.strip(), source="fact")
        usage = await _store.usage()
        return f"✓ Added. {usage['pct']}% full — {usage['char_count']:,}/{usage['limit']:,} chars, {usage['count']} facts."

    elif action == "replace":
        if not old_text:
            return "[ERROR] 'old_text' required for replace action"
        if not content:
            return "[ERROR] 'content' required for replace action"
        count = await _store.replace(old_text.strip(), content.strip())
        if not count:
            return f"No fact matched '{old_text[:80]}'."
        usage = await _store.usage()
        return f"✓ Replaced {count} fact(s). {usage['pct']}% full — {usage['char_count']:,}/{usage['limit']:,} chars."

    elif action == "remove":
        if not old_text:
            return "[ERROR] 'old_text' required for remove action"
        count = await _store.delete(substring=old_text.strip())
        if not count:
            return f"No fact matched '{old_text[:80]}'."
        usage = await _store.usage()
        return f"✓ Removed {count} fact(s). {usage['pct']}% full — {usage['char_count']:,}/{usage['limit']:,} chars."

    return f"[ERROR] Unknown action '{action}'. Use: add, replace, remove."


# ── Standalone tools (for agent use when it needs to browse) ────────────


async def memory_list(args: dict[str, Any]) -> str:
    """List all stored facts."""
    if _store is None:
        return "[ERROR] Memory store not wired."
    facts = await _store.list(limit=100)
    if not facts:
        return "(no facts stored)"
    usage = await _store.usage()
    lines = [f"{usage['pct']}% full — {usage['count']} facts, {usage['char_count']:,}/{usage['limit']:,} chars"]
    lines += [f"  {f.content}" for f in facts]
    return "\n".join(lines)


# ── Tool definitions ────────────────────────────────────────────────────


MEMORY_TOOL = {
    "name": "memory",
    "description": (
        "Save durable information to persistent memory that survives across sessions. "
        "Memory is injected into future conversations, so keep it compact.\n\n"
        "WHEN TO SAVE (do this proactively, don't wait to be asked):\n"
        "- User corrects you or says 'remember this'\n"
        "- User shares a preference, habit, or technical setup detail\n"
        "- You discover something about the environment (OS, installed tools, project conventions)\n"
        "- You learn a convention, tool quirk, or workflow specific to this setup\n"
        "- You identify a stable fact that will be useful again\n\n"
        "PRIORITY: user preferences & corrections > environment facts > procedural knowledge\n"
        "The most valuable memory prevents the user from having to repeat themselves.\n\n"
        "Do NOT save: task progress, session outcomes, completed-work logs, "
        "temporary state, one-off results, chit-chat, working directories.\n\n"
        "ACTIONS:\n"
        "- add: store a new fact (one sentence, English)\n"
        "- replace: update an existing fact — old_text identifies it by substring match\n"
        "- remove: delete a fact — old_text identifies it by substring match\n\n"
        "SKIP trivial/obvious info, things easily re-discovered, and anything that won't age."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["add", "replace", "remove"],
                "description": "The action to perform.",
            },
            "content": {
                "type": "string",
                "description": "The fact text. Required for 'add' and 'replace'.",
            },
            "old_text": {
                "type": "string",
                "description": "Short unique substring identifying the entry to replace or remove.",
            },
        },
        "required": ["action"],
    },
    "category": "learning",
}

MEMORY_LIST_TOOL = {
    "name": "memory_list",
    "description": "List all stored facts in long-term memory. Shows usage and content.",
    "parameters": {"type": "object", "properties": {}, "required": []},
    "category": "learning",
}

MEMORY_TOOLS = [
    {"name": MEMORY_TOOL["name"], "fn": memory_handler, "category": "learning",
     "description": MEMORY_TOOL["description"], "parameters": MEMORY_TOOL["parameters"]},
    {"name": MEMORY_LIST_TOOL["name"], "fn": memory_list, "category": "learning",
     "description": MEMORY_LIST_TOOL["description"], "parameters": MEMORY_LIST_TOOL["parameters"]},
]
