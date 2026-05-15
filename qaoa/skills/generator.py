"""Skill generator — creates QAOA UniToolCall skills on demand via LLM."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import TYPE_CHECKING

from ..types import SkillSpec, FUNCTIONAL_CATEGORIES, APPLICATION_DOMAINS

try:
    import yaml as _yaml
except ImportError:
    _yaml = None

if TYPE_CHECKING:
    from ..adapters.llm import LLMResponse


QAOA_SKILL_PROMPT = """You are a skill designer for Kageko Agent. Create a skill following the UniToolCall standard (arXiv:2604.11557).

CRITICAL: Use the exact name provided below. Do not invent a new name.

The skill must follow this structure:

---
name: {name}
description: One-line summary of what this skill does
category: {categories}
domain: {domains}
tools:
  - tool.name
permissions:
  - read
  - write
---

# Skill: {name}

## Objective
Clear one-sentence goal.

## Tools
- tool.name: when and how to use it. Every skill that creates or modifies files MUST include both file.write AND bash.run. Exploration skills MUST include file.read.

## Steps
1. First step — concrete action
2. Second step — concrete action
...

## Safety
Any constraints or warnings.

Pick ONE category and ONE domain from the lists above that best fit this skill.
Available tools: {tools}

User request: {query}"""


@dataclass(slots=True, kw_only=True)
class SkillGenerator:
    llm: object
    tools: object
    output_dir: Path = Path("./skills")

    def generate(self, query: str) -> SkillSpec:
        tool_names = [s.name for s in self.tools.list_specs()
                      if not s.name.startswith("skill.")]

        # Extract requested name from query: "name: description" or just "name"
        name = query.split(":")[0].strip().replace(" ", "_") if ":" in query else query.strip().replace(" ", "_")[:30]
        description = query.split(":", 1)[1].strip() if ":" in query else query.strip()

        prompt = QAOA_SKILL_PROMPT.format(
            name=name,
            query=query,
            tools=json.dumps(tool_names),
            categories=", ".join(FUNCTIONAL_CATEGORIES),
            domains=", ".join(APPLICATION_DOMAINS),
        )

        raw = self.llm.complete_text(prompt)
        skill = self._parse_markdown_skill(raw, description)
        # Preserve the requested name over whatever the LLM generated
        if skill.name != name:
            skill = SkillSpec(
                name=name,
                description=skill.description,
                instructions=skill.instructions,
                allowed_tools=skill.allowed_tools,
                permissions=skill.permissions,
                metadata=skill.metadata,
                source_path=skill.source_path,
                format=skill.format,
            )
        return skill

    def _parse_markdown_skill(self, raw: str, fallback_query: str) -> SkillSpec:
        """Parse a full markdown skill document with YAML frontmatter."""
        import re

        # Strip code fences if LLM wrapped the output
        text = raw.strip()
        for fence in ("```yaml", "```markdown", "```md", "```"):
            if text.startswith(fence):
                text = text[len(fence):].strip()
            if text.endswith("```"):
                text = text[:-3].strip()
        text = text.strip()

        meta: dict = {}
        body = text

        fm_match = re.match(
            r"\A---\s*\r?\n(.*?)\r?\n---\s*(.*)\Z",
            text, re.DOTALL,
        )
        if fm_match:
            try:
                if _yaml:
                    meta = _yaml.safe_load(fm_match.group(1)) or {}
                else:
                    meta = self._parse_simple_yaml(fm_match.group(1))
            except Exception:
                meta = self._parse_simple_yaml(fm_match.group(1))
            body = fm_match.group(2).strip()

        name = str(meta.get("name", "generated-skill")).strip().replace(" ", "_")[:30] or "generated-skill"
        description = str(meta.get("description", fallback_query[:80]))
        allowed_tools = meta.get("tools", [])
        if isinstance(allowed_tools, str):
            allowed_tools = [t.strip() for t in allowed_tools.split(",")]
        if not isinstance(allowed_tools, list):
            allowed_tools = []
        permissions = meta.get("permissions", [])
        if isinstance(permissions, str):
            permissions = [p.strip() for p in permissions.split(",")]
        if not isinstance(permissions, list):
            permissions = []

        return SkillSpec(
            name=name,
            description=description,
            instructions=body or text,
            allowed_tools=allowed_tools,
            permissions=permissions,
            metadata={
                "category": meta.get("category", "operations"),
                "domain": meta.get("domain", "technology"),
                "tags": meta.get("tags", []),
            },
            format="qaoa-uni-tool-call",
        )

    @staticmethod
    def _parse_simple_yaml(raw: str) -> dict:
        result: dict = {}
        current_list_key: str | None = None
        for line in raw.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("- "):
                if current_list_key:
                    val = stripped[2:].strip().strip('"').strip("'")
                    lst = result.get(current_list_key, [])
                    if not isinstance(lst, list):
                        lst = []
                        result[current_list_key] = lst
                    lst.append(val)
                continue
            if ":" in stripped:
                key, _, value = stripped.partition(":")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if value == "":
                    result[key] = []
                    current_list_key = key
                else:
                    result[key] = value
                    current_list_key = key
        return result

    def save_to_disk(self, skill: SkillSpec) -> Path:
        skill_dir = self.output_dir / skill.name
        skill_dir.mkdir(parents=True, exist_ok=True)
        output_path = skill_dir / "SKILL.md"

        frontmatter = (
            f"---\n"
            f"name: {skill.name}\n"
            f"description: {skill.description}\n"
            f"format: {skill.format}\n"
            f"category: {skill.metadata.get('category', 'operations')}\n"
            f"domain: {skill.metadata.get('domain', 'technology')}\n"
        )
        if skill.allowed_tools:
            frontmatter += "tools:\n"
            for t in skill.allowed_tools:
                frontmatter += f"  - {t}\n"
        if skill.permissions:
            frontmatter += "permissions:\n"
            for p in skill.permissions:
                frontmatter += f"  - {p}\n"
        frontmatter += "---\n\n"

        output_path.write_text(frontmatter + skill.instructions, encoding="utf-8")
        return output_path
