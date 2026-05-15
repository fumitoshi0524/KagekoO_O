"""Load scripts from skill directories as temporary tools."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from ..types import SkillSpec


@dataclass(slots=True, kw_only=True)
class SkillScript:
    """A script inside a skill directory, converted to a callable tool."""
    name: str           # tool name: "<skill_name>.<script_name>"
    skill_name: str
    script_path: Path
    description: str = ""
    workspace: Path | None = None  # where to run the script

    def run(self, payload: str = "") -> str:
        if self.script_path.suffix == ".py":
            return self._run_python(payload)
        else:
            return self._run_shell(payload)

    def _unix_path(self) -> str:
        """Convert Windows path to Unix-style for bash."""
        p = str(self.script_path).replace("\\", "/")
        if p[1:3] == ":/":
            p = "/" + p[0].lower() + p[2:]
        return p

    def _get_cwd(self) -> str:
        if self.workspace:
            return str(self.workspace)
        return str(self.script_path.parent)

    def _run_python(self, payload: str) -> str:
        completed = subprocess.run(
            ["python", str(self.script_path)] + (payload.split() if payload.strip() else []),
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=self._get_cwd(),
        )
        if completed.returncode != 0:
            raise RuntimeError(f"Script failed: {completed.stderr.strip() or '<none>'}")
        return completed.stdout.strip() or "<no-output>"

    def _run_shell(self, payload: str) -> str:
        from ..tools.builtins import _SHELL_PATH, _SHELL_TYPE
        upath = self._unix_path()
        shell = _SHELL_PATH
        if shell == "wsl":
            shell = "wsl"
        elif shell == "cmd.exe":
            shell = "cmd.exe"
        cwd = self._get_cwd().replace("\\", "/")
        if shell == "wsl":
            cmd = ["wsl", "--", "bash", upath] + (payload.split() if payload.strip() else [])
        elif shell == "powershell":
            cmd = ["powershell", "-File", upath] + (payload.split() if payload.strip() else [])
        elif shell == "cmd.exe":
            cmd = [upath] + (payload.split() if payload.strip() else [])
        else:
            cmd = [shell, upath] + (payload.split() if payload.strip() else [])

        completed = subprocess.run(
            cmd,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=cwd,
        )
        if completed.returncode != 0:
            raise RuntimeError(f"Script failed (exit={completed.returncode}): {completed.stderr.strip() or '<none>'}")
        return completed.stdout.strip() or "<no-output>"


@dataclass(slots=True, kw_only=True)
class SkillScriptLoader:
    """Discovers scripts in skill directories and registers them as temporary tools."""

    registry: object = None  # ToolRegistry
    _registered: dict[str, SkillScript] = field(default_factory=dict)

    def load_scripts(self, skill: SkillSpec) -> list[SkillScript]:
        """Find all scripts in a skill directory."""
        if skill.source_path is None:
            return []
        skill_dir = skill.source_path.parent if skill.source_path.name == "SKILL.md" else skill.source_path
        scripts_dir = skill_dir / "scripts"
        if not scripts_dir.exists() or not scripts_dir.is_dir():
            return []

        scripts: list[SkillScript] = []
        for f in sorted(scripts_dir.iterdir()):
            if f.is_file() and f.suffix in (".sh", ".py", ".bash"):
                tool_name = f"{skill.name}.{f.stem}"
                scripts.append(SkillScript(
                    name=tool_name,
                    skill_name=skill.name,
                    script_path=f,
                    description=f"Script from {skill.name} skill: {f.name}",
                ))
        return scripts

    def register(self, skill: SkillSpec, workspace: str = "") -> list[str]:
        """Register skill scripts as temporary tools. Returns list of tool names."""
        if self.registry is None:
            return []
        scripts = self.load_scripts(skill)
        names: list[str] = []
        for s in scripts:
            if workspace:
                s.workspace = Path(workspace)
        was_frozen = getattr(self.registry, 'is_frozen', False)
        if was_frozen:
            self.registry.unfreeze()
        try:
            for s in scripts:
                self._registered[s.name] = s
                self.registry.register(
                    s.name,
                    s.run,
                    description=s.description,
                    input_contract="optional arguments",
                    output_contract="script output",
                    tags=("skill-script", skill.name),
                    risk_level="write",
                    category="operations",
                    domain="technology",
                )
                names.append(s.name)
        finally:
            if was_frozen:
                self.registry.freeze()
        return names

    def unregister(self, skill: SkillSpec) -> list[str]:
        """Remove temporary script tools for a skill. Returns list of removed names."""
        removed: list[str] = []
        prefix = f"{skill.name}."
        for name in list(self._registered):
            if name.startswith(prefix):
                del self._registered[name]
                if self.registry:
                    self.registry.unregister(name)
                removed.append(name)
        return removed
