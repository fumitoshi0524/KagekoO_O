"""OpenAI-style ``get_tool_definitions`` bridge over Kageko :class:`~qaoa.llm.tools.base.BaseTool`.

**What this module exposes:** only the tool schemas derived from ``get_builtin_tools`` (``bash``,
``terminal``, ``process``, file/search tools, etc.). It does **not** list slash-command entry points.

**Division of labor:** the ``terminal`` and ``process`` tools implement multi-turn background shells
(including OpenCode / Codex TUI driving) via ``process_registry``. TUI slash commands such as ``/claude-cli``,
``/opencode-cli``, and ``/codex-cli`` are **separate**: they run one-shot CLI probes through ``coding_cli_bridge`` and
do **not** replace ``terminal``/``process``. PTY on POSIX is optional (``pip install 'kageko[terminal-pty]'``);
non-local backends use log polling. See ``KAAGEKO_SUPPORT_MAP.md``.
"""

from __future__ import annotations

from typing import Any


def tool_definitions_from_builtin_tools(tools: list[Any]) -> list[dict[str, Any]]:
    """Return OpenAI-style ``tools`` payloads from Kageko tool instances.

    Analogue to common ``model_tools.get_tool_definitions`` output shape:
    ``[{"type": "function", "function": {...}}]``.

    The returned schema describes **this** tool list only; it is not an exhaustive inventory of every
    way to run shell or CLI processes in the app (see module docstring).
    """
    out: list[dict[str, Any]] = []
    seen: set[int] = set()
    for t in tools:
        tid = id(t)
        if tid in seen:
            continue
        seen.add(tid)
        info = t.info()
        out.append({"type": "function", "function": info.to_dict()})
    return out
