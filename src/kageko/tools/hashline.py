# src/kageko/tools/hashline.py
"""Hashline edit engine — anchor-based source editing backed by Rust."""

from __future__ import annotations

from typing import Any

from kageko._native import HashlineEditor as _HashlineEditor, SourceLine

__all__ = ["HashlineEditor", "SourceLine"]


class HashlineEditor:
    """Python wrapper around the Rust hashline edit engine.

    Each source line is identified by an 8-char hex anchor (first 8 hex digits
    of the SHA-256 hash of the trimmed content).  Edits reference anchors
    instead of line numbers, so they stay valid even when earlier lines change.

    Edit format::

        #<line>|<anchor>| <new_content>

    If *new_content* is empty the line is deleted.
    """

    def __init__(self, source: str) -> None:
        self._editor = _HashlineEditor(source)

    def apply(self, edit: str) -> str:
        """Apply a single hashline edit.  Returns the new source text."""
        return self._editor.apply(edit)

    def apply_batch(self, edits: list[str]) -> str:
        """Apply multiple edits sequentially.  Returns the new source text."""
        return self._editor.apply_batch(edits)

    @property
    def source(self) -> str:
        """Current source text."""
        return self._editor.source()

    def lines(self) -> list[SourceLine]:
        """Return the list of SourceLine objects."""
        return list(self._editor.lines())
