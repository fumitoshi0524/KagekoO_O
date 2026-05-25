import pytest
from kageko.tools.registry import ToolRegistry, Tool


@pytest.fixture
def registry():
    return ToolRegistry()


def test_register_tool(registry):
    tool = Tool(
        name="file_read",
        description="Read a file",
        parameters={
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
        handler=lambda args: "file contents",
        category="file",
    )
    registry.register(tool)
    assert registry.get("file_read") is tool


def test_register_duplicate_raises(registry):
    tool = Tool(
        name="file_read",
        description="Read",
        parameters={"type": "object", "properties": {}},
        handler=lambda args: "",
        category="file",
    )
    registry.register(tool)
    with pytest.raises(ValueError, match="already registered"):
        registry.register(tool)


def test_schemas_returns_openai_format(registry):
    tool = Tool(
        name="file_read",
        description="Read a file",
        parameters={
            "type": "object",
            "properties": {"path": {"type": "string", "description": "File path"}},
            "required": ["path"],
        },
        handler=lambda args: "",
        category="file",
    )
    registry.register(tool)
    schemas = registry.schemas()
    assert len(schemas) == 1
    assert schemas[0]["name"] == "file_read"
    assert schemas[0]["description"] == "Read a file"
    assert "parameters" in schemas[0]


def test_categories(registry):
    read_tool = Tool(name="file_read", description="", parameters={}, handler=lambda a: "", category="file")
    write_tool = Tool(name="file_write", description="", parameters={}, handler=lambda a: "", category="file")
    bash_tool = Tool(name="bash", description="", parameters={}, handler=lambda a: "", category="shell")
    registry.register(read_tool)
    registry.register(write_tool)
    registry.register(bash_tool)
    assert registry.categories() == {"file": ["file_read", "file_write"], "shell": ["bash"]}


def test_list_tools(registry):
    t1 = Tool(name="a", description="", parameters={}, handler=lambda a: "", category="x")
    t2 = Tool(name="b", description="", parameters={}, handler=lambda a: "", category="y")
    registry.register(t1)
    registry.register(t2)
    names = registry.list_names()
    assert sorted(names) == ["a", "b"]


@pytest.mark.asyncio
async def test_execute_tool(registry):
    async def handler(args):
        return f"read {args['path']}"

    tool = Tool(
        name="file_read",
        description="Read a file",
        parameters={"type": "object", "properties": {"path": {"type": "string"}}},
        handler=handler,
        category="file",
    )
    registry.register(tool)
    result = await registry.execute("file_read", {"path": "test.py"})
    assert result == "read test.py"


@pytest.mark.asyncio
async def test_execute_unknown_tool(registry):
    with pytest.raises(KeyError, match="not found"):
        await registry.execute("nonexistent", {})
