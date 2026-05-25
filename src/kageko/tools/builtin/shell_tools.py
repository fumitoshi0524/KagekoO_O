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
