import pytest
from kageko.learning.tools import ToolGenerator, GeneratedTool
from kageko.tools.registry import ToolRegistry
from kageko.data.db import KagekoDB


@pytest.fixture
async def db(tmp_path):
    database = KagekoDB(str(tmp_path / "test.db"))
    await database.init()
    yield database
    await database.close()


def test_generated_tool_validation():
    tool = GeneratedTool(
        name="deploy_check",
        description="Check deployment readiness",
        parameters={
            "type": "object",
            "properties": {"env": {"type": "string"}},
            "required": ["env"],
        },
        implementation='async def handler(args): return "ok"',
        category="system",
    )
    assert tool.name == "deploy_check"
    assert tool.is_valid()


def test_generated_tool_invalid_name():
    tool = GeneratedTool(
        name="123bad",
        description="test",
        parameters={},
        implementation="",
        category="system",
    )
    assert not tool.is_valid()


async def test_hot_load_registers_tool(db):
    registry = ToolRegistry()
    gen = ToolGenerator(db=db, registry=registry)

    tool_def = {
        "name": "greet",
        "description": "Greet someone",
        "parameters": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
        "implementation": 'async def handler(args): return f"Hello, {args[\'name\']}!"',
        "category": "system",
    }

    await gen.hot_load(tool_def)
    assert registry.get("greet") is not None

    result = await registry.execute("greet", {"name": "World"})
    assert result == "Hello, World!"
