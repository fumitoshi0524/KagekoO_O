# tests/unit/test_repl_stream.py
from rich.console import Console
from io import StringIO


def test_stream_handler_creation():
    from kageko.repl.stream import StreamHandler
    buf = StringIO()
    console = Console(file=buf, force_terminal=True, width=80)
    handler = StreamHandler(console)
    assert handler is not None


def test_stream_handler_prints_tokens():
    from kageko.repl.stream import StreamHandler
    buf = StringIO()
    console = Console(file=buf, force_terminal=True, width=80)
    handler = StreamHandler(console)
    handler.on_token("Hello")
    handler.on_token(" world")
    handler.finish()
    output = buf.getvalue()
    assert "Hello" in output
    assert "world" in output


def test_stream_handler_finish():
    from kageko.repl.stream import StreamHandler
    buf = StringIO()
    console = Console(file=buf, force_terminal=True, width=80)
    handler = StreamHandler(console)
    handler.on_token("Hello")
    handler.finish()
    output = buf.getvalue()
    assert "Hello" in output


def test_stream_handler_spinner_start_stop():
    from kageko.repl.stream import StreamHandler
    buf = StringIO()
    console = Console(file=buf, force_terminal=True, width=80)
    handler = StreamHandler(console)
    handler.start_spinner("Loading...")
    handler.stop_spinner()
    assert handler._live is None
