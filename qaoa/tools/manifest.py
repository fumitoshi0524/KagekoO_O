"""Tool manifest for tracking generated tools."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True, frozen=True, kw_only=True)
class ToolEntry:
    name: str
    module: str
    category: str
    domain: str
    description: str
    schema: dict[str, Any]
    version: str = "1.0.0"


@dataclass(slots=True, kw_only=True)
class ToolManifest:
    version: str
    generated_at: str
    tools: list[ToolEntry] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "generated_at": self.generated_at,
            "tools": [
                {
                    "name": t.name,
                    "module": t.module,
                    "category": t.category,
                    "domain": t.domain,
                    "description": t.description,
                    "schema": t.schema,
                    "version": t.version,
                }
                for t in self.tools
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ToolManifest:
        tools = []
        for t in data.get("tools", []):
            tools.append(
                ToolEntry(
                    name=str(t["name"]),
                    module=str(t["module"]),
                    category=str(t.get("category", "utility")),
                    domain=str(t.get("domain", "general")),
                    description=str(t.get("description", "")),
                    schema=t.get("schema", {}),
                    version=str(t.get("version", "1.0.0")),
                )
            )
        return cls(
            version=str(data.get("version", "0.0.0")),
            generated_at=str(data.get("generated_at", "")),
            tools=tools,
        )


def load_manifest(path: str | Path) -> ToolManifest:
    manifest_path = Path(path)
    if not manifest_path.exists():
        return ToolManifest(version="0.0.0", generated_at="", tools=[])
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    return ToolManifest.from_dict(data)
