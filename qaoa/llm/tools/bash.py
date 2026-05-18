"""Bash tool for executing shell commands.

Parity with ClawCode -- same BashTool class, _prepare_command, _create_shell_process,
_create_shell_process_with_fallback, SAFE_COMMANDS, create_bash_tool, and run/run_stream methods.
"""

from __future__ import annotations

import asyncio
import contextlib
import locale
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ...config.settings import ShellConfig, get_settings
from ...utils.text import sanitize_text, strip_ansi_escapes
from .base import BaseTool, ToolCall, ToolContext, ToolInfo, ToolResponse
from .bash_fallback import should_attempt_python_fallback, try_python_shell_fallback
from .file_ops import resolve_tool_path
from .shell_compat import (
    ShellFamily,
    ShellLaunchSpec,
    build_shell_launch_spec,
    classify_shell_executable,
    detect_runtime,
    expand_command,
    failure_hints,
    resolve_git_bash_executable,
)


def _decode_bytes(data: bytes) -> str:
    """Decode process output bytes, preferring UTF-8.

    Modern tools (Rust/cargo, Node, Python) typically emit UTF-8 even on
    Windows where the console code page defaults to GBK/cp936.  We try
    UTF-8 first; only fall back to the system locale encoding when it fails.
    """
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        enc = locale.getpreferredencoding(False) or "utf-8"
        return data.decode(enc, errors="replace")


def _effective_bash_cwd(params: dict[str, Any], context: ToolContext) -> str | None:
    """Resolve working directory: explicit ``cwd`` param, else session workspace."""
    raw = params.get("cwd")
    if isinstance(raw, str) and raw.strip():
        resolved = resolve_tool_path(raw, context.working_directory)
        if resolved.is_dir():
            return str(resolved)
        if resolved.parent.is_dir():
            return str(resolved.parent)
        return None
    wd = (getattr(context, "working_directory", "") or "").strip()
    if not wd:
        return None
    try:
        base = Path(wd).resolve()
        if base.is_dir():
            return str(base)
    except OSError:
        pass
    return None


def _coerce_bash_timeout(raw: Any, default: float = 30.0) -> float:
    """Wall-clock limit for bash execution (``run`` / ``run_stream``)."""
    try:
        t = float(raw)
        if t <= 0:
            return default
        return t
    except (TypeError, ValueError):
        return default


async def _create_shell_process(
    launch: ShellLaunchSpec,
    cwd: str | None,
) -> asyncio.subprocess.Process:
    """Spawn a subprocess using either shell=True (cmd) or argv (PowerShell/POSIX)."""
    if launch.mode == "shell":
        return await asyncio.create_subprocess_shell(
            launch.shell_cmdline or "",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
            shell=True,
            executable=launch.shell_executable,
        )
    assert launch.argv is not None
    return await asyncio.create_subprocess_exec(
        *launch.argv,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )


def _resolve_shell_config() -> ShellConfig:
    try:
        return get_settings().shell
    except Exception:
        return ShellConfig()


def _resolve_environments_backend() -> tuple[bool, str]:
    """Whether bash should use ``create_environment`` and the backend type string."""
    sh = _resolve_shell_config()
    if not sh.use_environments_backend:
        return False, "local"
    override = os.getenv("KAGEKO_TERMINAL_ENV", "").strip()
    if override:
        return True, override.lower()
    te = (sh.terminal_env or "local").strip()
    return True, (te.lower() if te else "local")


def _bash_python_fallback_flags() -> tuple[bool, bool]:
    """Return (enabled, without_env_hint) from settings.shell."""
    sh = _resolve_shell_config()
    return (
        getattr(sh, "bash_python_fallback", True),
        getattr(sh, "bash_python_fallback_without_env_hint", False),
    )


def _strip_redundant_bash_prefix(command: str) -> str:
    """Drop leading ``bash `` when the bash tool already runs a shell.

    Models often emit ``bash date ...``; on Windows that runs ``bash.exe`` if
    present, or mis-parses under PowerShell. The intended command is usually
    ``date ...`` after platform expansion.
    """
    s = command.strip()
    low = s.lower()
    if low.startswith("bash ") and not low.startswith("bash -c"):
        return s[5:].lstrip()
    return command


@dataclass
class CommandPrepareResult:
    """Result of resolving a shell command into a subprocess launch spec."""

    original: str
    launch: ShellLaunchSpec
    family: ShellFamily
    used_git_bash: bool = False


def _prepare_command_from_config(original: str) -> CommandPrepareResult:
    """Expand and build launch spec using ``settings.shell`` only (no Git Bash)."""
    sh = _resolve_shell_config()
    shell_path = sh.path
    shell_args = list(sh.args)
    family = classify_shell_executable(shell_path)
    expanded = expand_command(original, family)
    launch = build_shell_launch_spec(expanded, shell_path, shell_args)
    return CommandPrepareResult(original, launch, family, used_git_bash=False)


def _prepare_command(
    raw_command: str,
    *,
    force_config_shell: bool = False,
) -> CommandPrepareResult:
    """Strip user input, expand for platform, build launch spec.

    On Windows, when ``prefer_git_bash_on_windows`` is set and
    ``force_config_shell`` is False, tries Git Bash first with POSIX expansion.
    """
    original = _strip_redundant_bash_prefix((raw_command or "").strip())
    sh = _resolve_shell_config()

    if (
        not force_config_shell
        and detect_runtime() == "windows"
        and getattr(sh, "prefer_git_bash_on_windows", True)
    ):
        gb = resolve_git_bash_executable()
        if gb:
            expanded = expand_command(original, "posix")
            launch = build_shell_launch_spec(expanded, gb, [])
            return CommandPrepareResult(original, launch, "posix", used_git_bash=True)

    return _prepare_command_from_config(original)


async def _create_shell_process_with_fallback(
    command_in: str,
    cwd: str | None,
    *,
    prep: CommandPrepareResult | None = None,
) -> tuple[asyncio.subprocess.Process, CommandPrepareResult]:
    """Create subprocess; on Windows, retry with configured shell if Git Bash spawn fails."""
    active = prep if prep is not None else _prepare_command(command_in)
    try:
        proc = await _create_shell_process(active.launch, cwd)
        return proc, active
    except OSError as first_err:
        if not active.used_git_bash:
            raise
        prep_fb = _prepare_command(command_in, force_config_shell=True)
        try:
            proc = await _create_shell_process(prep_fb.launch, cwd)
            return proc, prep_fb
        except OSError as second_err:
            raise OSError(
                "Git Bash and configured shell both failed to start. "
                f"Git Bash: {first_err!s}; configured shell: {second_err!s}. "
                "Install Git for Windows, set KAGEKO_GIT_BASH_PATH, or fix settings.shell."
            ) from second_err


# Safe commands that don't require permission (checked against original user text)
SAFE_COMMANDS = {
    "ls",
    "echo",
    "pwd",
    "cat",
    "head",
    "tail",
    "grep",
    "find",
    "which",
    "type",
    "cd",
    "git status",
    "git log",
    "git diff",
    "git branch",
    "git show",
    "git rev-parse",
    "git remote",
    "git config",
    "git ls-files",
    "dir",
    "where",
    "ver",
    "powershell",
    "pwsh",
}


def create_bash_tool(permissions: Any = None) -> "BashTool":
    """Create a bash tool instance.

    Args:
        permissions: Permission service

    Returns:
        BashTool instance
    """
    return BashTool(permissions=permissions)


class BashTool(BaseTool):
    """Tool for executing shell commands."""

    def __init__(self, permissions: Any = None) -> None:
        """Initialize the bash tool.

        Args:
            permissions: Permission service for command approval
        """
        self._permissions = permissions

    def info(self) -> ToolInfo:
        """Get tool information.

        Returns:
            ToolInfo describing this tool
        """
        return ToolInfo(
            name="bash",
            category="operations",
            domain="technology",
            description=(
                "Execute a shell command and get the output. "
                "Use this for running commands, checking files, git operations, etc. "
                "Commands that modify the filesystem or state require permission. "
                "On Windows, when Git for Windows is available, commands run in Git Bash with POSIX-style "
                "expansion; if bash is missing or cannot be started, the tool falls back to settings.shell "
                "(PowerShell/cmd). Set KAGEKO_GIT_BASH_PATH or disable prefer_git_bash_on_windows to "
                "control this. If a command fails, prefer built-in tools: "
                "`view` (read files), `ls` (list directory), `glob` (find paths), `grep` (search contents). "
                "On subprocess failure with typical WSL/store noise, a small whitelist of commands may be "
                "re-run in Python (see settings.shell.bash_python_fallback). "
                "When settings.shell.use_environments_backend is True, commands run via "
                "create_environment and BaseEnvironment.execute_async instead (see KAGEKO_SUPPORT_MAP environments)."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute.",
                    },
                    "cwd": {
                        "type": "string",
                        "description": (
                            "Working directory for the command. "
                            "If omitted, the session project directory is used (so `git` and paths resolve correctly)."
                        ),
                    },
                    "timeout": {
                        "type": "number",
                        "description": "Timeout in seconds (default: 30).",
                    },
                },
                "required": ["command"],
            },
            required=["command"],
        )

    def _append_hint(
        self,
        content: str,
        *,
        original: str,
        returncode: int,
        stderr: str,
        shell_family: str,
        is_error: bool,
    ) -> str:
        if not is_error:
            return content
        hint = failure_hints(
            original,
            returncode,
            stderr,
            detect_runtime(),
            shell_family,  # type: ignore[arg-type]
        )
        if hint:
            return f"{content}{hint}"
        return content

    async def run(
        self,
        call: ToolCall,
        context: ToolContext,
    ) -> ToolResponse:
        """Execute a shell command.

        Args:
            call: Tool call with command parameters
            context: Tool execution context

        Returns:
            Tool response with command output
        """
        params = call.input if isinstance(call.input, dict) else {}
        raw = params.get("command", "")
        command_in = raw if isinstance(raw, str) else ""
        prep = _prepare_command(command_in)
        original = prep.original
        timeout = _coerce_bash_timeout(params.get("timeout", 30))
        cwd = _effective_bash_cwd(params, context)

        if not original:
            return ToolResponse(
                content="Error: No command provided",
                is_error=True,
            )

        requires_permission = not self._is_safe_command(original)

        if requires_permission and self._permissions:
            from ...core.permission import PermissionRequest

            request = PermissionRequest(
                tool_name="bash",
                description=f"Execute shell command: {original}",
                path=cwd,
                input=params,
                session_id=context.session_id,
            )

            response = await self._permissions.request(request)
            if not response.granted:
                return ToolResponse(
                    content="Permission denied for command execution",
                    is_error=True,
                )

        use_backend, backend_type = _resolve_environments_backend()
        if use_backend:
            try:
                cwd_eff = (cwd or "").strip() or (getattr(context, "working_directory", "") or "").strip()
                timeout_int = max(1, int(round(timeout)))
                from .environments.factory import create_environment

                env = create_environment(
                    backend_type,
                    cwd=cwd_eff,
                    timeout=timeout_int,
                    persistent=False,
                )
                try:
                    result = await env.execute_async(
                        original,
                        cwd=cwd_eff or "",
                        timeout=timeout_int,
                    )
                finally:
                    env.cleanup()
                output = sanitize_text(strip_ansi_escapes(str(result.get("output", ""))))
                rc = int(result.get("returncode", -1))
                if rc != 0:
                    body = output.strip() or f"Command failed with exit code {rc}"
                    return ToolResponse(content=body, is_error=True)
                return ToolResponse(content=output)
            except Exception as e:
                return ToolResponse(
                    content=f"Error executing command: {e}",
                    is_error=True,
                )

        # Execute the command (asyncio subprocess path)
        try:
            process, active_prep = await _create_shell_process_with_fallback(
                command_in, cwd, prep=prep
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )

            output = sanitize_text(strip_ansi_escapes(_decode_bytes(stdout)))
            error = sanitize_text(strip_ansi_escapes(_decode_bytes(stderr)))

            if process.returncode != 0:
                fb_on, fb_aggr = _bash_python_fallback_flags()
                ws = (getattr(context, "working_directory", "") or "").strip()
                if should_attempt_python_fallback(
                    process.returncode,
                    output,
                    error,
                    bash_python_fallback=fb_on,
                    without_env_hint=fb_aggr,
                ):
                    alt = try_python_shell_fallback(original, cwd, ws)
                    if alt is not None:
                        return ToolResponse(content=alt)

                error_msg = error if error else f"Command failed with exit code {process.returncode}"
                body = f"{output}\n{error_msg}".strip()
                body = self._append_hint(
                    body,
                    original=original,
                    returncode=process.returncode or 0,
                    stderr=error,
                    shell_family=active_prep.family,
                    is_error=True,
                )
                return ToolResponse(
                    content=body,
                    is_error=True,
                )

            return ToolResponse(content=output)

        except TimeoutError:
            # Kill the process
            try:
                process.kill()
                await process.wait()
            except Exception:
                pass

            return ToolResponse(
                content=f"Command timed out after {timeout:g} seconds",
                is_error=True,
            )

        except Exception as e:
            return ToolResponse(
                content=f"Error executing command: {e}",
                is_error=True,
            )

    async def run_stream(
        self,
        call: ToolCall,
        context: ToolContext,
    ):
        """Stream stdout/stderr while the command runs.

        Yields ToolResponse objects:
        - metadata="stream": incremental chunks
        - metadata="final": final aggregated output (and error status)
        """
        params = call.input if isinstance(call.input, dict) else {}
        raw = params.get("command", "")
        command_in = raw if isinstance(raw, str) else ""
        prep = _prepare_command(command_in)
        original = prep.original
        timeout_s = _coerce_bash_timeout(params.get("timeout", 30))
        cwd = _effective_bash_cwd(params, context)

        if not original:
            yield ToolResponse(content="Error: No command provided", is_error=True, metadata="final")
            return

        requires_permission = not self._is_safe_command(original)
        if requires_permission and self._permissions:
            from ...core.permission import PermissionRequest

            request = PermissionRequest(
                tool_name="bash",
                description=f"Execute shell command: {original}",
                path=cwd,
                input=params,
                session_id=context.session_id,
            )
            response = await self._permissions.request(request)
            if not response.granted:
                yield ToolResponse(
                    content="Permission denied for command execution",
                    is_error=True,
                    metadata="final",
                )
                return

        use_backend, backend_type = _resolve_environments_backend()
        if use_backend:
            try:
                cwd_eff = (cwd or "").strip() or (getattr(context, "working_directory", "") or "").strip()
                timeout_int = max(1, int(round(timeout_s)))
                from .environments.factory import create_environment

                loop = asyncio.get_event_loop()
                start = loop.time()
                env = create_environment(
                    backend_type,
                    cwd=cwd_eff,
                    timeout=timeout_int,
                    persistent=False,
                )
                try:
                    result = await env.execute_async(
                        original,
                        cwd=cwd_eff or "",
                        timeout=timeout_int,
                    )
                finally:
                    env.cleanup()
                elapsed = max(0.0, loop.time() - start)
                output = sanitize_text(strip_ansi_escapes(str(result.get("output", ""))))
                rc = int(result.get("returncode", -1))
                yield ToolResponse(content=output, metadata="stdout")
                yield ToolResponse(
                    content=output,
                    is_error=(rc != 0),
                    metadata=f"final:{rc}:{elapsed:.3f}",
                )
            except Exception as e:
                yield ToolResponse(
                    content=f"Error executing command: {e}",
                    is_error=True,
                    metadata="final",
                )
            return

        start = asyncio.get_event_loop().time()
        try:
            process, active_prep = await _create_shell_process_with_fallback(
                command_in, cwd, prep=prep
            )
        except OSError as e:
            yield ToolResponse(
                content=f"Error executing command: {e}",
                is_error=True,
                metadata="final",
            )
            return

        q: asyncio.Queue[tuple[str, bytes]] = asyncio.Queue()
        stdout_chunks: list[str] = []
        stderr_chunks: list[str] = []

        async def _pump(stream, tag: str):
            try:
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    await q.put((tag, line))
            except Exception:
                pass

        stdout_task = asyncio.create_task(_pump(process.stdout, "stdout"))  # type: ignore[arg-type]
        stderr_task = asyncio.create_task(_pump(process.stderr, "stderr"))  # type: ignore[arg-type]

        loop = asyncio.get_event_loop()
        try:
            # Wall-clock deadline so long-running servers (e.g. http.server) cannot
            # spin forever before ``process.wait()``; matches ``run()`` semantics.
            deadline = start + timeout_s
            timed_out = False
            while True:
                if process.returncode is not None and q.empty():
                    break
                now = loop.time()
                if now >= deadline:
                    timed_out = True
                    break
                remaining = deadline - now
                waitt = min(0.2, remaining)
                if waitt <= 0:
                    timed_out = True
                    break
                try:
                    tag, chunk = await asyncio.wait_for(q.get(), timeout=waitt)
                except TimeoutError:
                    if process.returncode is None:
                        continue
                    break

                text = sanitize_text(strip_ansi_escapes(_decode_bytes(chunk)))
                if tag == "stdout":
                    stdout_chunks.append(text)
                    yield ToolResponse(content=text, metadata="stdout")
                else:
                    stderr_chunks.append(text)
                    yield ToolResponse(content=text, metadata="stderr")

            if timed_out:
                try:
                    process.kill()
                    await asyncio.wait_for(process.wait(), timeout=5.0)
                except Exception:
                    pass
                yield ToolResponse(
                    content=f"Command timed out after {timeout_s:g} seconds",
                    is_error=True,
                    metadata="final:timeout",
                )
                return

            await asyncio.wait_for(process.wait(), timeout=max(1.0, timeout_s))
        except TimeoutError:
            try:
                process.kill()
                await process.wait()
            except Exception:
                pass
            yield ToolResponse(
                content=f"Command timed out after {timeout_s:g} seconds",
                is_error=True,
                metadata="final:timeout",
            )
            return
        finally:
            for t in (stdout_task, stderr_task):
                if not t.done():
                    t.cancel()
            with contextlib.suppress(Exception):
                await asyncio.gather(stdout_task, stderr_task, return_exceptions=True)

        elapsed = max(0.0, asyncio.get_event_loop().time() - start)
        output = "".join(stdout_chunks)
        error = "".join(stderr_chunks)
        if process.returncode != 0:
            fb_on, fb_aggr = _bash_python_fallback_flags()
            ws = (getattr(context, "working_directory", "") or "").strip()
            if should_attempt_python_fallback(
                process.returncode,
                output,
                error,
                bash_python_fallback=fb_on,
                without_env_hint=fb_aggr,
            ):
                alt = try_python_shell_fallback(original, cwd, ws)
                if alt is not None:
                    yield ToolResponse(
                        content=alt,
                        metadata=f"final:{process.returncode}:{elapsed:.3f}",
                    )
                    return

            error_msg = error if error else f"Command failed with exit code {process.returncode}"
            body = f"{output}\n{error_msg}".strip()
            body = self._append_hint(
                body,
                original=original,
                returncode=process.returncode or 0,
                stderr=error,
                shell_family=active_prep.family,
                is_error=True,
            )
            yield ToolResponse(
                content=body,
                is_error=True,
                metadata=f"final:{process.returncode}:{elapsed:.3f}",
            )
            return

        yield ToolResponse(content=output, metadata=f"final:{process.returncode}:{elapsed:.3f}")

    def _is_safe_command(self, command: str) -> bool:
        """Check if a command is safe (doesn't require permission).

        Uses the user's command text (before platform expansion).

        Args:
            command: Command string (stripped)

        Returns:
            True if command is safe
        """
        parts = command.strip().split()
        if not parts:
            return True

        cmd = parts[0]

        if cmd in SAFE_COMMANDS:
            return True

        if cmd == "git" and len(parts) > 1:
            git_cmd = f"git {parts[1]}"
            if git_cmd in SAFE_COMMANDS:
                return True

        return False
