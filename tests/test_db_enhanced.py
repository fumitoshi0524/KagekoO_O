from __future__ import annotations

import asyncio
import pytest
import tempfile
from pathlib import Path

from kageko.data.db import KagekoDB


@pytest.mark.asyncio
async def test_wal_mode_enabled():
    """Database should run in WAL journal mode."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = KagekoDB(str(db_path))
        await db.init()
        try:
            cursor = await db._conn.execute("PRAGMA journal_mode")
            row = await cursor.fetchone()
            assert row[0] == "wal"
        finally:
            await db.close()


@pytest.mark.asyncio
async def test_write_retry_succeeds():
    """write_with_retry should succeed on first try in no-contention scenario."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = KagekoDB(str(db_path))
        await db.init()
        try:
            await db.write_with_retry(
                "INSERT INTO sessions (id, platform, chat_id, created_at) VALUES (?, ?, ?, ?)",
                ("test-session", "cli", "local", "2025-01-01T00:00:00"),
            )
            cursor = await db._conn.execute(
                "SELECT id FROM sessions WHERE id = ?", ("test-session",)
            )
            row = await cursor.fetchone()
            assert row is not None
            assert row[0] == "test-session"
        finally:
            await db.close()


@pytest.mark.asyncio
async def test_wal_checkpoint_counter():
    """After 50 writes, WAL checkpoint should have been triggered."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = KagekoDB(str(db_path))
        await db.init()
        try:
            for i in range(51):
                await db.write_with_retry(
                    "INSERT INTO sessions (id, platform, chat_id, created_at) VALUES (?, ?, ?, ?)",
                    (f"session-{i}", "cli", "local", "2025-01-01T00:00:00"),
                )
            # _write_count should have reset after checkpoint at 50
            assert db._write_count <= 1
        finally:
            await db.close()


@pytest.mark.asyncio
async def test_fts5_memory_search():
    """FTS5 should index memory content for full-text search."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = KagekoDB(str(db_path))
        await db.init()
        await db.write_with_retry(
            "INSERT INTO memory (id, content, tags, source, session_id) VALUES (?, ?, ?, ?, ?)",
            ("mem-1", "deployed nginx to production server", "ops,deploy", "conversation", "s1"),
        )
        results = await db.search_memory("nginx production")
        assert len(results) >= 1
        assert results[0]["id"] == "mem-1"
        await db.close()


@pytest.mark.asyncio
async def test_fts5_cjk_search():
    """Trigram FTS should support CJK substring search."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = KagekoDB(str(db_path))
        await db.init()
        await db.write_with_retry(
            "INSERT INTO memory (id, content, tags, source, session_id) VALUES (?, ?, ?, ?, ?)",
            ("mem-2", "部署了nginx到生产服务器", "运维", "conversation", "s1"),
        )
        results = await db.search_memory("部署了")
        assert len(results) >= 1
        assert results[0]["id"] == "mem-2"
        await db.close()


@pytest.mark.asyncio
async def test_fts5_sync_on_insert():
    """FTS index should auto-sync when memory rows are inserted."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = KagekoDB(str(db_path))
        await db.init()
        # Insert via write_with_retry (triggers should fire)
        await db.write_with_retry(
            "INSERT INTO memory (id, content, tags, source, session_id) VALUES (?, ?, ?, ?, ?)",
            ("mem-3", "refactored authentication module", "code,refactor", "tool_result", "s2"),
        )
        results = await db.search_memory("authentication")
        assert len(results) >= 1
        await db.close()


@pytest.mark.asyncio
async def test_save_memory_fts_integration():
    """save_memory() + search_memory() should work end-to-end including trigger sync."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = KagekoDB(str(db_path))
        await db.init()
        await db.save_memory(
            content="部署了新的数据库集群到生产环境",
            tags="运维,部署",
            source="conversation",
            session_id="s3",
        )
        results = await db.search_memory("部署")
        assert len(results) >= 1
        assert results[0]["id"] is not None
        assert "数据库集群" in results[0]["content"]
        await db.close()
