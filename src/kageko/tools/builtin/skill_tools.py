"""Agent tools for skill management (skill_list, skill_view, skill_extract,
skill_delete, skill_pin, skill_unpin, skill_patch, curator_run).

Hermes-aligned: progressive loading, self-patching, pin protection.
"""

from __future__ import annotations

from typing import Any

_store: Any = None  # SkillStore, wired at startup
_curator: Any = None  # Curator, wired at startup


def wire_skill_store(store) -> None:
    global _store
    _store = store


def wire_curator(curator) -> None:
    global _curator
    _curator = curator


# ── Skill CRUD ───────────────────────────────────────────────────────────


async def skill_list(args: dict[str, Any]) -> str:
    if _store is None:
        return "[ERROR] Skill store not wired."
    skills = await _store.list_all()
    if not skills:
        return "(no skills stored)"
    lines = []
    for s in skills:
        pinned = "📌" if s.pinned else " "
        lines.append(f"* {pinned}{s.name} [v{s.version}] [{s.state}] — {s.description[:80]}")
    return f"{len(skills)} skills:\n" + "\n".join(lines)


async def skill_view(args: dict[str, Any]) -> str:
    name = args.get("name", "")
    if not name:
        return "[ERROR] Missing 'name'"
    if _store is None:
        return "[ERROR] Skill store not wired."
    record = await _store.view(name)
    if not record:
        return f"[ERROR] Skill '{name}' not found."
    tags = ", ".join(record.tags) if record.tags else "none"
    return (
        f"# {record.name} (v{record.version}, {record.state}{' 📌' if record.pinned else ''})\n"
        f"Description: {record.description}\n"
        f"Trigger: {record.trigger}\n"
        f"Tags: {tags}\n"
        f"---\n{record.content}"
    )


async def skill_extract(args: dict[str, Any]) -> str:
    history = args.get("history", "")
    if not history:
        return "[ERROR] Missing 'history' — pass recent conversation text."
    if _store is None:
        return "[ERROR] Skill store not wired."
    if not _store.llm:
        return "[ERROR] Skill store has no LLM wired."
    record = await _store.extract_from_conversation(history)
    if not record:
        return "No reusable skill pattern found."
    steps = "\n".join(f"  - {s}" for s in record.steps[:10]) if record.steps else "  (no steps)"
    return (
        f"Extracted & saved skill '{record.name}' v{record.version}\n"
        f"  Description: {record.description}\n"
        f"  Trigger: {record.trigger}\n"
        f"  Steps:\n{steps}"
    )


async def skill_delete(args: dict[str, Any]) -> str:
    name = args.get("name", "")
    if not name:
        return "[ERROR] Missing 'name'"
    if _store is None:
        return "[ERROR] Skill store not wired."
    if args.get("archive", False):
        await _store.archive(name)
        return f"Archived skill '{name}'."
    await _store.delete(name)
    return f"Deleted skill '{name}'."


# ── Pin / Unpin ─────────────────────────────────────────────────────────


async def skill_pin(args: dict[str, Any]) -> str:
    name = args.get("name", "")
    if not name:
        return "[ERROR] Missing 'name'"
    if _store is None:
        return "[ERROR] Skill store not wired."
    ok = await _store.pin(name)
    return f"Pinned skill '{name}'." if ok else f"Skill '{name}' not found."


async def skill_unpin(args: dict[str, Any]) -> str:
    name = args.get("name", "")
    if not name:
        return "[ERROR] Missing 'name'"
    if _store is None:
        return "[ERROR] Skill store not wired."
    ok = await _store.unpin(name)
    return f"Unpinned skill '{name}'." if ok else f"Skill '{name}' not found."


# ── Self-patch ──────────────────────────────────────────────────────────


async def skill_patch(args: dict[str, Any]) -> str:
    name = args.get("name", "")
    find = args.get("find", "")
    replace = args.get("replace", "")
    if not name or not find:
        return "[ERROR] Missing 'name' and/or 'find'"
    if _store is None:
        return "[ERROR] Skill store not wired."
    ok = await _store.patch(name, find, replace)
    if ok:
        return f"Patched skill '{name}': '{find[:60]}' → '{replace[:60]}'."
    return f"[ERROR] Pattern '{find[:60]}' not found in '{name}'."


# ── Curator ─────────────────────────────────────────────────────────────


async def curator_run(args: dict[str, Any]) -> str:
    if _curator is None:
        return "[ERROR] Curator not wired."
    # Run full maintenance + QAOA pipeline
    actions = await _curator.maintain()
    # Also run explicit QAOA report if curator has LLM
    qaoa_report = ""
    if hasattr(_curator, "run_qaoa_pipeline"):
        qaoa_report = "\n\n" + await _curator.run_qaoa_pipeline()
    if not actions and not qaoa_report.strip():
        return "Curator ran: no actions needed."
    return f"Curator ran: {len(actions)} actions.\n" + "\n".join(f"  - {a}" for a in actions) + qaoa_report


# ── Tool definitions ────────────────────────────────────────────────────


SKILL_TOOLS = [
    {"name": "skill_list", "fn": skill_list, "category": "learning",
     "description": "List stored skills with name, version, state (active/stale/archived), pinned status.",
     "parameters": {"type": "object", "properties": {}, "required": []}},

    {"name": "skill_view", "fn": skill_view, "category": "learning",
     "description": "Load full content of a skill by name. Use this before executing a skill's workflow.",
     "parameters": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}},

    {"name": "skill_extract", "fn": skill_extract, "category": "learning",
     "description": "Extract a reusable skill from conversation history. Triggers: complex multi-step task, error recovery, or user correction.",
     "parameters": {"type": "object", "properties": {"history": {"type": "string"}}, "required": ["history"]}},

    {"name": "skill_delete", "fn": skill_delete, "category": "learning",
     "description": "Delete or archive a skill by name.",
     "parameters": {"type": "object", "properties": {"name": {"type": "string"}, "archive": {"type": "boolean", "description": "Archive instead of delete"}}, "required": ["name"]}},

    {"name": "skill_pin", "fn": skill_pin, "category": "learning",
     "description": "Pin a skill to protect it from automatic archival.",
     "parameters": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}},

    {"name": "skill_unpin", "fn": skill_unpin, "category": "learning",
     "description": "Unpin a skill so the curator can archive it when stale.",
     "parameters": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}},

    {"name": "skill_patch", "fn": skill_patch, "category": "learning",
     "description": "Surgically update a skill's content with find-and-replace. Patch only the broken part — don't rewrite the whole thing.",
     "parameters": {"type": "object", "properties": {"name": {"type": "string"}, "find": {"type": "string"}, "replace": {"type": "string"}}, "required": ["name", "find", "replace"]}},

    {"name": "curator_run", "fn": curator_run, "category": "learning",
     "description": "Run curator maintenance: stale→archive, safety audit, overlap detection.",
     "parameters": {"type": "object", "properties": {}, "required": []}},
]
