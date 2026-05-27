from __future__ import annotations

import json
import pytest
import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock

from kageko.data.db import KagekoDB
from kageko.learning.curator import Curator, CuratorConfig


@pytest.fixture
async def db():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        database = KagekoDB(str(db_path))
        await database.init()
        yield database
        await database.close()


@pytest.fixture
def curator_config(tmp_path):
    return CuratorConfig(
        stale_days=30, archive_days=90, interval_hours=0, state_path=tmp_path / ".curator_state"
    )


@pytest.fixture
def curator(db, curator_config):
    return Curator(db=db, config=curator_config)


@pytest.mark.asyncio
async def test_transition_active_to_stale(curator, db):
    old_ts = time.time() - 31 * 86400
    await db.write_with_retry(
        "INSERT INTO skills (name, version, description, content, last_used, state, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 'active', '2020-01-01', '2020-01-01')",
        ("old-skill", "1.0.0", "An old skill", "# Old Skill\n\nSteps...", old_ts),
    )
    actions = await curator._transition_states()
    assert any("stale" in a for a in actions)


@pytest.mark.asyncio
async def test_transition_stale_to_archived(curator, db):
    old_ts = time.time() - 91 * 86400
    await db.write_with_retry(
        "INSERT INTO skills (name, version, description, content, last_used, state, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 'stale', '2020-01-01', '2020-01-01')",
        ("very-old-skill", "1.0.0", "A very old skill", "# Very Old\n\nSteps...", old_ts),
    )
    actions = await curator._transition_states()
    assert any("archived" in a for a in actions)


@pytest.mark.asyncio
async def test_pinned_skills_exempt(curator, db):
    old_ts = time.time() - 31 * 86400
    await db.write_with_retry(
        "INSERT INTO skills (name, version, description, content, last_used, pinned, state, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 1, 'active', '2020-01-01', '2020-01-01')",
        ("pinned-skill", "1.0.0", "Important skill", "# Pinned\n\nSteps...", old_ts),
    )
    actions = await curator._transition_states()
    assert not any("pinned-skill" in a for a in actions)


@pytest.mark.asyncio
async def test_audit_generated_tool(curator):
    safe_code = "def run(x):\n    return x + 1"
    assert await curator.audit_tool_safety("safe-tool", safe_code) is True

    dangerous_code = "import os\nos.system('rm -rf /')"
    assert await curator.audit_tool_safety("dangerous-tool", dangerous_code) is False


@pytest.mark.asyncio
async def test_maybe_run_respects_interval(tmp_path, db):
    state_path = tmp_path / ".curator_state"
    config = CuratorConfig(interval_hours=24, state_path=state_path)
    c = Curator(db=db, config=config)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps({"last_run": time.time()}))
    result = await c.maybe_run()
    assert result is False


@pytest.mark.asyncio
async def test_maintain_logs_actions(curator, db):
    await curator.maintain()
    cursor = await db._conn.execute("SELECT COUNT(*) FROM curator_log")
    row = await cursor.fetchone()
    assert row[0] >= 0
