"""Async bridge to the OpenAI Codex ``codex`` CLI (path B'').

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


class CodexCLIError(CodingCLIError):
    """Raised when the Codex CLI is missing, the backend is unavailable, or execution fails."""


_CODEX_CONFIG: Final[CodingCLIConfig] = CodingCLIConfig(
    family="codex",
    candidates=("codex",),
    default_cmd_fallback="codex",
    missing_local_binary_msg="No 'codex' executable found on PATH.",
    slash_name="codex-cli",
    error_cls=CodexCLIError,
)


def resolve_codex_executable() -> str | None:
    """Return ``codex`` on PATH, or ``None``."""
    return resolve_coding_executable(_CODEX_CONFIG)


def resolve_codex_cli_terminal_backend() -> str:
    """Backend id for ``/codex-cli`` (same env vars as ``create_environment`` / bash tool)."""
    return resolve_coding_cli_terminal_backend()


def build_codex_cli_command_line(exe: str | None, args: list[str]) -> str:
    """Single shell command line: executable + args (POSIX quoting via :func:`shlex.join`)."""
    return build_coding_cli_command_line(_CODEX_CONFIG, exe, args)


async def run_codex_cli_via_host_subprocess(
    exe: str,
    args: list[str],
    *,
    cwd: Path | str | None = None,
    timeout: float | None = 120.0,
) -> tuple[int, str, str]:
    """Run ``codex`` via direct asyncio subprocess (host only). For tests and narrow call sites."""
    return await _run_host(_CODEX_CONFIG, exe, args, cwd=cwd, timeout=timeout)


async def run_codex_cli_via_terminal_environment(
    backend: str,
    exe: str | None,
    args: list[str],
    *,
    cwd: Path | str | None = None,
    timeout: float | None = 120.0,
    session_id: str | None = None,
) -> tuple[int, str, str]:
    """Run Codex CLI inside :func:`create_environment` (local/docker/ssh/...)."""
    return await _run_term(
        _CODEX_CONFIG,
        backend,
        exe,
        args,
        cwd=cwd,
        timeout=timeout,
        session_id=session_id,
    )


async def run_codex_cli(
    args: list[str],
    *,
    cwd: Path | str | None = None,
    timeout: float | None = 120.0,
    session_id: str | None = None,
    force_host_subprocess: bool = False,
) -> tuple[int, str, str]:
    """Run ``codex`` with the given arguments."""
    return await run_coding_cli(
        _CODEX_CONFIG,
        args,
        cwd=cwd,
        timeout=timeout,
        session_id=session_id,
        force_host_subprocess=force_host_subprocess,
    )


def release_codex_cli_session_environments(session_id: str | None) -> None:
    """Release cached terminal environments for one TUI chat session (Codex CLI only)."""
    release_coding_cli_session_environments("codex", session_id)


def release_all_codex_cli_session_environments() -> None:
    """Release every cached Codex CLI environment."""
    release_all_coding_cli_session_environments(family="codex")


__all__ = [
    "CodexCLIError",
    "build_codex_cli_command_line",
    "release_all_codex_cli_session_environments",
    "release_codex_cli_session_environments",
    "resolve_codex_cli_terminal_backend",
    "resolve_codex_executable",
    "run_codex_cli",
    "run_codex_cli_via_host_subprocess",
    "run_codex_cli_via_terminal_environment",
]
