# tests/unit/test_repl_status.py
from rich.console import Console
from io import StringIO


def test_status_line_renders():
    from kageko.repl.status import render_status_line
    buf = StringIO()
    console = Console(file=buf, force_terminal=True, width=80)
    render_status_line(console, turn=3, tokens=1500, model="gpt-4o")
    output = buf.getvalue()
    assert "3" in output
    assert "1.5k" in output
    assert "gpt-4o" in output


def test_status_line_zero_turns():
    from kageko.repl.status import render_status_line
    buf = StringIO()
    console = Console(file=buf, force_terminal=True, width=80)
    render_status_line(console, turn=0, tokens=0, model="gpt-4o")
    output = buf.getvalue()
    assert "gpt-4o" in output


def test_format_tokens():
    from kageko.repl.status import _format_tokens
    assert _format_tokens(500) == "500"
    assert _format_tokens(1500) == "1.5k"
    assert _format_tokens(1_500_000) == "1.5m"
