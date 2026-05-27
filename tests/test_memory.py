from __future__ import annotations

import asyncio
import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from kageko.data.db import KagekoDB
from kageko.learning.memory import MemoryManager, MemoryEntry


@pytest.fixture
async def db():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        database = KagekoDB(str(db_path))
        await database.init()
        yield database
        await database.close()


@pytest.fixture
async def memory(db):
    return MemoryManager(db)


@pytest.mark.asyncio
async def test_memory_store_and_search(memory):
    """Stored memories should be searchable via FTS5."""
    await memory.store(MemoryEntry(
        id="m1",
        content="Fixed the authentication bug in the login endpoint",
        tags=["bugfix", "auth"],
        source="conversation",
        session_id="s1",
    ))
    results = await memory.prefetch("authentication bug")
    assert len(results) >= 1
    assert results[0].id == "m1"


@pytest.mark.asyncio
async def test_memory_prefetch_limit(memory):
    """prefetch should respect the limit parameter."""
    for i in range(10):
        await memory.store(MemoryEntry(
            id=f"m{i}",
            content=f"Task number {i} about deployment",
            tags=["deploy"],
            source="conversation",
            session_id="s1",
        ))
    results = await memory.prefetch("deployment", limit=3)
    assert len(results) <= 3


@pytest.mark.asyncio
async def test_summarize_tool_result_terminal(memory):
    """Should produce meaningful summary for terminal tool results."""
    summary = memory.summarize_tool_result(
        "run_bash",
        "==================== 47 failed, 2 passed in 3.21s ====================\n"
        "FAILED tests/test_auth.py::test_login - AssertionError\n"
        "FAILED tests/test_auth.py::test_logout - TimeoutError\n"
        "... (45 more failures)",
    )
    assert "run_bash" in summary
    assert "47" in summary
    assert len(summary) < 300


@pytest.mark.asyncio
async def test_summarize_tool_result_file(memory):
    """Should produce meaningful summary for file tool results."""
    summary = memory.summarize_tool_result(
        "read_file",
        "line 1\nline 2\nline 3\n" + "\n".join([f"line {i}" for i in range(4, 50)]),
    )
    assert "read_file" in summary
    assert "50" in summary or "lines" in summary
