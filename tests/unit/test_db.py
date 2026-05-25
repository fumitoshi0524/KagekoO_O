import pytest
import tempfile
from pathlib import Path
from kageko.data.db import KagekoDB


@pytest.fixture
async def db(tmp_path):
    db_path = tmp_path / "test.db"
    database = KagekoDB(str(db_path))
    await database.init()
    yield database
    await database.close()


@pytest.mark.asyncio
async def test_init_creates_tables(db):
    tables = await db.list_tables()
    assert "sessions" in tables
    assert "skills" in tables
    assert "tools" in tables
    assert "trajectories" in tables
    assert "memory" in tables


@pytest.mark.asyncio
async def test_create_and_get_session(db):
    session = await db.create_session(platform="cli", chat_id="local")
    assert session.id is not None
    assert session.platform == "cli"

    fetched = await db.get_session(session.id)
    assert fetched.platform == "cli"
    assert fetched.chat_id == "local"


@pytest.mark.asyncio
async def test_session_messages(db):
    session = await db.create_session(platform="cli", chat_id="local")
    await db.append_message(session.id, role="user", content="hello")
    await db.append_message(session.id, role="assistant", content="hi there")

    messages = await db.get_messages(session.id)
    assert len(messages) == 2
    assert messages[0].content == "hello"
    assert messages[1].content == "hi there"


@pytest.mark.asyncio
async def test_save_and_search_skill(db):
    await db.save_skill(
        name="deploy-check",
        version="1.0.0",
        trigger="When deploying",
        description="Pre-deployment checks",
        content="# Deploy Check\n\n1. Run tests\n2. Check git status",
        tags=["devops"],
    )
    results = await db.search_skills("deploy")
    assert len(results) == 1
    assert results[0].name == "deploy-check"


@pytest.mark.asyncio
async def test_save_and_search_memory(db):
    await db.save_memory(key="user_pref", value="User prefers dark mode", source="session_1")
    results = await db.search_memory("dark mode")
    assert len(results) == 1
    assert results[0].key == "user_pref"


@pytest.mark.asyncio
async def test_save_trajectory(db):
    trajectory_data = {
        "query": "read config.py",
        "steps": [
            {"step": 1, "tool": "file_read", "args": {"path": "config.py"}, "result": "..."}
        ],
        "answer": "The config sets model=gpt-4o",
    }
    await db.save_trajectory(trajectory_data)
    trajectories = await db.list_trajectories()
    assert len(trajectories) == 1
    assert trajectories[0].query == "read config.py"
