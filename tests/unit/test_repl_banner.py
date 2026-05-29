# tests/unit/test_repl_banner.py
from rich.console import Console
from io import StringIO


def test_welcome_banner_renders():
    from kageko.repl.banner import render_welcome
    buf = StringIO()
    console = Console(file=buf, force_terminal=True, width=80)
    render_welcome(console, model="gpt-4o", provider="openai", version="0.4.0")
    output = buf.getvalue()
    assert "O_O" in output
    assert "gpt-4o" in output
    assert "openai" in output


def test_welcome_banner_narrow_terminal():
    from kageko.repl.banner import render_welcome
    buf = StringIO()
    console = Console(file=buf, force_terminal=True, width=40)
    render_welcome(console, model="gpt-4o", provider="openai", version="0.4.0")
    output = buf.getvalue()
    assert "gpt-4o" in output
    # Should not crash on narrow terminals


def test_welcome_banner_with_tips():
    from kageko.repl.banner import render_welcome
    buf = StringIO()
    console = Console(file=buf, force_terminal=True, width=80)
    render_welcome(console, model="gpt-4o", provider="openai", version="0.4.0")
    output = buf.getvalue()
    # Tips section should be present
    assert "help" in output.lower() or "/" in output
