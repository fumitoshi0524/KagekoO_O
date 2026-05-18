"""Async bridge to the OpenCode ``opencode`` CLI (path B').

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


class OpenCodeCLIError(CodingCLIError):
    """Raised when the OpenCode CLI is missing, the backend is unavailable, or execution fails."""


_OPENCODE_CONFIG: Final[CodingCLIConfig] = CodingCLIConfig(
    family="opencode",
    candidates=("opencode",),
    default_cmd_fallback="opencode",
    missing_local_binary_msg="No 'opencode' executable found on PATH.",
    slash_name="opencode-cli",
    error_cls=OpenCodeCLIError,
)


def resolve_opencode_executable() -> str | None:
    """Return ``opencode`` on PATH, or ``None``."""
    return resolve_coding_executable(_OPENCODE_CONFIG)


def resolve_opencode_cli_terminal_backend() -> str:
    """Backend id for ``/opencode-cli`` (same env vars as ``create_environment`` / bash tool)."""
    return resolve_coding_cli_terminal_backend()


def build_opencode_cli_command_line(exe: str | None, args: list[str]) -> str:
    """Single shell command line: executable + args (POSIX quoting via :func:`shlex.join`)."""
    return build_coding_cli_command_line(_OPENCODE_CONFIG, exe, args)


async def run_opencode_cli_via_host_subprocess(
    exe: str,
    args: list[str],
    *,
    cwd: Path | str | None = None,
    timeout: float | None = 120.0,
) -> tuple[int, str, str]:
    """Run ``opencode`` via direct asyncio subprocess (host only). For tests and narrow call sites."""
    return await _run_host(_OPENCODE_CONFIG, exe, args, cwd=cwd, timeout=timeout)


async def run_opencode_cli_via_terminal_environment(
    backend: str,
    exe: str | None,
    args: list[str],
    *,
    cwd: Path | str | None = None,
    timeout: float | None = 120.0,
    session_id: str | None = None,
) -> tuple[int, str, str]:
    """Run OpenCode CLI inside :func:`create_environment` (local/docker/ssh/...)."""
    return await _run_term(
        _OPENCODE_CONFIG,
        backend,
        exe,
        args,
        cwd=cwd,
        timeout=timeout,
        session_id=session_id,
    )


async def run_opencode_cli(
    args: list[str],
    *,
    cwd: Path | str | None = None,
    timeout: float | None = 120.0,
    session_id: str | None = None,
    force_host_subprocess: bool = False,
) -> tuple[int, str, str]:
    """Run ``opencode`` with the given arguments."""
    return await run_coding_cli(
        _OPENCODE_CONFIG,
        args,
        cwd=cwd,
        timeout=timeout,
        session_id=session_id,
        force_host_subprocess=force_host_subprocess,
    )


def release_opencode_cli_session_environments(session_id: str | None) -> None:
    """Release cached terminal environments for one TUI chat session (OpenCode CLI only)."""
    release_coding_cli_session_environments("opencode", session_id)


def release_all_opencode_cli_session_environments() -> None:
    """Release every cached OpenCode CLI environment."""
    release_all_coding_cli_session_environments(family="opencode")


__all__ = [
    "OpenCodeCLIError",
    "build_opencode_cli_command_line",
    "release_all_opencode_cli_session_environments",
    "release_opencode_cli_session_environments",
    "resolve_opencode_cli_terminal_backend",
    "resolve_opencode_executable",
    "run_opencode_cli",
    "run_opencode_cli_via_host_subprocess",
    "run_opencode_cli_via_terminal_environment",
]
