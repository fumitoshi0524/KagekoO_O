# tests/unit/test_hashline_py.py
"""Tests for the Rust hashline edit engine via Python wrapper."""

from __future__ import annotations

import pytest

from kageko.tools.hashline import HashlineEditor


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_construction_empty():
    editor = HashlineEditor("")
    assert editor.source == ""
    assert editor.lines() == []


def test_construction_single_line():
    editor = HashlineEditor("hello")
    lines = editor.lines()
    assert len(lines) == 1
    assert lines[0].content == "hello"
    assert lines[0].number == 1


def test_construction_multi_line():
    editor = HashlineEditor("line one\nline two\nline three")
    lines = editor.lines()
    assert len(lines) == 3
    assert lines[0].content == "line one"
    assert lines[1].content == "line two"
    assert lines[2].content == "line three"


def test_anchors_are_deterministic():
    editor = HashlineEditor("hello\nworld")
    lines1 = editor.lines()
    lines2 = editor.lines()
    assert lines1[0].anchor == lines2[0].anchor
    assert lines1[1].anchor == lines2[1].anchor


# ---------------------------------------------------------------------------
# apply – single edit
# ---------------------------------------------------------------------------


def test_apply_replace_content():
    source = "hello\nworld\ntest"
    editor = HashlineEditor(source)
    anchor = editor.lines()[1].anchor  # "world"
    result = editor.apply(f"#2|{anchor}| planet")
    assert "planet" in result
    assert "world" not in result
    assert editor.source == result


def test_apply_delete_line():
    source = "aaa\nbbb\nccc"
    editor = HashlineEditor(source)
    anchor = editor.lines()[1].anchor  # "bbb"
    result = editor.apply(f"#2|{anchor}|")
    lines = result.split("\n")
    assert len(lines) == 2
    assert "bbb" not in result


def test_apply_anchor_mismatch_raises():
    editor = HashlineEditor("hello\nworld")
    with pytest.raises(Exception, match="Anchor not found"):
        editor.apply("#1|deadbeef| new content")


# ---------------------------------------------------------------------------
# apply_batch
# ---------------------------------------------------------------------------


def test_apply_batch():
    source = "aaa\nbbb\nccc"
    editor = HashlineEditor(source)
    a0 = editor.lines()[0].anchor
    a2 = editor.lines()[2].anchor
    result = editor.apply_batch([
        f"#1|{a0}| AAA",
        f"#3|{a2}| CCC",
    ])
    lines = result.split("\n")
    assert lines[0] == " AAA"
    assert lines[1] == "bbb"
    assert lines[2] == " CCC"


# ---------------------------------------------------------------------------
# lines helper
# ---------------------------------------------------------------------------


def test_lines_returns_list():
    editor = HashlineEditor("x\ny")
    lines = editor.lines()
    assert isinstance(lines, list)
    assert len(lines) == 2


def test_source_roundtrip():
    original = "one\ntwo\nthree"
    editor = HashlineEditor(original)
    assert editor.source == original
