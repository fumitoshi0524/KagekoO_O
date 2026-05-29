"""Tests for token tracking in status line rendering."""
from __future__ import annotations

from io import StringIO

from rich.console import Console

from kageko.repl.status import render_status_line, _format_tokens


def test_format_tokens():
    assert _format_tokens(500) == "500"
    assert _format_tokens(1500) == "1.5k"
    assert _format_tokens(1_500_000) == "1.5m"


def test_render_status_line_shows_tokens():
    """render_status_line should display non-zero token count."""
    buf = StringIO()
    c = Console(file=buf, width=80, force_terminal=True)
    render_status_line(c, turn=3, tokens=4200, model="gpt-4o")
    output = buf.getvalue()
    assert "4.2k" in output
    assert "Turn" in output
    assert "3" in output
    assert "gpt-4o" in output


def test_render_status_line_with_mode():
    """render_status_line should display mode when provided."""
    buf = StringIO()
    c = Console(file=buf, width=80, force_terminal=True)
    render_status_line(c, turn=1, tokens=0, model="gpt-4o", mode="tool-use")
    output = buf.getvalue()
    assert "tool-use" in output
    assert "Mode" in output


def test_render_status_line_without_mode():
    """render_status_line should not show Mode when mode is empty."""
    buf = StringIO()
    c = Console(file=buf, width=80, force_terminal=True)
    render_status_line(c, turn=1, tokens=0, model="gpt-4o", mode="")
    with_mode = StringIO()
    c2 = Console(file=with_mode, width=80, force_terminal=True)
    render_status_line(c2, turn=1, tokens=0, model="gpt-4o", mode="tool-use")
    # Without mode should produce shorter output
    assert len(buf.getvalue()) < len(with_mode.getvalue())
    assert "tool-use" not in buf.getvalue()
