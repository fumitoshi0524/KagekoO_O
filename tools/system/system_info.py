"""Auto-generated tool module."""

from __future__ import annotations

import json
import os
import platform
import sys
from datetime import datetime


def run(payload: str) -> str:
    """Return system information."""
    try:
        data = json.loads(payload)
        query = str(data.get("query", "all")).lower().strip()
    except (json.JSONDecodeError, TypeError):
        query = "all"

    info: dict[str, object] = {}

    if query in ("all", "os"):
        info["os"] = platform.system()
        info["os_version"] = platform.version()
        info["os_release"] = platform.release()
    if query in ("all", "python"):
        info["python_version"] = sys.version
        info["python_executable"] = sys.executable
    if query in ("all", "hardware"):
        info["machine"] = platform.machine()
        info["processor"] = platform.processor()
        info["cpu_count"] = os.cpu_count()
    if query in ("all", "cwd"):
        info["cwd"] = os.getcwd()
        info["home"] = os.path.expanduser("~")
    if query in ("all", "time"):
        info["time_utc"] = datetime.utcnow().isoformat() + "Z"
        info["time_local"] = datetime.now().isoformat()
        info["timezone"] = str(datetime.now().astimezone().tzinfo)
    if query in ("all", "env"):
        safe_vars = {k: v for k, v in os.environ.items() if not _is_secret(k)}
        info["env_count"] = len(safe_vars)
        info["env_keys"] = list(safe_vars.keys())[:20]

    return json.dumps(info, indent=2, ensure_ascii=False)


def _is_secret(key: str) -> bool:
    upper = key.upper()
    return any(word in upper for word in ("KEY", "TOKEN", "SECRET", "PASSWORD", "PASSWD", "AUTH", "CREDENTIAL"))


TOOL_SPEC = {
    "name": "system_info",
    "description": "Query system information including OS details, Python version, hardware specs, current working directory, time, and environment variables.",
    "category": "system",
    "domain": "technology",
    "risk_level": "read",
    "schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "What information to query: os, python, hardware, cwd, time, env, or all (default).",
                "enum": ["all", "os", "python", "hardware", "cwd", "time", "env"],
                "default": "all"
            }
        },
        "required": []
    }
}
