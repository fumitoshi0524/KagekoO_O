from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from kageko.data.db import KagekoDB


@dataclass
class Skill:
    name: str
    version: str
    trigger: str
    description: str
    content: str
    tags: list[str] = field(default_factory=list)

    @classmethod
    def from_markdown(cls, path: str) -> Skill:
        text = Path(path).read_text(encoding="utf-8")
        return cls._parse(text)

    @classmethod
    def _parse(cls, text: str) -> Skill:
        # Extract frontmatter
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.DOTALL)
        if not match:
            raise ValueError("Invalid skill format: missing frontmatter")

        fm_text = match.group(1)
        content = match.group(2)

        # Parse frontmatter key-value pairs
        fm = {}
        for line in fm_text.strip().split("\n"):
            if ":" in line:
                key, _, value = line.partition(":")
                key = key.strip()
                value = value.strip()
                # Parse list values like [devops, deployment]
                if value.startswith("[") and value.endswith("]"):
                    value = [v.strip().strip("'\"") for v in value[1:-1].split(",")]
                fm[key] = value

        if "name" not in fm:
            raise ValueError("Skill frontmatter must contain 'name'")

        return cls(
            name=fm["name"],
            version=fm.get("version", "0.1.0"),
            trigger=fm.get("trigger", ""),
            description=fm.get("description", ""),
            content=content.strip(),
            tags=fm.get("tags", []) if isinstance(fm.get("tags"), list) else [],
        )

    def to_markdown(self) -> str:
        tags_str = "[" + ", ".join(self.tags) + "]" if self.tags else "[]"
        return f"""---
name: {self.name}
version: {self.version}
trigger: {self.trigger}
description: {self.description}
tags: {tags_str}
---

{self.content}
"""


class SkillEngine:
    def __init__(self, db: KagekoDB):
        self.db = db

    async def save(self, skill: Skill) -> None:
        await self.db.save_skill(
            name=skill.name,
            version=skill.version,
            trigger=skill.trigger,
            description=skill.description,
            content=skill.to_markdown(),
            tags=skill.tags,
        )

    async def search(self, query: str) -> list[Skill]:
        records = await self.db.search_skills(query)
        return [
            Skill(
                name=r.name,
                version=r.version,
                trigger=r.trigger,
                description=r.description,
                content=r.content,
                tags=r.tags,
            )
            for r in records
        ]
