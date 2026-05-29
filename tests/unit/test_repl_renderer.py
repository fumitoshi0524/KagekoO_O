# tests/unit/test_repl_renderer.py
from rich.console import Console
from io import StringIO


def test_render_markdown_basic():
    from kageko.repl.renderer import render_markdown
    buf = StringIO()
    console = Console(file=buf, force_terminal=True, width=80)
    render_markdown(console, "# Hello\n\nSome **bold** text.")
    output = buf.getvalue()
    assert "Hello" in output
    assert "bold" in output


def test_render_markdown_code_block():
    from kageko.repl.renderer import render_markdown
    buf = StringIO()
    console = Console(file=buf, force_terminal=True, width=80)
    render_markdown(console, '```python\nprint("hi")\n```')
    output = buf.getvalue()
    assert "print" in output


def test_render_markdown_empty():
    from kageko.repl.renderer import render_markdown
    buf = StringIO()
    console = Console(file=buf, force_terminal=True, width=80)
    render_markdown(console, "")
    # Should not crash


def test_render_markdown_no_crash_on_none():
    from kageko.repl.renderer import render_markdown
    buf = StringIO()
    console = Console(file=buf, force_terminal=True, width=80)
    render_markdown(console, None)  # type: ignore
    # Should not crash
