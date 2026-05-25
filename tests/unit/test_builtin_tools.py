# tests/unit/test_builtin_tools.py
import pytest
import tempfile
from pathlib import Path
from kageko.tools.builtin.file_tools import file_read, file_write, file_list
from kageko.tools.builtin.shell_tools import bash_run
from kageko.tools.builtin.system_tools import echo, todo_add, todo_list


@pytest.mark.asyncio
async def test_file_write_and_read(tmp_path):
    fp = str(tmp_path / "test.txt")
    result = await file_write({"path": fp, "content": "hello world"})
    assert "written" in result.lower()

    content = await file_read({"path": fp})
    assert content == "hello world"


@pytest.mark.asyncio
async def test_file_read_not_found():
    content = await file_read({"path": "/nonexistent/file.txt"})
    assert "[ERROR]" in content


@pytest.mark.asyncio
async def test_file_list(tmp_path):
    (tmp_path / "a.py").write_text("# a")
    (tmp_path / "b.txt").write_text("b")
    result = await file_list({"path": str(tmp_path)})
    assert "a.py" in result
    assert "b.txt" in result


@pytest.mark.asyncio
async def test_bash_run():
    result = await bash_run({"command": "echo hello"})
    assert "hello" in result


@pytest.mark.asyncio
async def test_bash_run_timeout():
    result = await bash_run({"command": "sleep 10", "timeout": 1})
    assert "timeout" in result.lower() or "timed out" in result.lower()


@pytest.mark.asyncio
async def test_echo():
    result = await echo({"text": "test message"})
    assert result == "test message"


@pytest.mark.asyncio
async def test_todo():
    result = await todo_add({"task": "Fix the bug", "priority": "high"})
    assert "added" in result.lower()

    items = await todo_list({})
    assert "Fix the bug" in items
