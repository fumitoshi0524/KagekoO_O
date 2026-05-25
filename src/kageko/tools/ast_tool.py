from __future__ import annotations

from kageko._native import summarize as _summarize


def ast_summarize(source: str, language: str = "python") -> str:
    """Parse source code and return a summary of top-level declarations."""
    nodes = _summarize(source, language)
    if not nodes:
        return "(no declarations found)"
    lines = []
    for node in nodes:
        lines.append(f"L{node.start_line}-{node.end_line} [{node.kind}] {node.text}")
    return "\n".join(lines)
