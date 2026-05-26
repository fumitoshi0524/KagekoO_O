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
    source = args["source"]
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
