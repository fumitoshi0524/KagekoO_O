import pytest
from pathlib import Path
from kageko.tools.grep_tool import grep


def test_grep_finds_matches(tmp_path):
    (tmp_path / "test.py").write_text("hello world\nfoo bar\nhello again")
    result = grep("hello", str(tmp_path))
    assert "hello world" in result
    assert "hello again" in result
    assert "foo bar" not in result


def test_grep_no_matches(tmp_path):
    (tmp_path / "test.py").write_text("nothing here")
    result = grep("xyz", str(tmp_path))
    assert "No matches" in result


def test_grep_max_results(tmp_path):
    (tmp_path / "test.py").write_text("\n".join([f"match {i}" for i in range(100)]))
    result = grep("match", str(tmp_path), max_results=3)
    lines = result.strip().split("\n")
    assert len(lines) == 3
