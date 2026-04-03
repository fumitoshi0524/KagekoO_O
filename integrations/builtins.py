"""Builtin tool pack and external skill loading."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess

from .tools import ToolRegistry


@dataclass(slots=True, kw_only=True)
class BuiltinToolPack:
    workspace: Path
    skills_dir: Path | None = None

    def register(self, registry: ToolRegistry) -> None:
        registry.register("echo", self._echo)
        registry.register("file.read", self._file_read)
        registry.register("file.write", self._file_write)
        registry.register("bash.run", self._bash_run)
        registry.register("todo.write", self._todo_write)
        registry.register("skill.load", self._skill_load)

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
            line = f"{line} — {details}"
        updated = existing.rstrip() + f"\n{line}\n"
        todo_file.write_text(updated, encoding="utf-8")
        return f"todo-added:{title}"

    def _skill_load(self, payload: str) -> str:
        skill_name = payload.strip()
        if skill_name == "":
            raise ValueError("skill.load requires a skill name.")
        for base in self._candidate_skill_dirs():
            candidate = base / f"{skill_name}.skill"
            if candidate.exists():
                return candidate.read_text(encoding="utf-8")
        raise FileNotFoundError(
            f"Skill '{skill_name}' not found. Expected '<skills_dir>/{skill_name}.skill'."
        )

    def _candidate_skill_dirs(self) -> list[Path]:
        dirs: list[Path] = []
        if self.skills_dir is not None:
            dirs.append(self.skills_dir)
        dirs.append(self.workspace / "skills")
        return dirs

    def _safe_path(self, relative_path: str) -> Path:
        raw = Path(relative_path)
        target = (self.workspace / raw).resolve()
        root = self.workspace.resolve()
        if root == target or root in target.parents:
            return target
        raise ValueError("Path must stay inside workspace.")
