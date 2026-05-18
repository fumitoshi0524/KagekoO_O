# QAOA category: operations, domain: technology
"""Desktop (OS-level) automation helpers for Computer Use style tooling.

Requires optional dependencies: ``mss``, ``pyautogui`` (see ``[project.optional-dependencies]`` desktop).

These tools operate on the **host OS desktop** (all applications). They are distinct from
``browser_*`` tools, which only control the automated browser session.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any

from ....config.settings import get_settings

logger = logging.getLogger(__name__)

_last_desktop_screenshot_cleanup: float = 0.0

_pyautogui_configured = False

DESKTOP_TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "desktop_screenshot",
        "description": (
            "Capture a PNG screenshot of the desktop (primary monitor or a rectangular region). "
            "Use for OS-level tasks outside a single browser. For web pages inside the automated "
            "browser session, prefer browser_snapshot or browser_vision. "
            "Returns JSON with screenshot_path; you can reference the image in a follow-up using "
            "MEDIA:<screenshot_path> when the vision model must see the pixels. "
            "Requires desktop tools to be enabled in settings and optional deps installed."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "left": {
                    "type": "integer",
                    "description": "Left edge in screen coordinates (default 0).",
                    "default": 0,
                },
                "top": {
                    "type": "integer",
                    "description": "Top edge in screen coordinates (default 0).",
                    "default": 0,
                },
                "width": {
                    "type": "integer",
                    "description": "Region width. Omit with height to capture the full primary monitor.",
                },
                "height": {
                    "type": "integer",
                    "description": "Region height. Omit with width to capture the full primary monitor.",
                },
                "monitor_index": {
                    "type": "integer",
                    "description": "mss monitor index: 0=all displays union, 1=primary (default). See DesktopConfig.monitor_index.",
                    "default": 1,
                },
            },
            "required": [],
        },
    },
    {
        "name": "desktop_move",
        "description": (
            "Move the mouse cursor to absolute screen coordinates without clicking. "
            "Use to verify coordinates before desktop_click."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "Screen X coordinate."},
                "y": {"type": "integer", "description": "Screen Y coordinate."},
                "duration": {
                    "type": "number",
                    "description": "Optional seconds to animate the move (0 = instant).",
                    "default": 0.0,
                },
            },
            "required": ["x", "y"],
        },
    },
    {
        "name": "desktop_click",
        "description": (
            "Click the mouse at absolute screen coordinates (x, y). "
            "Dangerous: can interact with any visible window. "
            "Use browser_click for elements inside the automated browser."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "Screen X coordinate."},
                "y": {"type": "integer", "description": "Screen Y coordinate."},
                "button": {
                    "type": "string",
                    "enum": ["left", "right", "middle"],
                    "description": "Mouse button (default left).",
                    "default": "left",
                },
                "clicks": {
                    "type": "integer",
                    "description": "Number of clicks (default 1).",
                    "default": 1,
                },
            },
            "required": ["x", "y"],
        },
    },
    {
        "name": "desktop_type",
        "description": (
            "Type text using the keyboard at the current focus. "
            "ASCII/Latin text works best; pyautogui has limited Unicode support. "
            "For browser inputs, browser_type is usually safer."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to type."},
                "interval": {
                    "type": "number",
                    "description": "Optional delay between keystrokes in seconds (default 0).",
                    "default": 0.0,
                },
            },
            "required": ["text"],
        },
    },
    {
        "name": "desktop_key",
        "description": (
            "Press a key or key combination. Single key: e.g. 'enter', 'esc', 'tab'. "
            "Combination: comma-separated names, e.g. 'ctrl,c' or 'ctrl,shift,t' (pyautogui names)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "keys": {
                    "type": "string",
                    "description": "One key name or comma-separated combo (e.g. 'ctrl,c').",
                }
            },
            "required": ["keys"],
        },
    },
]


def check_desktop_requirements(for_kageko_mode: bool | None = None) -> bool:
    """Return True if desktop tools are allowed and optional deps import successfully.

    Args:
        for_kageko_mode: When ``desktop.tools_require_kageko_mode`` is True, pass ``False`` to
            exclude desktop tools (e.g. TUI default coder path). ``None`` skips this check (CLI).
    """
    ok, _ = check_desktop_requirements_detail(for_kageko_mode=for_kageko_mode)
    return ok


def check_desktop_requirements_detail(for_kageko_mode: bool | None = None) -> tuple[bool, str | None]:
    """Return ``(ok, reason)`` for diagnostics (doctor, logs). ``reason`` is None on full success."""
    try:
        st = get_settings()
    except Exception as e:
        return False, f"settings unavailable: {e}"
    if not st.desktop.enabled:
        return False, "desktop.enabled is false (set in .kageko.json or KAAGEKO_DESKTOP__ENABLED)"
    if getattr(st.desktop, "tools_require_kageko_mode", False) and for_kageko_mode is False:
        return False, "desktop.tools_require_kageko_mode is true but session is not Kageko mode"
    try:
        import mss  # noqa: F401
        import pyautogui  # noqa: F401
    except ImportError as e:
        return False, f"missing optional deps (pip install kageko[desktop]): {e}"
    warn: list[str] = []
    if sys.platform.startswith("linux") and not (
        os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
    ):
        warn.append("no DISPLAY/WAYLAND_DISPLAY — Linux GUI capture may fail")
    return True, ("; ".join(warn) if warn else None)


def _screenshots_dir() -> Path:
    """Resolved under the configured data directory (respects cwd / absolute paths)."""
    st = get_settings()
    base = st.ensure_data_directory() / "desktop_screenshots"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _cleanup_old_desktop_screenshots(screenshots_dir: Path, *, max_age_hours: float = 24.0) -> None:
    """Remove PNGs older than max_age_hours to cap disk use."""
    global _last_desktop_screenshot_cleanup
    now = time.time()
    if now - _last_desktop_screenshot_cleanup < 3600:
        return
    _last_desktop_screenshot_cleanup = now
    try:
        for f in screenshots_dir.glob("desktop_*.png"):
            try:
                if now - f.stat().st_mtime > max_age_hours * 3600:
                    f.unlink(missing_ok=True)
            except OSError as e:
                logger.debug("desktop screenshot prune skipped %s: %s", f, e)
    except OSError as e:
        logger.debug("desktop screenshot cleanup: %s", e)


def _configure_pyautogui() -> None:
    """Tune pyautogui once per process (LLMs may emit many small actions)."""
    global _pyautogui_configured
    if _pyautogui_configured:
        return
    import pyautogui

    pause = os.environ.get("KAAGEKO_DESKTOP_PYAUTOGUI_PAUSE", "").strip()
    try:
        pyautogui.PAUSE = float(pause) if pause else 0.05
    except ValueError:
        pyautogui.PAUSE = 0.05
    pyautogui.FAILSAFE = True
    _pyautogui_configured = True


def _clamp_dim(n: int, max_v: int) -> int:
    return max(1, min(n, max_v))


def _clip_region_to_monitor(
    mon: dict[str, int],
    left: int,
    top: int,
    width: int | None,
    height: int | None,
    max_w: int,
    max_h: int,
) -> dict[str, int] | None:
    """Intersect requested rect with ``mon``; return None if empty."""
    ml, mt, mw, mh = mon["left"], mon["top"], mon["width"], mon["height"]
    if width is None and height is None:
        return dict(mon)
    rw = _clamp_dim(width or mw, max_w)
    rh = _clamp_dim(height or mh, max_h)
    r_left = max(int(left), ml)
    r_top = max(int(top), mt)
    r_right = min(int(left) + rw, ml + mw)
    r_bottom = min(int(top) + rh, mt + mh)
    iw = r_right - r_left
    ih = r_bottom - r_top
    if iw < 1 or ih < 1:
        return None
    return {
        "left": r_left,
        "top": r_top,
        "width": min(iw, max_w),
        "height": min(ih, max_h),
    }


def desktop_screenshot(
    left: int = 0,
    top: int = 0,
    width: int | None = None,
    height: int | None = None,
    monitor_index: int | None = None,
) -> str:
    """Capture a PNG; return JSON string with path and dimensions."""
    import mss
    from mss.tools import to_png

    st = get_settings()
    max_w = st.desktop.max_screenshot_width
    max_h = st.desktop.max_screenshot_height
    mid = int(monitor_index) if monitor_index is not None else int(st.desktop.monitor_index)

    screenshots = _screenshots_dir()
    _cleanup_old_desktop_screenshots(screenshots)

    try:
        with mss.mss() as sct:
            if mid < 0 or mid >= len(sct.monitors):
                return json.dumps(
                    {
                        "ok": False,
                        "error": f"invalid monitor_index {mid} (valid 0..{len(sct.monitors) - 1})",
                    },
                    ensure_ascii=False,
                )
            mon = sct.monitors[mid]
            region = _clip_region_to_monitor(mon, left, top, width, height, max_w, max_h)
            if region is None:
                return json.dumps(
                    {
                        "ok": False,
                        "error": "region does not intersect the selected monitor (check left/top/width/height)",
                    },
                    ensure_ascii=False,
                )

            shot = sct.grab(region)
            out = screenshots / f"desktop_{uuid.uuid4().hex}.png"
            to_png(shot.rgb, shot.size, output=str(out))

        payload = {
            "ok": True,
            "screenshot_path": str(out.resolve()),
            "width": shot.width,
            "height": shot.height,
            "monitor_index": mid,
            "note": "Reference the image with MEDIA:<screenshot_path> in a follow-up if vision is needed.",
        }
        return json.dumps(payload, ensure_ascii=False)
    except Exception as e:
        logger.warning("desktop_screenshot failed: %s", e)
        return json.dumps(
            {
                "ok": False,
                "error": str(e),
                "hint": (
                    "Ensure a display is available (headless servers may need a virtual framebuffer)."
                ),
            },
            ensure_ascii=False,
        )


def desktop_move(x: int, y: int, duration: float = 0.0) -> str:
    """Move cursor without clicking."""
    import pyautogui

    _configure_pyautogui()
    try:
        pyautogui.moveTo(int(x), int(y), duration=float(duration))
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)
    return json.dumps({"ok": True, "x": int(x), "y": int(y)}, ensure_ascii=False)


def desktop_click(
    x: int,
    y: int,
    button: str = "left",
    clicks: int = 1,
) -> str:
    """Click at screen coordinates."""
    import pyautogui

    _configure_pyautogui()
    n = max(1, int(clicks))
    failsafe_cls = getattr(pyautogui, "FailSafeException", None)
    try:
        pyautogui.click(x=int(x), y=int(y), clicks=n, button=str(button))
    except Exception as e:
        if failsafe_cls is not None and isinstance(e, failsafe_cls):
            return json.dumps(
                {
                    "ok": False,
                    "error": "pyautogui failsafe triggered (mouse moved to a screen corner)",
                },
                ensure_ascii=False,
            )
        return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)
    return json.dumps(
        {"ok": True, "x": int(x), "y": int(y), "button": button, "clicks": n},
        ensure_ascii=False,
    )


def desktop_type(text: str, interval: float = 0.0) -> str:
    """Type text at current focus (ASCII via pyautogui.write; Unicode via clipboard paste)."""
    import pyautogui

    _configure_pyautogui()
    try:
        if text.isascii():
            pyautogui.write(text, interval=float(interval))
        else:
            try:
                import pyperclip

                pyperclip.copy(text)
                if sys.platform == "darwin":
                    pyautogui.hotkey("command", "v")
                else:
                    pyautogui.hotkey("ctrl", "v")
            except Exception:
                pyautogui.write(text, interval=float(interval))
    except Exception as e:
        return json.dumps(
            {
                "ok": False,
                "error": str(e),
                "hint": "For Unicode, pyperclip + paste is used; ensure clipboard access.",
            },
            ensure_ascii=False,
        )
    return json.dumps({"ok": True, "typed_chars": len(text)}, ensure_ascii=False)


def desktop_key(keys: str) -> str:
    """Press one key or a combination (comma-separated)."""
    import pyautogui

    _configure_pyautogui()
    raw = (keys or "").strip()
    if not raw:
        return json.dumps({"ok": False, "error": "empty keys"}, ensure_ascii=False)

    st = get_settings()
    norm = raw.lower().replace(" ", "")
    for block in getattr(st.desktop, "blocked_hotkey_substrings", None) or []:
        b = block.lower().replace(" ", "")
        if b and b in norm:
            return json.dumps(
                {"ok": False, "error": f"hotkey blocked by policy: {block!r}"},
                ensure_ascii=False,
            )

    parts = [p.strip() for p in raw.replace("+", ",").split(",") if p.strip()]
    try:
        if len(parts) > 1:
            pyautogui.hotkey(*parts)
        else:
            pyautogui.press(parts[0])
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)
    return json.dumps({"ok": True, "keys": raw}, ensure_ascii=False)


__all__ = [
    "DESKTOP_TOOL_SCHEMAS",
    "check_desktop_requirements",
    "check_desktop_requirements_detail",
    "desktop_click",
    "desktop_key",
    "desktop_move",
    "desktop_screenshot",
    "desktop_type",
]
