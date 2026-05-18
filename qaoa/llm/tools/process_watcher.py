# QAOA category: system, domain: technology
"""Drain ``process_registry.pending_watchers`` and poll until background processes exit (Hermes-aligned).

Parity with ClawCode -- same background_process_notification_mode,
schedule_drain_pending_watchers, recover_checkpoint_and_schedule_watchers.

TUI injects an async ``notify(session_id, text)`` callback to append messages to the chat.

Notification modes (same semantics as Hermes ``display.background_process_notifications``):

- ``all`` -- periodic updates while output grows, plus a final message on exit
- ``result`` -- final completion message only (kageko default when nothing else is set)
- ``error`` -- final message only when exit code is non-zero
- ``off`` -- no chat messages (watcher still runs until the process ends)

Resolution order: ``HERMES_BACKGROUND_NOTIFICATIONS`` (override), then
``KAGEKO_BACKGROUND_PROCESS_NOTIFICATIONS``, then Settings field
``background_process_notifications`` in ``.kageko.json`` when settings are loaded, else ``result``.
"""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import Awaitable, Callable
from typing import Any

from .process_registry import process_registry

logger = logging.getLogger(__name__)

NotifyFn = Callable[[str, str], Awaitable[None]]

_VALID_MODES = frozenset({"all", "result", "error", "off"})


def _normalize_mode_str(raw: str | None) -> str | None:
    if raw is None:
        return None
    s = raw.strip().lower()
    if not s:
        return None
    if s in ("false", "0", "no"):
        return "off"
    if s in _VALID_MODES:
        return s
    logger.warning("Unknown background_process_notifications %r, ignoring", raw)
    return None


def background_process_notification_mode() -> str:
    """Return effective notification mode (``all`` | ``result`` | ``error`` | ``off``)."""
    for key in ("HERMES_BACKGROUND_NOTIFICATIONS", "KAGEKO_BACKGROUND_PROCESS_NOTIFICATIONS"):
        m = _normalize_mode_str(os.getenv(key))
        if m is not None:
            return m
    try:
        from ...config.settings import get_settings

        s = get_settings().background_process_notifications
        if s in _VALID_MODES:
            return s
    except (RuntimeError, AttributeError):
        pass
    return "result"


def schedule_drain_pending_watchers(
    notify: NotifyFn,
) -> list[asyncio.Task[None]]:
    """Pop all pending watchers and spawn one asyncio task each (non-blocking)."""
    tasks: list[asyncio.Task[None]] = []
    while True:
        with process_registry._lock:
            if not process_registry.pending_watchers:
                break
            w = process_registry.pending_watchers.pop(0)
        tasks.append(asyncio.create_task(_run_process_watcher(w, notify)))
    return tasks


async def _run_process_watcher(watcher: dict[str, Any], notify: NotifyFn) -> None:
    session_id = str(watcher.get("session_id", ""))
    interval = int(watcher.get("check_interval", 30) or 30)
    task_id = str(watcher.get("task_id") or watcher.get("session_key") or "").strip()
    mode = background_process_notification_mode()

    if not session_id:
        return

    logger.debug(
        "Process watcher started: %s every %ss mode=%s",
        session_id,
        interval,
        mode,
    )

    if mode == "off":
        while True:
            await asyncio.sleep(interval)
            s = process_registry.get(session_id)
            if s is None or s.exited:
                break
        logger.debug("Process watcher ended (silent): %s", session_id)
        return

    last_output_len = 0
    while True:
        await asyncio.sleep(interval)
        session = process_registry.get(session_id)
        if session is None:
            break

        current_output_len = len(session.output_buffer)
        has_new_output = current_output_len > last_output_len
        last_output_len = current_output_len

        if session.exited:
            should_notify = mode in ("all", "result") or (
                mode == "error" and session.exit_code not in (0, None)
            )
            if should_notify:
                tail = session.output_buffer[-1000:] if session.output_buffer else ""
                text = (
                    f"[Background process {session_id} finished "
                    f"with exit code {session.exit_code}]\n{tail}"
                )
                target = task_id or session.task_id
                if target:
                    try:
                        await notify(target, text)
                    except Exception as e:
                        logger.error("Background process notify failed: %s", e)
            break

        if has_new_output and mode == "all":
            new_output = session.output_buffer[-500:] if session.output_buffer else ""
            text = (
                f"[Background process {session_id} is still running]\n"
                f"New output:\n{new_output}"
            )
            target = task_id or session.task_id
            if target:
                try:
                    await notify(target, text)
                except Exception as e:
                    logger.error("Background process notify failed: %s", e)


async def recover_checkpoint_and_schedule_watchers(notify: NotifyFn) -> tuple[int, list[asyncio.Task[None]]]:
    """Call ``recover_from_checkpoint`` then drain any pending watchers (including re-enqueued)."""
    n = process_registry.recover_from_checkpoint()
    tasks = schedule_drain_pending_watchers(notify)
    return n, tasks
