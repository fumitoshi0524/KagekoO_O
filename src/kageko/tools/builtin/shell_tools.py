# src/kageko/tools/builtin/shell_tools.py
from __future__ import annotations

import asyncio
import locale
import sys
from typing import Any

from kageko.tools.sandbox import get_workspace_root


def _decode_output(data: bytes) -> str:
    """Decode subprocess output using the system's real encoding.

    On Windows, cmd.exe outputs in the system ANSI codepage (e.g. GBK/CP936
    on Chinese Windows, CP1252 on US Windows).  Hard-coding UTF-8 produces
    garbled output for any command that emits non-ASCII text.
    """
    encoding = locale.getpreferredencoding(False)  # e.g. 'cp936' on Chinese Windows
    try:
        return data.decode(encoding, errors="replace")
    except (UnicodeDecodeError, LookupError):
        return data.decode("utf-8", errors="replace")


async def bash_run(args: dict[str, Any]) -> str:
    command = args.get("command")
    if not command:
        return "[ERROR] Missing required parameter: 'command'"
    timeout = args.get("timeout", 180)
    proc = None
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(get_workspace_root()),
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            if proc.returncode is None:
                try:
                    proc.kill()
                except ProcessLookupError:
                    pass
                try:
                    await asyncio.wait_for(proc.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    pass
            return f"[ERROR] Command timed out or was cancelled after {timeout}s: {command}"

        output = _decode_output(stdout)
        error = _decode_output(stderr)
        if proc.returncode != 0:
            return f"[EXIT {proc.returncode}]\n{output}\n{error}".strip()
        return output.strip() or "(no output)"
    except Exception as e:
        if proc is not None and proc.returncode is None:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
        return f"[ERROR] {type(e).__name__}: {e}"


NATIVE_SHELL_TOOL = {
    "name": "native_shell",
    "description": (
        "Execute a command in a persistent shell session. "
        "Working directory and environment variables SURVIVE across calls — "
        "`cd` once and subsequent commands run there. "
        "It uses PowerShell on Windows, /bin/sh on Linux/Mac — your full "
        "system PATH is available (uv, python, cargo, git, npm, etc.). "
        "Use this when you need: cd + multi-step workflows, installing "
        "packages, running scripts, setting env vars for later commands, "
        "or any sequence where one command depends on the previous one's state. "
        "For single commands that don't need state to persist, use `bash`. "
        "NOT for: reading files (→ file_read), listing directories (→ file_list), "
        "searching code (→ grep)."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "Shell command to execute in the persistent session",
            },
        },
        "required": ["command"],
    },
    "category": "shell",
}

# Global shell instance for persistence
_shell_instance = None
_shell_lock = asyncio.Lock()


async def native_shell_handler(args: dict) -> str:
    global _shell_instance
    try:
        from kageko._native import NativeShell
    except ImportError:
        return "[ERROR] Native shell module not compiled. Run: pip install -e ."

    command = args.get("command")
    if not command:
        return "[ERROR] Missing required parameter: 'command'"

    loop = asyncio.get_running_loop()
    async with _shell_lock:
        try:
            if _shell_instance is None:
                _shell_instance = NativeShell()
            # Run the blocking Rust exec in a thread so the event loop
            # stays free to handle Ctrl+C / cancellation.
            result = await loop.run_in_executor(
                None, _shell_instance.exec, command,
            )
        except Exception as e:
            msg = str(e)
            if "os error 267" in msg or "directory" in msg.lower():
                _shell_instance = NativeShell()
                try:
                    result = await loop.run_in_executor(
                        None, _shell_instance.exec, command,
                    )
                except Exception as e2:
                    return f"[ERROR] {type(e2).__name__}: {e2}"
            else:
                return f"[ERROR] {type(e).__name__}: {e}"
    return result
