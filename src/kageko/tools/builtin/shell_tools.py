# src/kageko/tools/builtin/shell_tools.py
from __future__ import annotations

import asyncio
from typing import Any


async def bash_run(args: dict[str, Any]) -> str:
    command = args["command"]
    timeout = args.get("timeout", 30)
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return f"[ERROR] Command timed out after {timeout}s: {command}"

        output = stdout.decode("utf-8", errors="replace")
        error = stderr.decode("utf-8", errors="replace")
        if proc.returncode != 0:
            return f"[EXIT {proc.returncode}]\n{output}\n{error}".strip()
        return output.strip() or "(no output)"
    except Exception as e:
        return f"[ERROR] {type(e).__name__}: {e}"


NATIVE_SHELL_TOOL = {
    "name": "native_shell",
    "description": "Execute commands in a persistent in-process shell session. Environment and working directory persist across calls.",
    "parameters": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "Shell command to execute",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (default: 30)",
                "default": 30,
            },
        },
        "required": ["command"],
    },
    "category": "shell",
}

# Global shell instance for persistence
_shell_instance = None


async def native_shell_handler(args: dict) -> str:
    global _shell_instance
    try:
        from kageko._native import NativeShell
    except ImportError:
        return "[ERROR] Native shell module not compiled. Run: pip install -e ."

    if _shell_instance is None:
        _shell_instance = NativeShell()

    command = args["command"]
    try:
        result = _shell_instance.exec(command)
        return result
    except Exception as e:
        return f"[ERROR] {type(e).__name__}: {e}"
