# QAOA category: system, domain: technology
"""Pluggable interrupt check for persistent shell polling."""

from __future__ import annotations

from collections.abc import Callable

_check: Callable[[], bool] | None = None


def set_interrupt_check(fn: Callable[[], bool] | None) -> None:
    """Register a callable returning True when the current command should abort.

    Used by :class:`PersistentShellMixin` during the status-file poll loop.
    Defaults to never interrupted until TUI or tools wire this hook.
    """
    global _check
    _check = fn


def is_interrupted() -> bool:
    """Return True if the active run should be cancelled (e.g. user sent a new message)."""
    if _check is None:
        return False
    try:
        return bool(_check())
    except Exception:
        return False
