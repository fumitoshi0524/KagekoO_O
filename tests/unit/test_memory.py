"""Tests for memory manager."""
from __future__ import annotations

import pytest

from kageko.data.db import KagekoDB
from kageko.learning.memory import MemoryManager, MemoryEntry


@pytest.fixture
async def db(tmp_path):
    database = KagekoDB(str(tmp_path / "test.db"))
    await database.init()
    yield database
    await database.close()


@pytest.fixture
async def memory(db):
    return MemoryManager(db)


@pytest.mark.asyncio
async def test_memory_store(memory):
    entry = MemoryEntry(id="key1", content="value1", source="test")
    await memory.store(entry)
    # Verify it was stored by searching
    results = await memory.prefetch("value1")
    assert len(results) >= 1
    assert results[0].id == "key1"


@pytest.mark.asyncio
async def test_memory_recall(memory):
    await memory.store(MemoryEntry(
        id="python1",
        content="Python is a programming language",
        source="test",
    ))
    results = await memory.prefetch("programming")
    assert len(results) >= 1
    assert any("programming" in r.content for r in results)


@pytest.mark.asyncio
async def test_memory_recall_empty(memory):
    results = await memory.prefetch("nonexistent_query_xyz")
    assert results == []


@pytest.mark.asyncio
async def test_summarize_tool_result(memory):
    summary = memory.summarize_tool_result("read_file", "line 1\nline 2\nline 3")
    assert "read_file" in summary
    assert "lines" in summary


@pytest.mark.asyncio
async def test_summarize_tool_result_bash_success(memory):
    summary = memory.summarize_tool_result("run_bash", "all tests passed\nok")
    assert "run_bash" in summary
    assert "exit 0" in summary


@pytest.mark.asyncio
async def test_summarize_tool_result_bash_failure(memory):
    summary = memory.summarize_tool_result(
        "run_bash",
        "FAILED test_foo - error\n1 failed, 0 passed",
    )
    assert "run_bash" in summary
    assert "failed" in summary.lower()


@pytest.mark.asyncio
async def test_memory_store_tags(memory):
    await memory.store(MemoryEntry(
        id="tagged1",
        content="Tagged entry",
        tags=["alpha", "beta"],
        source="test",
    ))
    results = await memory.prefetch("Tagged entry")
    assert len(results) >= 1
    assert "alpha" in results[0].tags
    assert "beta" in results[0].tags
