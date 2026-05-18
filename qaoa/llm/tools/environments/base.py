# QAOA category: system, domain: technology
"""Base class for Kageko execution environment backends."""

from __future__ import annotations

import asyncio
import os
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path

from .sudo import transform_sudo_command


def get_sandbox_dir() -> Path:
    """Host root for sandbox storage (Docker workspaces, overlays, etc.).

    Override with ``KAAGEKO_TERMINAL_SANDBOX_DIR``. Default: ``~/.kageko/sandboxes``.
    """
    custom = os.getenv("KAAGEKO_TERMINAL_SANDBOX_DIR")
    if custom:
        p = Path(custom)
    else:
        p = Path.home() / ".kageko" / "sandboxes"
    p.mkdir(parents=True, exist_ok=True)
    return p


class BaseEnvironment(ABC):
    """Common interface for execution backends (local, docker, ssh, ...)."""

    def __init__(self, cwd: str, timeout: int, env: dict[str, str] | None = None) -> None:
        self.cwd = cwd
        self.timeout = timeout
        self.env = env or {}

    @abstractmethod
    def execute(
        self,
        command: str,
        cwd: str = "",
        *,
        timeout: int | None = None,
        stdin_data: str | None = None,
    ) -> dict[str, str | int]:
        """Run a command; return ``{"output": str, "returncode": int}``."""
        ...

    @abstractmethod
    def cleanup(self) -> None:
        """Release backend resources."""
        ...

    def stop(self) -> None:
        self.cleanup()

    def __del__(self) -> None:
        try:
            self.cleanup()
        except Exception:
            pass

    def _prepare_command(self, command: str) -> tuple[str, str | None]:
        return transform_sudo_command(command)

    def _build_run_kwargs(
        self,
        timeout: int | None,
        stdin_data: str | None = None,
    ) -> dict[str, object]:
        kw: dict[str, object] = {
            "text": True,
            "timeout": timeout or self.timeout,
            "encoding": "utf-8",
            "errors": "replace",
            "stdout": subprocess.PIPE,
            "stderr": subprocess.STDOUT,
        }
        if stdin_data is not None:
            kw["input"] = stdin_data
        else:
            kw["stdin"] = subprocess.DEVNULL
        return kw

    def _timeout_result(self, timeout: int | None) -> dict[str, str | int]:
        return {
            "output": f"Command timed out after {timeout or self.timeout}s",
            "returncode": 124,
        }

    async def execute_async(
        self,
        command: str,
        cwd: str = "",
        *,
        timeout: int | None = None,
        stdin_data: str | None = None,
    ) -> dict[str, str | int]:
        """Async wrapper: runs :meth:`execute` in a thread pool (TUI-safe)."""
        return await asyncio.to_thread(
            self.execute,
            command,
            cwd,
            timeout=timeout,
            stdin_data=stdin_data,
        )
