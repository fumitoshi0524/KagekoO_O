# tests/unit/test_cli_repl_integration.py


def test_repl_modules_importable():
    from kageko.repl.banner import render_welcome
    from kageko.repl.tool_card import render_tool_call, render_tool_result
    from kageko.repl.status import render_status_line
    from kageko.repl.stream import StreamHandler
    from kageko.repl.renderer import render_markdown
    assert callable(render_welcome)
    assert callable(render_tool_call)
    assert callable(render_tool_result)
    assert callable(render_status_line)
    assert StreamHandler is not None
    assert callable(render_markdown)


def test_cli_imports_work():
    from kageko.cli import _interactive_chat, _single_query
    assert callable(_interactive_chat)
    assert callable(_single_query)
