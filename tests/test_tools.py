def test_hashline_tool_registered():
    from kageko.tools.registry import ToolRegistry
    registry = ToolRegistry()
    from kageko.tools.builtin.hashline_tool import register
    register(registry)
    schema = registry.schemas()
    tool_names = [s["name"] for s in schema]
    assert "hashline_edit" in tool_names


def test_hashline_tool_schema():
    from kageko.tools.registry import ToolRegistry
    registry = ToolRegistry()
    from kageko.tools.builtin.hashline_tool import register
    register(registry)
    schema = registry.get_schema("hashline_edit")
    assert schema is not None
    params = schema["parameters"]["properties"]
    assert "file_path" in params
    assert "anchor" in params
    assert "new_content" in params
