"""Skill format conversion — import skills from other agent ecosystems."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Any

from ..types import SkillSpec


@dataclass(slots=True, kw_only=True)
class SkillConverter:
    """Convert skills between formats using registered converters."""

    _converters: dict[str, Callable[[Path], SkillSpec]] = field(default_factory=dict)

    def register(self, source_format: str, converter: Callable[[Path], SkillSpec]) -> None:
        self._converters[source_format] = converter

    def convert(self, source: Path, source_format: str) -> SkillSpec:
        converter = self._converters.get(source_format)
        if converter is None:
            raise ValueError(
                f"No converter for format '{source_format}'. "
                f"Available: {', '.join(sorted(self._converters))}"
            )
        return converter(source)

    @property
    def supported_formats(self) -> list[str]:
        return sorted(self._converters)


# ── Format-specific converters ────────────────────────────────────────


def _convert_claude_code(path: Path) -> SkillSpec:
    """Convert a Claude Code skill (markdown + YAML frontmatter) to SkillSpec."""
    import re
    raw = path.read_text(encoding="utf-8")
    meta: dict[str, Any] = {}
    content = raw

    # Parse YAML frontmatter
    fm_match = re.match(
        r"\A---\s*\r?\n(?P<header>.*?)\r?\n---\s*(?:\r?\n(?P<body>.*))?\Z",
        raw, re.DOTALL,
    )
    if fm_match:
        header = fm_match.group("header") or ""
        body = fm_match.group("body") or ""
        content = body.strip()
        # Simple YAML key: value parsing
        for line in header.splitlines():
            stripped = line.strip()
            if stripped == "" or stripped.startswith("#"):
                continue
            if ":" in stripped:
                key, _, value = stripped.partition(":")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                meta[key] = value

    name = meta.get("name", path.stem)
    description = meta.get("description", "")
    allowed_tools: list[str] = []
    raw_tools = meta.get("tools")
    if isinstance(raw_tools, str):
        allowed_tools = [t.strip() for t in raw_tools.split(",") if t.strip() != ""]

    permissions: list[str] = []
    raw_perms = meta.get("permissions")
    if isinstance(raw_perms, str):
        permissions = [p.strip() for p in raw_perms.split(",") if p.strip() != ""]

    return SkillSpec(
        name=name,
        description=description,
        instructions=content,
        allowed_tools=allowed_tools,
        permissions=permissions,
        metadata={k: v for k, v in meta.items() if k not in ("name", "description", "tools", "permissions")},
        source_path=path,
        format="claude-code",
    )


def _convert_superpowers(path: Path) -> SkillSpec:
    """Convert a Superpowers skill (markdown with YAML frontmatter) to SkillSpec.

    Superpowers skills have a similar format to Claude Code skills but with
    different frontmatter conventions (e.g., 'name', 'description' in frontmatter,
    followed by detailed instructions).
    """
    import re
    raw = path.read_text(encoding="utf-8")
    meta: dict[str, Any] = {}
    content = raw

    fm_match = re.match(
        r"\A---\s*\r?\n(?P<header>.*?)\r?\n---\s*(?:\r?\n(?P<body>.*))?\Z",
        raw, re.DOTALL,
    )
    if fm_match:
        header = fm_match.group("header") or ""
        body = fm_match.group("body") or ""
        content = body.strip()
        current_list_key: str | None = None
        for line in header.splitlines():
            stripped = line.strip()
            if stripped == "" or stripped.startswith("#"):
                continue
            if stripped.startswith("- "):
                if current_list_key:
                    val = stripped[2:].strip().strip('"').strip("'")
                    existing = meta.get(current_list_key)
                    if not isinstance(existing, list):
                        existing = []
                        meta[current_list_key] = existing
                    existing.append(val)
                continue
            if ":" in stripped:
                key, _, value = stripped.partition(":")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if value == "":
                    meta[key] = []
                    current_list_key = key
                else:
                    meta[key] = value
                    current_list_key = key

    name = meta.get("name", path.stem)
    # Superpowers uses "description" or "description" interchangeably
    description = str(meta.get("description", meta.get("description", "")))
    allowed_tools: list[str] = []
    raw_tools = meta.get("tools", meta.get("allowed_tools"))
    if isinstance(raw_tools, list):
        allowed_tools = [str(t).strip() for t in raw_tools]
    elif isinstance(raw_tools, str):
        allowed_tools = [t.strip() for t in raw_tools.split(",") if t.strip() != ""]

    permissions: list[str] = []
    raw_perms = meta.get("permissions")
    if isinstance(raw_perms, list):
        permissions = [str(p).strip() for p in raw_perms]
    elif isinstance(raw_perms, str):
        permissions = [p.strip() for p in raw_perms.split(",") if p.strip() != ""]

    return SkillSpec(
        name=name,
        description=description,
        instructions=content,
        allowed_tools=allowed_tools,
        permissions=permissions,
        metadata={k: v for k, v in meta.items()
                  if k not in ("name", "description", "tools", "allowed_tools", "permissions")},
        source_path=path,
        format="superpowers",
    )


# ── Converter instances ───────────────────────────────────────────────

ClaudeCodeConverter = _convert_claude_code
SuperpowersConverter = _convert_superpowers


def create_default_converter() -> SkillConverter:
    converter = SkillConverter()
    converter.register("claude-code", _convert_claude_code)
    converter.register("superpowers", _convert_superpowers)
    converter.register("kageko-native", _convert_claude_code)  # same format
    return converter
