from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from kageko.learning.skills import SkillEngine, validate_frontmatter


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.search_memory = AsyncMock(return_value=[])
    db.write_with_retry = AsyncMock()
    return db


@pytest.fixture
def mock_llm():
    llm = AsyncMock()
    llm.chat = AsyncMock(return_value=MagicMock(
        content='{"name": "deploy-check", "version": "1.0.0", "description": "Pre-deploy validation", "trigger": "deploying", "tags": ["ops"], "steps": ["Run tests", "Check git status"]}'
    ))
    return llm


@pytest.fixture
def engine(mock_db, mock_llm):
    return SkillEngine(db=mock_db, llm=mock_llm)


def test_validate_frontmatter_valid():
    errors = validate_frontmatter(
        name="test-skill", version="1.0.0", trigger="when testing", description="A test skill", tags=["test"],
    )
    assert errors == []


def test_validate_frontmatter_missing_fields():
    errors = validate_frontmatter(name="", version="1.0.0")
    assert len(errors) > 0


def test_render_template_variables(engine):
    content = "Skill dir: ${KAGEKO_SKILL_DIR}, Session: ${KAGEKO_SESSION_ID}"
    rendered = engine.render_template(content, skill_dir="/skills/test", session_id="s123")
    assert "/skills/test" in rendered
    assert "s123" in rendered


def test_render_template_inline_shell(engine):
    content = "Date: !`echo 2026-05-27`"
    rendered = engine.render_template(content)
    assert "2026-05-27" in rendered


@pytest.mark.asyncio
async def test_create_from_conversation(engine):
    messages = [
        {"role": "user", "content": "I need a skill for deploying"},
        {"role": "assistant", "content": "Here's what I do: run tests, check status"},
    ]
    skill = await engine.create_from_conversation(messages)
    assert skill is not None
    assert skill["name"] == "deploy-check"


@pytest.mark.asyncio
async def test_tool_generator_detect_pattern(mock_db):
    from kageko.learning.tools import ToolGenerator

    llm = AsyncMock()
    llm.chat = AsyncMock(return_value=MagicMock(content='{"name": "git_status", "category": "shell", "description": "Get git status", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}}, "implementation": "def execute(path): return \\"ok\\""}'))

    mock_db.get_recent_trajectories = AsyncMock(return_value=[
        {"actions": [{"tool": "run_bash", "args": {"command": "git status"}}]},
        {"actions": [{"tool": "run_bash", "args": {"command": "git status"}}]},
        {"actions": [{"tool": "run_bash", "args": {"command": "git status"}}]},
        {"actions": [{"tool": "run_bash", "args": {"command": "git status"}}]},
    ])

    gen = ToolGenerator(db=mock_db, llm=llm)
    tool_def = await gen.analyze_and_generate()
    assert tool_def is not None
    assert tool_def["name"] == "git_status"


@pytest.mark.asyncio
async def test_tool_generator_hot_load(mock_db):
    from kageko.learning.tools import ToolGenerator
    from kageko.tools.registry import ToolRegistry

    llm = AsyncMock()
    registry = ToolRegistry()
    gen = ToolGenerator(db=mock_db, llm=llm, registry=registry)
    tool_def = {
        "name": "echo_tool",
        "category": "utility",
        "description": "Echo input",
        "parameters": {"type": "object", "properties": {"text": {"type": "string"}}},
        "implementation": "def execute(text): return text",
    }
    gen.hot_load(tool_def)
    names = [s["name"] for s in registry.schemas()]
    assert "echo_tool" in names
