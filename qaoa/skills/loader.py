"""Skill file loader — discovers and parses skill files from disk.

Refactored from BuiltinToolPack (qaoa/adapters/builtins.py lines 15-504).
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import tomllib
from typing import Any

from ..types import SkillSpec
from .conformance import ConformanceEngine

_SKILL_FILE_EXTENSIONS: tuple[str, ...] = (
    ".skill", ".md", ".markdown", ".toml", ".json", ".yaml", ".yml",
)
_DIRECTORY_SKILL_FILES: tuple[str, ...] = (
    "SKILL.md", "skill.md", "skill.markdown",
    "skill.toml", "skill.json", "skill.yaml", "skill.yml",
)
_FRONT_MATTER_PATTERN = re.compile(
    r"\A---\s*\r?\n(?P<header>.*?)\r?\n---\s*(?:\r?\n(?P<body>.*))?\Z",
    re.DOTALL,
)


@dataclass(slots=True, kw_only=True)
class SkillDocument:
    """Intermediate parse result before conversion to SkillSpec."""
    name: str
    source_path: Path
    content: str
    metadata: dict[str, Any]
    format: str


class SkillLoader:
    def __init__(self, skills_dirs: list[Path] | None = None) -> None:
        self._skills_dirs: list[Path] = skills_dirs or []
        self._conformance = ConformanceEngine()

    def add_dir(self, path: Path) -> None:
        if path not in self._skills_dirs:
            self._skills_dirs.append(path)

    def load_all(self) -> list[SkillSpec]:
        documents = self._discover_all()
        specs = [self._document_to_spec(doc) for doc in documents]
        for spec in specs:
            result = self._conformance.validate(spec)
            spec.metadata["conformance_passed"] = result.passed
            spec.metadata["conformance_score"] = result.score
            if not result.passed:
                spec.metadata["conformance_issues"] = result.issues
        return specs

    def load_one(self, name: str) -> SkillSpec:
        document = self._resolve(name)
        return self._document_to_spec(document)

    def discover_files(self) -> list[Path]:
        """Return all discovered skill file paths."""
        return [doc.source_path for doc in self._discover_all()]

    # ── Internal: discovery ──────────────────────────────────────────

    def _discover_all(self) -> list[SkillDocument]:
        discovered: dict[str, SkillDocument] = {}
        for base in self._skills_dirs:
            if not base.exists() or not base.is_dir():
                continue
            for file_path in sorted(base.glob("*")):
                if file_path.is_file() and file_path.suffix.lower() in _SKILL_FILE_EXTENSIONS:
                    doc = self._parse(file_path=file_path, default_name=file_path.stem, strict=False)
                    discovered.setdefault(doc.name, doc)
                elif file_path.is_dir():
                    for skill_file_name in _DIRECTORY_SKILL_FILES:
                        candidate = file_path / skill_file_name
                        if candidate.exists() and candidate.is_file():
                            doc = self._parse(file_path=candidate, default_name=file_path.name, strict=False)
                            discovered.setdefault(doc.name, doc)
                            break
        return sorted(discovered.values(), key=lambda d: d.name.lower())

    def _resolve(self, skill_name: str) -> SkillDocument:
        if skill_name == "":
            raise ValueError("Skill name cannot be empty.")
        requested = Path(skill_name)
        if requested.is_absolute() or ".." in requested.parts:
            raise ValueError("Skill name must be a relative identifier.")

        for base in self._skills_dirs:
            doc = self._find_in_base(base=base, skill_name=skill_name, strict=True)
            if doc is not None:
                return doc

        raise FileNotFoundError(
            f"Skill '{skill_name}' not found. "
            "Supported layouts: '<dir>/<name>.skill', '<dir>/<name>.md', "
            "'<dir>/<name>/SKILL.md', '<dir>/<name>/skill.toml'."
        )

    def _find_in_base(self, *, base: Path, skill_name: str, strict: bool) -> SkillDocument | None:
        if not base.exists() or not base.is_dir():
            return None
        requested = Path(skill_name)

        candidates: list[Path] = []
        if requested.suffix != "":
            candidates.append(base / requested)
        else:
            for ext in _SKILL_FILE_EXTENSIONS:
                candidates.append(base / f"{skill_name}{ext}")
        skill_dir = base / requested
        for name in _DIRECTORY_SKILL_FILES:
            candidates.append(skill_dir / name)

        for candidate in candidates:
            if not self._is_within_base(base, candidate):
                continue
            if candidate.exists() and candidate.is_file():
                default_name = requested.stem if requested.suffix != "" else requested.name
                if candidate.parent == skill_dir and candidate.parent.name != "":
                    default_name = candidate.parent.name
                return self._parse(file_path=candidate, default_name=default_name, strict=strict)
        return None

    @staticmethod
    def _is_within_base(base: Path, candidate: Path) -> bool:
        base_r = base.resolve()
        cand_r = candidate.resolve()
        return base_r == cand_r or base_r in cand_r.parents

    # ── Internal: parsing ────────────────────────────────────────────

    def _parse(self, *, file_path: Path, default_name: str, strict: bool) -> SkillDocument:
        raw = file_path.read_text(encoding="utf-8")
        suffix = file_path.suffix.lower()
        metadata: dict[str, Any] = {}
        content = raw
        normalized_format = suffix.lstrip(".")

        if suffix in (".md", ".markdown"):
            parsed = self._parse_markdown(raw=raw, strict=strict, source_path=file_path)
            metadata = parsed["metadata"]
            content = parsed["content"]
            normalized_format = parsed["format"]
        elif suffix == ".toml":
            metadata = self._parse_toml(raw=raw, strict=strict)
            normalized_format = "toml"
        elif suffix == ".skill":
            metadata = self._parse_toml(raw=raw, strict=False)
            normalized_format = "legacy-skill"
        elif suffix == ".json":
            metadata = self._parse_json(raw=raw, strict=strict)
            normalized_format = "json"
        elif suffix in (".yaml", ".yml"):
            metadata = self._parse_simple_yaml(raw=raw, strict=strict)
            normalized_format = "yaml"

        skill_name = str(metadata.get("name", default_name)).strip() or default_name
        description = metadata.get("description", "")
        metadata["name"] = skill_name
        metadata["description"] = str(description)
        return SkillDocument(
            name=skill_name, source_path=file_path,
            content=content, metadata=metadata, format=normalized_format,
        )

    def _parse_markdown(self, *, raw: str, strict: bool, source_path: Path) -> dict[str, Any]:
        match = _FRONT_MATTER_PATTERN.match(raw)
        if match is None:
            return {"metadata": {}, "content": raw, "format": "markdown"}
        header = match.group("header") or ""
        body = match.group("body") or ""
        metadata = self._parse_simple_yaml(raw=header, strict=strict)
        if "description" not in metadata and strict:
            raise ValueError(
                f"Skill markdown frontmatter in '{source_path}' requires 'description'."
            )
        return {"metadata": metadata, "content": body.strip(), "format": "markdown-frontmatter"}

    @staticmethod
    def _parse_toml(*, raw: str, strict: bool) -> dict[str, Any]:
        try:
            parsed = tomllib.loads(raw)
        except tomllib.TOMLDecodeError:
            if strict:
                raise
            return {}
        if isinstance(parsed, dict):
            return parsed
        if strict:
            raise ValueError("Skill TOML content must be a key-value mapping.")
        return {}

    @staticmethod
    def _parse_json(*, raw: str, strict: bool) -> dict[str, Any]:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            if strict:
                raise
            return {}
        if isinstance(parsed, dict):
            return parsed
        if strict:
            raise ValueError("Skill JSON content must be a JSON object.")
        return {}

    def _parse_simple_yaml(self, *, raw: str, strict: bool) -> dict[str, Any]:
        result: dict[str, Any] = {}
        current_list_key: str | None = None
        for line in raw.splitlines():
            stripped = line.strip()
            if stripped == "" or stripped.startswith("#"):
                continue
            if stripped.startswith("- "):
                if current_list_key is None:
                    if strict:
                        raise ValueError("YAML list item appears before any key.")
                    return {}
                value_text = stripped[2:].strip()
                lst = result.get(current_list_key)
                if not isinstance(lst, list):
                    lst = []
                    result[current_list_key] = lst
                lst.append(self._parse_scalar(value_text))
                continue
            if ":" not in stripped:
                if strict:
                    raise ValueError(f"Invalid YAML line: {line}")
                return {}
            key, value = stripped.split(":", 1)
            key_text = key.strip()
            value_text = value.strip()
            if key_text == "":
                if strict:
                    raise ValueError(f"Invalid YAML key in line: {line}")
                return {}
            if value_text == "":
                result[key_text] = []
                current_list_key = key_text
            else:
                result[key_text] = self._parse_scalar(value_text)
                current_list_key = key_text
        return result

    def _parse_scalar(self, raw_value: str) -> Any:
        value = raw_value.strip()
        if value == "":
            return ""
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            return value[1:-1]
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            if inner == "":
                return []
            return [self._parse_scalar(item) for item in inner.split(",")]
        lowered = value.lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
        if lowered in {"null", "none", "~"}:
            return None
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            return value

    # ── Internal: conversion to SkillSpec ────────────────────────────

    @staticmethod
    def _document_to_spec(doc: SkillDocument) -> SkillSpec:
        allowed_tools: list[str] = []
        raw_tools = doc.metadata.get("tools")
        if isinstance(raw_tools, list):
            allowed_tools = [str(t).strip() for t in raw_tools if str(t).strip() != ""]
        elif isinstance(raw_tools, str):
            allowed_tools = [t.strip() for t in raw_tools.split(",") if t.strip() != ""]

        permissions: list[str] = []
        raw_perms = doc.metadata.get("permissions")
        if isinstance(raw_perms, list):
            permissions = [str(p).strip() for p in raw_perms if str(p).strip() != ""]
        elif isinstance(raw_perms, str):
            permissions = [p.strip() for p in raw_perms.split(",") if p.strip() != ""]

        return SkillSpec(
            name=doc.name,
            description=str(doc.metadata.get("description", "")),
            instructions=doc.content,
            allowed_tools=allowed_tools,
            permissions=permissions,
            metadata=doc.metadata,
            source_path=doc.source_path,
            format=doc.format,
        )
