# src/kageko/tools/builtin/hashline_tool.py
"""Hashline edit tool -- anchor-based source editing registered as an agent tool."""

from __future__ import annotations

from typing import Any

from kageko.tools.hashline import HashlineEditor


HASHLINE_TOOL: dict[str, Any] = {
    "name": "hashline_edit",
    "description": (
        "Edit source code using anchor-based hashline edits. "
        "Each line is identified by a content hash anchor instead of a line number. "
        "Edit format: #<line>|<anchor>|<new_content>. "
        "Pass 'edit' for a single edit or 'edits' (newline-separated) for a batch."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "source": {
                "type": "string",
                "description": "The source text to edit",
            },
            "edit": {
                "type": "string",
                "description": "A single hashline edit string: #<line>|<anchor>|<new_content>",
            },
            "edits": {
                "type": "string",
                "description": "Multiple hashline edits, one per line",
            },
        },
        "required": ["source"],
    },
    "category": "code",
}


async def hashline_edit(args: dict[str, Any]) -> str:
    """Apply hashline edits to source code."""
    source = args.get("source")
    if not source:
        return "[ERROR] Missing required parameter: 'source'"
    single_edit = args.get("edit")
    batch_edits = args.get("edits")

    if not single_edit and not batch_edits:
        return "Error: provide either 'edit' or 'edits' parameter"

    try:
        editor = HashlineEditor(source)
        if single_edit:
            result = editor.apply(single_edit)
        else:
            edit_list = [e.strip() for e in batch_edits.strip().split("\n") if e.strip()]
            result = editor.apply_batch(edit_list)
        return result
    except Exception as e:
        return f"Hashline edit error: {type(e).__name__}: {e}"


from kageko.tools.registry import ToolRegistry, Tool

HASHLINE_SCHEMA = {
    "name": "hashline_edit",
    "description": "Edit source files using anchor-based hashline references. "
                   "The anchor is the first 8 chars of the content hash of the line to replace.",
    "parameters": {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the source file to edit",
            },
            "anchor": {
                "type": "string",
                "description": "First 8 characters of the SHA-256 hash of the original line content",
            },
            "new_content": {
                "type": "string",
                "description": "The new content to replace the anchored line with",
            },
        },
        "required": ["file_path", "anchor", "new_content"],
    },
}


def register(registry: ToolRegistry) -> None:
    """Register hashline_edit tool in the registry."""
    if "hashline_edit" in registry.list_names():
        return
    registry.register(Tool(
        name=HASHLINE_TOOL["name"],
        description=HASHLINE_TOOL["description"],
        parameters=HASHLINE_TOOL["parameters"],
        handler=hashline_edit,
        category=HASHLINE_TOOL.get("category", "code"),
    ))
