"""Builtin tool pack and external skill loading."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import subprocess
import tomllib
from typing import Any

from .tools import ToolRegistry

_SKILL_FILE_EXTENSIONS: tuple[str, ...] = (
    ".skill",
    ".md",
    ".markdown",
    ".toml",
    ".json",
    ".yaml",
    ".yml",
)
_DIRECTORY_SKILL_FILES: tuple[str, ...] = (
    "SKILL.md",
    "skill.md",
    "skill.markdown",
    "skill.toml",
    "skill.json",
    "skill.yaml",
    "skill.yml",
)
_FRONT_MATTER_PATTERN = re.compile(
    r"\A---\s*\r?\n(?P<header>.*?)\r?\n---\s*(?:\r?\n(?P<body>.*))?\Z",
    re.DOTALL,
)


@dataclass(slots=True, kw_only=True)
class SkillDocument:
    name: str
    source_path: Path
    content: str
    metadata: dict[str, Any]
    format: str


@dataclass(slots=True, kw_only=True)
class BuiltinToolPack:
    workspace: Path
    skills_dir: Path | None = None

    def register(self, registry: ToolRegistry) -> None:
        registry.register(
            "echo",
            self._echo,
            description="Echo back the payload unchanged.",
            input_contract="any plain text",
            output_contract="same plain text",
            tags=("utility",),
            risk_level="read",
            category="system",
            domain="technology",
        )
        registry.register(
            "file.read",
            self._file_read,
            description="Read UTF-8 text file content from workspace-relative path.",
            input_contract="workspace-relative file path",
            output_contract="full file content as text",
            tags=("filesystem", "read"),
            risk_level="read",
            category="search",
            domain="technology",
        )
        registry.register(
            "file.write",
            self._file_write,
            description="Write UTF-8 text content to workspace-relative path.",
            input_contract="'<relative_path>\\n<content>'",
            output_contract="'wrote:<relative_path>' confirmation",
            tags=("filesystem", "write"),
            risk_level="write",
            category="operations",
            domain="technology",
        )
        registry.register(
            "bash.run",
            self._bash_run,
            description="Execute a shell command inside workspace.",
            input_contract="shell command string",
            output_contract="stdout text or '<no-output>'",
            tags=("shell",),
            risk_level="destructive",
            category="operations",
            domain="technology",
        )
        registry.register(
            "todo.write",
            self._todo_write,
            description="Append one TODO item to workspace TODO.md.",
            input_contract="'title|details' (details optional)",
            output_contract="'todo-added:<title>' confirmation",
            tags=("productivity",),
            risk_level="write",
            category="operations",
            domain="business",
        )
        registry.register(
            "skill.load",
            self._skill_load,
            description="Load raw skill instruction text.",
            input_contract="skill name identifier",
            output_contract="skill content text",
            tags=("skills",),
            risk_level="read",
            category="search",
            domain="technology",
        )
        registry.register(
            "skill.describe",
            self._skill_describe,
            description="Return normalized metadata for one skill as JSON.",
            input_contract="skill name identifier",
            output_contract="JSON object text",
            tags=("skills", "metadata"),
            risk_level="read",
            category="search",
            domain="technology",
        )
        registry.register(
            "skill.list",
            self._skill_list,
            description="List discoverable skills as JSON array.",
            input_contract="optional query filter",
            output_contract="JSON array text",
            tags=("skills", "metadata"),
            risk_level="read",
            category="search",
            domain="technology",
        )

    def _echo(self, payload: str) -> str:
        return payload

    def _file_read(self, payload: str) -> str:
        target = self._safe_path(payload.strip())
        return target.read_text(encoding="utf-8")

    def _file_write(self, payload: str) -> str:
        parts = payload.split("\n", 1)
        if len(parts) != 2:
            raise ValueError(
                "file.write payload must be '<relative_path>\\n<content>'."
            )
        relative_path = parts[0].strip()
        content = parts[1]
        target = self._safe_path(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"wrote:{target.relative_to(self.workspace)}"

    def _bash_run(self, payload: str) -> str:
        command = payload.strip()
        if command == "":
            raise ValueError("bash.run payload cannot be empty.")
        completed = subprocess.run(
            command,
            shell=True,
            check=False,
            capture_output=True,
            text=True,
            cwd=str(self.workspace),
        )
        stdout = completed.stdout.strip()
        stderr = completed.stderr.strip()
        if completed.returncode != 0:
            raise RuntimeError(
                f"bash.run failed (exit={completed.returncode}). stderr={stderr or '<none>'}"
            )
        return stdout if stdout != "" else "<no-output>"

    def _todo_write(self, payload: str) -> str:
        parts = payload.split("|", 1)
        title = parts[0].strip()
        details = parts[1].strip() if len(parts) > 1 else ""
        if title == "":
            raise ValueError("todo.write requires title in payload 'title|details'.")
        todo_file = self.workspace / "TODO.md"
        if todo_file.exists():
            existing = todo_file.read_text(encoding="utf-8")
        else:
            existing = "# TODO\n\n"
        line = f"- [ ] {title}"
        if details != "":
            line = f"{line} 鈥?{details}"
        updated = existing.rstrip() + f"\n{line}\n"
        todo_file.write_text(updated, encoding="utf-8")
        return f"todo-added:{title}"

    def _skill_load(self, payload: str) -> str:
        skill_name = payload.strip()
        document = self._resolve_skill_document(skill_name)
        return document.content

    def _skill_describe(self, payload: str) -> str:
        skill_name = payload.strip()
        document = self._resolve_skill_document(skill_name)
        return json.dumps(self._document_payload(document), ensure_ascii=False)

    def _skill_list(self, payload: str) -> str:
        query = payload.strip().lower()
        documents = self._discover_skill_documents()
        payloads = [self._document_payload(document) for document in documents]
        if query != "":
            payloads = [
                item
                for item in payloads
                if query in item["name"].lower()
                or query in item["description"].lower()
                or query in item["format"].lower()
            ]
        return json.dumps(payloads, ensure_ascii=False)

    def _candidate_skill_dirs(self) -> list[Path]:
        dirs: list[Path] = []
        if self.skills_dir is not None:
            dirs.append(self.skills_dir)
        dirs.append(self.workspace / "skills")
        return dirs

    def _resolve_skill_document(self, skill_name: str) -> SkillDocument:
        if skill_name == "":
            raise ValueError("skill.load requires a skill name.")
        requested = Path(skill_name)
        if requested.is_absolute() or ".." in requested.parts:
            raise ValueError("Skill name must be a relative identifier.")

        for base in self._candidate_skill_dirs():
            document = self._find_in_base(base=base, skill_name=skill_name, strict=True)
            if document is not None:
                return document

        raise FileNotFoundError(
            "Skill '{}' not found. Supported layouts: "
            "'<skills_dir>/<name>.skill', '<skills_dir>/<name>.md', "
            "'<skills_dir>/<name>/SKILL.md', '<skills_dir>/<name>/skill.toml'.".format(
                skill_name
            )
        )

    def _discover_skill_documents(self) -> list[SkillDocument]:
        discovered: dict[str, SkillDocument] = {}
        for base in self._candidate_skill_dirs():
            if not base.exists() or not base.is_dir():
                continue

            for file_path in sorted(base.glob("*")):
                if file_path.is_file() and file_path.suffix.lower() in _SKILL_FILE_EXTENSIONS:
                    document = self._parse_skill_file(
                        file_path=file_path,
                        default_name=file_path.stem,
                        strict=False,
                    )
                    discovered.setdefault(document.name, document)
                elif file_path.is_dir():
                    for skill_file_name in _DIRECTORY_SKILL_FILES:
                        candidate = file_path / skill_file_name
                        if candidate.exists() and candidate.is_file():
                            document = self._parse_skill_file(
                                file_path=candidate,
                                default_name=file_path.name,
                                strict=False,
                            )
                            discovered.setdefault(document.name, document)
                            break
        return sorted(discovered.values(), key=lambda item: item.name.lower())

    def _find_in_base(
        self,
        *,
        base: Path,
        skill_name: str,
        strict: bool,
    ) -> SkillDocument | None:
        if not base.exists() or not base.is_dir():
            return None

        requested = Path(skill_name)
        candidates: list[Path] = []
        if requested.suffix != "":
            candidates.append(base / requested)
        else:
            for extension in _SKILL_FILE_EXTENSIONS:
                candidates.append(base / f"{skill_name}{extension}")

        skill_dir = base / requested
        for skill_file_name in _DIRECTORY_SKILL_FILES:
            candidates.append(skill_dir / skill_file_name)

        for candidate in candidates:
            if not self._is_within_base(base, candidate):
                continue
            if candidate.exists() and candidate.is_file():
                default_name = requested.stem if requested.suffix != "" else requested.name
                if candidate.parent == skill_dir and candidate.parent.name != "":
                    default_name = candidate.parent.name
                return self._parse_skill_file(
                    file_path=candidate,
                    default_name=default_name,
                    strict=strict,
                )
        return None

    @staticmethod
    def _is_within_base(base: Path, candidate: Path) -> bool:
        base_resolved = base.resolve()
        candidate_resolved = candidate.resolve()
        return base_resolved == candidate_resolved or base_resolved in candidate_resolved.parents

    def _parse_skill_file(
        self,
        *,
        file_path: Path,
        default_name: str,
        strict: bool,
    ) -> SkillDocument:
        raw = file_path.read_text(encoding="utf-8")
        suffix = file_path.suffix.lower()
        metadata: dict[str, Any] = {}
        content = raw
        normalized_format = suffix.lstrip(".")

        if suffix in (".md", ".markdown"):
            parsed = self._parse_markdown_skill(
                raw=raw,
                strict=strict,
                source_path=file_path,
            )
            metadata = parsed["metadata"]
            content = parsed["content"]
            normalized_format = parsed["format"]
        elif suffix == ".toml":
            metadata = self._parse_toml_metadata(raw=raw, strict=strict)
            normalized_format = "toml"
        elif suffix == ".skill":
            # Keep backward compatibility for freeform legacy skill files.
            metadata = self._parse_toml_metadata(raw=raw, strict=False)
            normalized_format = "legacy-skill"
        elif suffix == ".json":
            metadata = self._parse_json_metadata(raw=raw, strict=strict)
            normalized_format = "json"
        elif suffix in (".yaml", ".yml"):
            metadata = self._parse_simple_yaml_map(raw=raw, strict=strict)
            normalized_format = "yaml"

        skill_name = str(metadata.get("name", default_name)).strip() or default_name
        description = metadata.get("description", "")
        metadata["name"] = skill_name
        metadata["description"] = str(description)

        return SkillDocument(
            name=skill_name,
            source_path=file_path,
            content=content,
            metadata=metadata,
            format=normalized_format,
        )

    def _parse_markdown_skill(
        self,
        *,
        raw: str,
        strict: bool,
        source_path: Path,
    ) -> dict[str, Any]:
        match = _FRONT_MATTER_PATTERN.match(raw)
        if match is None:
            return {"metadata": {}, "content": raw, "format": "markdown"}

        header = match.group("header") or ""
        body = match.group("body") or ""
        metadata = self._parse_simple_yaml_map(raw=header, strict=strict)
        if "description" not in metadata and strict:
            raise ValueError(
                f"Skill markdown frontmatter in '{source_path}' requires 'description'."
            )
        return {
            "metadata": metadata,
            "content": body.strip(),
            "format": "markdown-frontmatter",
        }

    @staticmethod
    def _parse_toml_metadata(*, raw: str, strict: bool) -> dict[str, Any]:
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
    def _parse_json_metadata(*, raw: str, strict: bool) -> dict[str, Any]:
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

    def _parse_simple_yaml_map(self, *, raw: str, strict: bool) -> dict[str, Any]:
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
                list_value = result.get(current_list_key)
                if not isinstance(list_value, list):
                    list_value = []
                    result[current_list_key] = list_value
                list_value.append(self._parse_scalar(value_text))
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

    @staticmethod
    def _document_payload(document: SkillDocument) -> dict[str, Any]:
        return {
            "name": document.name,
            "description": str(document.metadata.get("description", "")),
            "format": document.format,
            "path": str(document.source_path),
            "metadata": document.metadata,
        }

    def _safe_path(self, relative_path: str) -> Path:
        raw = Path(relative_path)
        target = (self.workspace / raw).resolve()
        root = self.workspace.resolve()
        if root == target or root in target.parents:
            return target
        raise ValueError("Path must stay inside workspace.")


