import sys


def test_rewrite_argv_inserts_chat():
    sys.argv[:] = ["kageko", "explain", "this", "code"]
    from kageko.cli import _rewrite_argv

    _rewrite_argv()
    assert sys.argv == ["kageko", "chat", "explain", "this", "code"]


def test_rewrite_argv_skips_known_command():
    sys.argv[:] = ["kageko", "tui"]
    from kageko.cli import _rewrite_argv

    _rewrite_argv()
    assert sys.argv == ["kageko", "tui"]


def test_rewrite_argv_skips_flags():
    sys.argv[:] = ["kageko", "--help"]
    from kageko.cli import _rewrite_argv

    _rewrite_argv()
    assert sys.argv == ["kageko", "--help"]


def test_rewrite_argv_skips_empty():
    sys.argv[:] = ["kageko"]
    from kageko.cli import _rewrite_argv

    _rewrite_argv()
    assert sys.argv == ["kageko"]
