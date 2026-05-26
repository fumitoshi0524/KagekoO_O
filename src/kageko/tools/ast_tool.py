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


AST_SUMMARIZE_TOOL = {
    "name": "ast_summarize",
    "description": "Parse source code and list top-level declarations (functions, classes, etc.)",
    "parameters": {
        "type": "object",
        "properties": {
            "source": {"type": "string", "description": "Source code to analyze"},
            "language": {"type": "string", "description": "Language: python, javascript, rust", "default": "python"},
        },
        "required": ["source"],
    },
    "category": "code",
}


async def ast_summarize_handler(args: dict) -> str:
    return ast_summarize(args["source"], args.get("language", "python"))
