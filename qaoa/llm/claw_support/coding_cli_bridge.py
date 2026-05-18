"""Shared async bridge for external coding CLIs (path B): ``claude``, ``opencode``, ``codex``, etc.

Uses the same terminal backend stack as the bash tool when
``KAAGEKO_TERMINAL_ENV`` / ``TERMINAL_ENV`` selects a backend. See
``KAAGEKO_SUPPORT_MAP.md``.
"""

from __future__ import annotations

import asyncio
import os
import shlex
import shutil
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from qaoa.llm.tools.environments.base import BaseEnvironment
from qaoa.llm.tools.environments.env_vars import merge_run_env
from qaoa.llm.tools.environments.factory import create_environment

# Backends that are placeholders in Kageko (no real execution stack yet).
_UNIMPLEMENTED_CLI_BACKENDS: Final[frozenset[str]] = frozenset(
    {"modal", "daytona", "singularity", "apptainer"},
)

_CLI_ENV_LOCK: Final[threading.Lock] = threading.Lock()
# family -> (session_id, backend, normalized_cwd) -> environment
_CLI_ENV_REGISTRIES: dict[str, dict[tuple[str, str, str], BaseEnvironment]] = {
    "claude": {},
    "opencode": {},
    "codex": {},
}


class CodingCLIError(RuntimeError):
    """Raised when the CLI is missing, the backend is unavailable, or execution fails."""


@dataclass(frozen=True, slots=True)
class CodingCLIConfig:
    """Per-CLI branding for shared bridge logic."""

    family: str
    candidates: tuple[str, ...]
    default_cmd_fallback: str
    missing_local_binary_msg: str
    slash_name: str  # e.g. "claude-cli" for error strings
    error_cls: type[CodingCLIError] = CodingCLIError


def resolve_coding_cli_terminal_backend() -> str:
    """Backend id (same env vars as ``create_environment`` / bash tool)."""
    v = os.getenv("KAAGEKO_TERMINAL_ENV", "").strip()
    if v:
        return v.lower()
    v = os.getenv("TERMINAL_ENV", "").strip()
    if v:
        return v.lower()
    return "local"


def resolve_coding_executable(config: CodingCLIConfig) -> str | None:
    """Return first candidate found on PATH, or ``None``."""
    for name in config.candidates:
        path = shutil.which(name)
        if path:
            return path
    return None


def build_coding_cli_command_line(config: CodingCLIConfig, exe: str | None, args: list[str]) -> str:
    prog = exe if exe else config.default_cmd_fallback
    return shlex.join([prog] + list(args))


def _cache_key(session_id: str, backend: str, work: str) -> tuple[str, str, str]:
    return (session_id.strip(), backend.lower(), os.path.abspath(work))


def _timeout_seconds(timeout: float | None) -> int:
    if timeout is None:
        return 86_400
    return max(1, int(round(timeout)))


async def run_coding_cli_via_host_subprocess(
    config: CodingCLIConfig,
    exe: str,
    args: list[str],
    *,
    cwd: Path | str | None = None,
    timeout: float | None = 120.0,
) -> tuple[int, str, str]:
    """Direct asyncio subprocess on host only (tests / narrow call sites)."""
    work = Path(cwd) if cwd is not None else None
    try:
        proc = await asyncio.create_subprocess_exec(
            exe,
            *args,
            cwd=str(work) if work is not None else None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=merge_run_env(None, {}),
        )
    except OSError as e:
        raise config.error_cls(f"Failed to spawn CLI: {e}") from e

    try:
        if timeout is not None:
            out_b, err_b = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        else:
            out_b, err_b = await proc.communicate()
    except TimeoutError as e:
        proc.kill()
        await proc.wait()
        raise config.error_cls(
            f"CLI timed out after {timeout}s (args={args!r})"
        ) from e

    code = proc.returncode if proc.returncode is not None else -1
    out = (out_b or b"").decode(errors="replace")
    err = (err_b or b"").decode(errors="replace")
    return code, out, err


def release_coding_cli_session_environments(family: str, session_id: str | None) -> None:
    """Release cached terminal environments for one TUI chat session and one CLI family."""
    sid = (session_id or "").strip()
    if not sid:
        return
    reg = _CLI_ENV_REGISTRIES.get(family)
    if not reg:
        return
    with _CLI_ENV_LOCK:
        keys = [k for k in reg if k[0] == sid]
        for key in keys:
            env = reg.pop(key, None)
            if env is not None:
                try:
                    env.cleanup()
                except Exception:
                    pass


def release_all_coding_cli_session_environments(*, family: str | None = None) -> None:
    """Release cached environments. ``family`` None clears every registered CLI family."""
    with _CLI_ENV_LOCK:
        entries: list[BaseEnvironment] = []
        if family is None:
            for _fam, reg in list(_CLI_ENV_REGISTRIES.items()):
                for _, env in list(reg.items()):
                    entries.append(env)
                reg.clear()
        else:
            reg = _CLI_ENV_REGISTRIES.get(family)
            if reg:
                for _, env in list(reg.items()):
                    entries.append(env)
                reg.clear()
    for env in entries:
        try:
            env.cleanup()
        except Exception:
            pass


def release_all_external_cli_for_session(session_id: str | None) -> None:
    """Release claude + opencode + codex cached envs for one chat session (TUI switch/delete)."""
    for fam in ("claude", "opencode", "codex"):
        release_coding_cli_session_environments(fam, session_id)


async def run_coding_cli_via_terminal_environment(
    config: CodingCLIConfig,
    backend: str,
    exe: str | None,
    args: list[str],
    *,
    cwd: Path | str | None = None,
    timeout: float | None = 120.0,
    session_id: str | None = None,
) -> tuple[int, str, str]:
    """Run CLI inside :func:`create_environment` (local/docker/ssh/...)."""
    work = os.path.abspath(str(Path(cwd).resolve()) if cwd else os.getcwd())
    timeout_int = _timeout_seconds(timeout)
    merged = merge_run_env(None, {})
    cmd = build_coding_cli_command_line(config, exe, args)
    reg = _CLI_ENV_REGISTRIES.setdefault(config.family, {})

    sid = (session_id or "").strip()
    reuse = bool(sid)
    env: BaseEnvironment | None = None
    created_for_this_call = False

    cache_key: tuple[str, str, str] | None = None
    if reuse:
        cache_key = _cache_key(sid, backend, work)
        with _CLI_ENV_LOCK:
            env = reg.get(cache_key)
            if env is None:
                try:
                    env = create_environment(
                        backend,
                        cwd=work,
                        timeout=timeout_int,
                        env=merged,
                        persistent=False,
                    )
                except ValueError as e:
                    raise config.error_cls(str(e)) from e
                except RuntimeError as e:
                    raise config.error_cls(str(e)) from e
                reg[cache_key] = env
                created_for_this_call = True
    else:
        try:
            env = create_environment(
                backend,
                cwd=work,
                timeout=timeout_int,
                env=merged,
                persistent=False,
            )
        except ValueError as e:
            raise config.error_cls(str(e)) from e
        except RuntimeError as e:
            raise config.error_cls(str(e)) from e

    assert env is not None

    try:
        result = await env.execute_async(cmd, cwd=work, timeout=timeout_int)
    except RuntimeError as e:
        if reuse and created_for_this_call and cache_key is not None:
            with _CLI_ENV_LOCK:
                reg.pop(cache_key, None)
            try:
                env.cleanup()
            except Exception:
                pass
        raise config.error_cls(str(e)) from e
    finally:
        if not reuse:
            try:
                env.cleanup()
            except Exception:
                pass

    rc = int(result.get("returncode", -1))
    out = str(result.get("output", "") or "")
    return rc, out, ""


async def run_coding_cli(
    config: CodingCLIConfig,
    args: list[str],
    *,
    cwd: Path | str | None = None,
    timeout: float | None = 120.0,
    session_id: str | None = None,
    force_host_subprocess: bool = False,
) -> tuple[int, str, str]:
    """Run a configured external coding CLI with arguments."""
    backend = resolve_coding_cli_terminal_backend()

    if backend in _UNIMPLEMENTED_CLI_BACKENDS:
        raise config.error_cls(
            f"Terminal backend {backend!r} is not implemented for /{config.slash_name} in kageko. "
            "Set KAAGEKO_TERMINAL_ENV to local, docker, or ssh, or see KAAGEKO_SUPPORT_MAP.md."
        )

    if force_host_subprocess:
        exe = resolve_coding_executable(config)
        if not exe:
            raise config.error_cls(config.missing_local_binary_msg)
        return await run_coding_cli_via_host_subprocess(
            config, exe, args, cwd=cwd, timeout=timeout
        )

    exe = resolve_coding_executable(config)
    if backend == "local" and not exe:
        raise config.error_cls(config.missing_local_binary_msg)

    return await run_coding_cli_via_terminal_environment(
        config,
        backend,
        exe,
        args,
        cwd=cwd,
        timeout=timeout,
        session_id=session_id,
    )


__all__ = [
    "CodingCLIConfig",
    "CodingCLIError",
    "build_coding_cli_command_line",
    "release_all_coding_cli_session_environments",
    "release_all_external_cli_for_session",
    "release_coding_cli_session_environments",
    "resolve_coding_cli_terminal_backend",
    "resolve_coding_executable",
    "run_coding_cli",
    "run_coding_cli_via_host_subprocess",
    "run_coding_cli_via_terminal_environment",
]
