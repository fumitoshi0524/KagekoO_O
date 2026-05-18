"""Async bridge to the ``claude`` / ``claude-code`` CLI (path B).

Thin wrapper over :mod:`coding_cli_bridge`. See ``KAAGEKO_SUPPORT_MAP.md``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from .coding_cli_bridge import (
    CodingCLIConfig,
    CodingCLIError,
    build_coding_cli_command_line,
    release_all_coding_cli_session_environments,
    release_coding_cli_session_environments,
    resolve_coding_cli_terminal_backend,
    resolve_coding_executable,
    run_coding_cli,
    run_coding_cli_via_host_subprocess as _run_host,
    run_coding_cli_via_terminal_environment as _run_term,
)


class ClaudeCLIError(CodingCLIError):
    """Raised when the CLI is missing, the backend is unavailable, or execution fails."""


_CLAUDE_CONFIG_WITH_ERROR: Final[CodingCLIConfig] = CodingCLIConfig(
    family="claude",
    candidates=("claude", "claude-code"),
    default_cmd_fallback="claude",
    missing_local_binary_msg="No 'claude' or 'claude-code' executable found on PATH.",
    slash_name="claude-cli",
    error_cls=ClaudeCLIError,
)


def resolve_claude_executable() -> str | None:
    """Return first ``claude`` or ``claude-code`` found on PATH, or ``None``."""
    return resolve_coding_executable(_CLAUDE_CONFIG_WITH_ERROR)


def resolve_claude_cli_terminal_backend() -> str:
    """Backend id for ``/claude-cli`` (same env vars as ``create_environment`` / bash tool)."""
    return resolve_coding_cli_terminal_backend()


def build_claude_cli_command_line(exe: str | None, args: list[str]) -> str:
    """Single shell command line: executable + args (POSIX quoting via :func:`shlex.join`)."""
    return build_coding_cli_command_line(_CLAUDE_CONFIG_WITH_ERROR, exe, args)


async def run_claude_cli_via_host_subprocess(
    exe: str,
    args: list[str],
    *,
    cwd: Path | str | None = None,
    timeout: float | None = 120.0,
) -> tuple[int, str, str]:
    """Run ``claude`` via direct asyncio subprocess (host only). For tests and narrow call sites."""
    return await _run_host(_CLAUDE_CONFIG_WITH_ERROR, exe, args, cwd=cwd, timeout=timeout)


async def run_claude_cli_via_terminal_environment(
    backend: str,
    exe: str | None,
    args: list[str],
    *,
    cwd: Path | str | None = None,
    timeout: float | None = 120.0,
    session_id: str | None = None,
) -> tuple[int, str, str]:
    """Run Claude CLI inside :func:`create_environment` (local/docker/ssh/...)."""
    return await _run_term(
        _CLAUDE_CONFIG_WITH_ERROR,
        backend,
        exe,
        args,
        cwd=cwd,
        timeout=timeout,
        session_id=session_id,
    )


async def run_claude_cli(
    args: list[str],
    *,
    cwd: Path | str | None = None,
    timeout: float | None = 120.0,
    session_id: str | None = None,
    force_host_subprocess: bool = False,
) -> tuple[int, str, str]:
    """Run ``claude`` (or ``claude-code``) with the given arguments."""
    return await run_coding_cli(
        _CLAUDE_CONFIG_WITH_ERROR,
        args,
        cwd=cwd,
        timeout=timeout,
        session_id=session_id,
        force_host_subprocess=force_host_subprocess,
    )


def release_claude_cli_session_environments(session_id: str | None) -> None:
    """Release cached terminal environments for one TUI chat session (Claude CLI only)."""
    release_coding_cli_session_environments("claude", session_id)


def release_all_claude_cli_session_environments() -> None:
    """Release every cached Claude CLI environment."""
    release_all_coding_cli_session_environments(family="claude")


__all__ = [
    "ClaudeCLIError",
    "build_claude_cli_command_line",
    "release_all_claude_cli_session_environments",
    "release_claude_cli_session_environments",
    "resolve_claude_cli_terminal_backend",
    "resolve_claude_executable",
    "run_claude_cli",
    "run_claude_cli_via_host_subprocess",
    "run_claude_cli_via_terminal_environment",
]
