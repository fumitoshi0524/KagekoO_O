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
