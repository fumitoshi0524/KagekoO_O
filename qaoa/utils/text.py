"""Centralized text sanitization utilities.

Provides a single ``sanitize_text`` function that removes encoding
artifacts (mojibake, Unicode replacement characters, control chars)
so that content passed to the LLM or rendered in the TUI is always
clean and readable.
"""

from __future__ import annotations

import re

_MOJIBAKE_MAP: list[tuple[str, str]] = [
    ("â", "-"),   # en-dash mojibake
    ("â", "-"),   # em-dash mojibake
    ("â", '"'),   # left double-quote mojibake
    ("â", '"'),   # right double-quote mojibake
    ("â", "'"),   # left single-quote mojibake
    ("â", "'"),   # right single-quote mojibake
    ("â¦", "..."), # ellipsis mojibake
]

_CTRL_RE = re.compile(
    # Strip C0/C1 control chars EXCEPT:
    #   \x09 = TAB, \x0a = LF, \x0d = CR  (kept by not being in range)
    #   \x1b = ESC  (handled by strip_ansi_escapes for subprocess output)
    r"[\x00-\x08\x0b\x0c\x0e-\x1a\x1c-\x1f\x7f-\x9f]",
)

# CSI / Fe escape sequences (colors, cursor, SGR mouse reporting, etc.)
_ANSI_ESCAPE_RE = re.compile(
    r"\x1B(?:"
    r"[@-Z\\\-_]"  # Fe
    r"|\[[<\d;]*[mM]"  # SGR mouse (e.g. ESC [ < 35 ; 46 ; 31 m)
    r"|\[[0-?]*[ -/]*[@-~]"  # CSI (colors, cursor, etc.)
    r")"
)


def sanitize_text(text: str) -> str:
    """Clean *text* by removing common encoding artifacts.

    The function is **idempotent** and safe to apply multiple times.

    Steps performed:
    1. Remove Unicode replacement character U+FFFD.
    2. Collapse runs of three or more ``?`` into a single space
       (legacy compatibility for already-mangled text).
    3. Fix common UTF-8-decoded-as-Latin-1 mojibake patterns.
    4. Strip invisible C0/C1 control characters (except ``\\n``, ``\\t``,
       ``\\r``).
    """
    if not text:
        return text

    # U+FFFD indicates undecodable bytes; rendering it as "?" makes the
    # UI look like mojibake. Drop it to keep output clean/readable.
    text = text.replace("ï¿½", "")
    text = re.sub(r"\?{3,}", " ", text)

    for bad, good in _MOJIBAKE_MAP:
        text = text.replace(bad, good)

    text = _CTRL_RE.sub("", text)
    return text


def strip_ansi_escapes(text: str) -> str:
    """Remove ANSI / terminal escape sequences from *text*.

    Use for **subprocess** stdout/stderr before showing in the TUI. Raw ESC
    sequences (including SGR mouse reporting) can corrupt Textual/Rich layout.
    """
    if not text:
        return text
    return _ANSI_ESCAPE_RE.sub("", text)


__all__ = ["sanitize_text", "strip_ansi_escapes"]
