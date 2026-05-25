# tests/unit/test_curator.py
import pytest
from kageko.data.db import KagekoDB
from kageko.learning.curator import Curator


@pytest.fixture
async def db(tmp_path):
    database = KagekoDB(str(tmp_path / "test.db"))
    await database.init()
    yield database
    await database.close()


@pytest.fixture
def curator(db):
    return Curator(db=db, stale_days=30)


@pytest.mark.asyncio
async def test_curator_initializes(curator):
    assert curator.stale_days == 30


@pytest.mark.asyncio
async def test_curator_logs_action(curator, db):
    await curator.log_action("archive", "skill", "old-skill", "Skill not used in 30 days")
    # Verify no error on log write


@pytest.mark.asyncio
async def test_audit_tool_safety_blocks_dangerous(curator):
    result = await curator.audit_tool_safety("bad_tool", "import os\nos.system('rm -rf /')")
    assert result is False


@pytest.mark.asyncio
async def test_audit_tool_safety_allows_safe(curator):
    result = await curator.audit_tool_safety("safe_tool", "async def handler(args): return args['x']")
    assert result is True
