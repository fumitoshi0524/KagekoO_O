# tests/unit/test_repl_tool_card.py
from rich.console import Console
from io import StringIO


def test_tool_card_pending():
    from kageko.repl.tool_card import render_tool_call
    buf = StringIO()
    console = Console(file=buf, force_terminal=True, width=80)
    render_tool_call(console, "file_read", {"path": "/tmp/test.py"}, status="pending")
    output = buf.getvalue()
    assert "file_read" in output
    assert "/tmp/test.py" in output


def test_tool_card_success():
    from kageko.repl.tool_card import render_tool_result
    buf = StringIO()
    console = Console(file=buf, force_terminal=True, width=80)
    render_tool_result(console, "file_read", "print('hello')", is_error=False)
    output = buf.getvalue()
    assert "file_read" in output
    assert "print" in output


def test_tool_card_error():
    from kageko.repl.tool_card import render_tool_result
    buf = StringIO()
    console = Console(file=buf, force_terminal=True, width=80)
    render_tool_result(console, "bash_run", "[ERROR] Command not found", is_error=True)
    output = buf.getvalue()
    assert "ERROR" in output or "error" in output.lower()


def test_tool_card_truncates_long_args():
    from kageko.repl.tool_card import _truncate_value
    long_val = "x" * 500
    result = _truncate_value(long_val, max_len=100)
    assert len(result) <= 110


def test_tool_card_result_json():
    from kageko.repl.tool_card import render_tool_result
    buf = StringIO()
    console = Console(file=buf, force_terminal=True, width=80)
    render_tool_result(console, "file_read", '{"key": "value"}', is_error=False)
    output = buf.getvalue()
    assert "file_read" in output
    assert "key" in output
