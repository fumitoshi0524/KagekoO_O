import pytest
from unittest.mock import AsyncMock, MagicMock
from kageko.learning.skills import SkillEngine, Skill, validate_frontmatter


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.search_memory = AsyncMock(return_value=[])
    return db


@pytest.fixture
def mock_llm():
    llm = AsyncMock()
    llm.chat = AsyncMock(return_value=MagicMock(
        content='{"name": "deploy-check", "version": "1.0.0", "description": "Pre-deploy", "trigger": "deploying", "tags": ["ops"], "steps": ["Run tests"]}'
    ))
    return llm


@pytest.fixture
def engine(mock_db, mock_llm):
    return SkillEngine(db=mock_db, llm=mock_llm)


def test_skill_dataclass():
    skill = Skill(
        name="test",
        version="1.0.0",
        trigger="When testing",
        description="A test skill",
        tags=["test"],
        steps=["Do thing"],
        content="# Test",
    )
    assert skill.name == "test"
    assert skill.steps == ["Do thing"]


def test_validate_frontmatter_valid():
    errors = validate_frontmatter(
        name="test-skill", version="1.0.0", trigger="when testing", description="A test skill",
    )
    assert errors == []


def test_validate_frontmatter_missing_name():
    errors = validate_frontmatter(name="", version="1.0.0", trigger="t", description="d")
    assert any("name" in e for e in errors)


def test_validate_frontmatter_bad_name():
    errors = validate_frontmatter(name="Bad Name", version="1.0.0", trigger="t", description="d")
    assert any("kebab-case" in e for e in errors)


@pytest.mark.asyncio
async def test_create_from_conversation(engine):
    messages = [
        {"role": "user", "content": "I need a skill for deploying"},
        {"role": "assistant", "content": "Here's what I do: run tests"},
    ]
    skill = await engine.create_from_conversation(messages)
    assert skill is not None
    assert skill["name"] == "deploy-check"


@pytest.mark.asyncio
async def test_search(engine):
    results = await engine.search("deploy")
    assert results == []
