from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from kageko.types import Message


def validate_frontmatter(
    *,
    name: str | None = None,
    trigger: str | None = None,
    description: str | None = None,
    version: str | None = None,
    tags: list[str] | None = None,
) -> list[str]:
    """Return a list of validation error strings. Empty list = valid."""
    errors: list[str] = []
    if not name:
        errors.append("name is required")
    if not version:
        errors.append("version is required")
    if not trigger:
        errors.append("trigger is required")
    if not description:
        errors.append("description is required")
    if name and not re.match(r"^[a-z0-9][a-z0-9\\-]*$", name):
        errors.append("name must be kebab-case (lowercase alphanumeric + hyphens)")
    return errors


@dataclass
class Skill:
    name: str
    version: str
    description: str
    trigger: str
    tags: list[str]
    steps: list[str]
    content: str = ""


class SkillEngine:
    """Dual-layer skill system: Layer 1 (conversation) + Layer 2 (QAOA)."""

    def __init__(self, db: Any, llm: Any) -> None:
        self.db = db
        self.llm = llm

    def validate(self, **kwargs: Any) -> list[str]:
        return validate_frontmatter(**kwargs)

    def render_template(
        self, content: str, skill_dir: str = "", session_id: str = "",
    ) -> str:
        """Substitute template variables and inline shell commands."""
        content = content.replace("${KAGEKO_SKILL_DIR}", skill_dir)
        content = content.replace("${KAGEKO_SESSION_ID}", session_id)

        def _exec_inline(match: re.Match) -> str:
            cmd = match.group(1)
            try:
                result = subprocess.run(
                    cmd, shell=True, capture_output=True, text=True, timeout=5
                )
                return result.stdout.strip()[:4000]
            except Exception:
                return f"[shell error: {cmd}]"

        content = re.sub(r'!`([^`]+)`', _exec_inline, content)
        return content

    async def create_from_conversation(self, messages: list[dict]) -> dict | None:
        """Layer 1: Extract skill from conversation messages."""
        prompt = (
            "Extract a reusable skill from this conversation. "
            "Write ALL fields (name, description, trigger, steps) in **English**, "
            "regardless of the conversation language.\n"
            "Return JSON with: name, version, description, trigger, tags, steps.\n\n"
            + "\n".join(f"{m['role']}: {m['content'][:200]}" for m in messages[-6:])
        )
        response = await self.llm.chat([Message(role="user", content=prompt)])
        try:
            skill_data = json.loads(response.content)
            errors = validate_frontmatter(
                name=skill_data.get("name", ""),
                version=skill_data.get("version", ""),
                trigger=skill_data.get("trigger", ""),
                description=skill_data.get("description", ""),
            )
            if errors:
                return None
            return skill_data
        except (json.JSONDecodeError, KeyError):
            return None

    async def search(self, query: str, limit: int = 5) -> list[dict]:
        """Search skills via FTS5."""
        skills = await self.db.search_skills(query)
        return [
            {"name": s.name, "description": s.description, "trigger": s.trigger, "tags": s.tags}
            for s in skills[:limit]
        ]
