"""Tests for diff rendering."""
from __future__ import annotations

from io import StringIO

import pytest
from rich.console import Console

from kageko.repl.diff import is_diff_output, render_diff, render_diff_text


def test_is_diff_output_unified():
    text = "--- a/file.py\n+++ b/file.py\n@@ -1,3 +1,3 @@\n-old\n+new"
    assert is_diff_output(text) is True


def test_is_diff_output_git():
    text = "diff --git a/file.py b/file.py\nindex abc..def\n--- a/file.py"
    assert is_diff_output(text) is True


def test_is_diff_output_plain():
    assert is_diff_output("hello world") is False
    assert is_diff_output("") is False


def test_is_diff_output_incomplete():
    # Has +++ and --- but no @@
    assert is_diff_output("--- a\n+++ b") is False


def test_render_diff_no_changes():
    buf = StringIO()
    c = Console(file=buf, force_terminal=True, width=80)
    render_diff(c, "same content", "same content")
    output = buf.getvalue()
    assert "No changes" in output


def test_render_diff_with_changes():
    buf = StringIO()
    c = Console(file=buf, force_terminal=True, width=80)
    render_diff(c, "old line\n", "new line\n", filename="test.py")
    output = buf.getvalue()
    assert "-old line" in output
    assert "+new line" in output
    assert "@@" in output


def test_render_diff_text():
    buf = StringIO()
    c = Console(file=buf, force_terminal=True, width=80)
    diff = "--- a/f\n+++ b/f\n@@ -1,1 +1,1 @@\n-old\n+new"
    render_diff_text(c, diff)
    output = buf.getvalue()
    assert "old" in output
    assert "new" in output


def test_render_diff_text_empty():
    buf = StringIO()
    c = Console(file=buf, force_terminal=True, width=80)
    render_diff_text(c, "")
    assert buf.getvalue() == ""
