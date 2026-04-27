"""Workspace context loader for agent prompts."""

from __future__ import annotations

import subprocess
from pathlib import Path


class ContextManager:
    """Loads workspace context to enrich agent queries."""

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace

    def load(self) -> str:
        parts: list[str] = []
        agents_md = self._load_agents_md()
        if agents_md:
            parts.append("# Workspace Instructions\n" + agents_md)
        git_status = self._load_git_status()
        if git_status:
            parts.append("# Git Status\n" + git_status)
        return "\n\n".join(parts)

    def _load_agents_md(self) -> str | None:
        for name in ("AGENTS.md", "AGENT.md", "agents.md", "agent.md"):
            path = self.workspace / name
            if path.exists() and path.is_file():
                try:
                    return path.read_text(encoding="utf-8").strip()
                except OSError:
                    continue
        return None

    def _load_git_status(self) -> str | None:
        try:
            result = subprocess.run(
                ["git", "status", "--short"],
                cwd=str(self.workspace),
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except FileNotFoundError:
            pass
        return None
