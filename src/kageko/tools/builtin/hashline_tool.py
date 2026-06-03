"""Hashline edit tool — anchor-based source editing (omp model).

Each line read via `file_read` is annotated with an 8-char hex anchor derived from
the SHA-256 hash of the trimmed line content. The model copies these anchors from
the read output and passes them to `hashline_edit` — it NEVER computes anchors itself.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from kageko.tools.sandbox import resolve_path, SandboxViolation


# Backward-compat no-op — hashline_edit is now in BUILTIN_TOOLS directly
def register(registry) -> None:
    pass

# ---------------------------------------------------------------------------
# Anchor computation (same algorithm as the Rust engine)
# ---------------------------------------------------------------------------


def _compute_anchor(line: str) -> str:
    """Compute an 8-char hex anchor from a line's trimmed content."""
    import hashlib
    digest = hashlib.sha256(line.rstrip("\n\r").encode()).digest()
    return digest[:4].hex()


def _annotate_source(source: str) -> str:
    """Prefix each line with its anchor: ``1#abc12345|content``."""
    lines = source.split("\n")
    out: list[str] = []
    for i, line in enumerate(lines, 1):
        anchor = _compute_anchor(line)
        out.append(f"{i}#{anchor}|{line}")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def annotate_file_read(raw_content: str, file_path: str) -> str | None:
    """Annotate file content with hashline anchors.

    Returns the annotated string, or None if the file is too large / binary.
    """
    # Skip binary / huge files (> 500 KB or 5000 lines)
    if len(raw_content) > 512_000:
        return None
    if raw_content.count("\n") > 5000:
        return None
    # Skip files with null bytes (likely binary)
    if "\0" in raw_content:
        return None
    return _annotate_source(raw_content)


def apply_anchor_edit(file_path: str, anchor: str, new_content: str) -> str:
    """Read a file, find the line matching *anchor*, replace it with *new_content*.

    Returns a status message for the model.
    """
    path = resolve_path(file_path, must_exist=True)
    source = path.read_text(encoding="utf-8")
    lines = source.split("\n")

    # Build anchor→index map
    anchor_map: dict[str, int] = {}
    for i, line in enumerate(lines):
        a = _compute_anchor(line)
        anchor_map[a] = i

    if anchor not in anchor_map:
        # Staleness — the file changed since the model last read it.
        # List current anchors so the model can retry.
        current = _annotate_source(source)
        return (
            f"[STALE] Anchor '{anchor}' not found in {file_path}. "
            f"The file has changed since you last read it.\n"
            f"Re-read the file, then use the correct anchor from the fresh output.\n\n"
            f"Current state (first 2000 chars):\n{current[:2000]}"
        )

    idx = anchor_map[anchor]
    lines[idx] = new_content

    new_source = "\n".join(lines)
    path.write_text(new_source, encoding="utf-8")
    new_anchor = _compute_anchor(new_content)

    return (
        f"Replaced line {idx + 1} in {file_path}\n"
        f"  Old anchor: {anchor}\n"
        f"  New anchor: {new_anchor}\n"
        f"  New content: {new_content[:120]}"
    )


# ---------------------------------------------------------------------------
# Agent tool definition
# ---------------------------------------------------------------------------


HASHLINE_TOOL: dict[str, Any] = {
    "name": "hashline_edit",
    "description": (
        "Edit an existing file by referencing a line anchor. "
        "Anchors appear in `file_read` output as `N#XXXXXXXX|line content`. "
        "Copy the anchor you want to replace, then call this tool.\n\n"
        "Use this as the PRIMARY way to edit existing files. It is safer and "
        "more reliable than `file_write` because it targets a single line. "
        "Use `file_write` ONLY for creating brand-new files."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the file to edit",
            },
            "anchor": {
                "type": "string",
                "description": (
                    "The 8-char hex anchor from the file_read output "
                    "(the part after '#' and before '|', e.g. 'abc12345' in '1#abc12345|code')"
                ),
            },
            "new_content": {
                "type": "string",
                "description": "The replacement line content (NOT including the anchor prefix)",
            },
        },
        "required": ["file_path", "anchor", "new_content"],
    },
    "category": "code",
}


async def hashline_edit(args: dict[str, Any]) -> str:
    """Apply a single hashline anchor-based edit."""
    file_path = args.get("file_path")
    anchor = args.get("anchor")
    new_content = args.get("new_content")

    if not file_path:
        return "[ERROR] Missing required parameter: 'file_path'"
    if not anchor:
        return "[ERROR] Missing required parameter: 'anchor'"
    if new_content is None:
        return "[ERROR] Missing required parameter: 'new_content'"

    try:
        return apply_anchor_edit(file_path, anchor, new_content)
    except SandboxViolation as e:
        return f"[SANDBOX] {e}"
    except FileNotFoundError:
        return f"[ERROR] File not found: {file_path}"
    except Exception as e:
        return f"[ERROR] {type(e).__name__}: {e}"
