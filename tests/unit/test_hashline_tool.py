# tests/unit/test_hashline_tool.py
import pytest


def test_hashline_tool_schema():
    """Hashline tool must have correct OpenAI function schema."""
    from kageko.tools.builtin.hashline_tool import HASHLINE_TOOL
    assert HASHLINE_TOOL["name"] == "hashline_edit"
    assert "source" in HASHLINE_TOOL["parameters"]["properties"]
    assert "edit" in HASHLINE_TOOL["parameters"]["properties"]
    assert "source" in HASHLINE_TOOL["parameters"]["required"]
    assert "edit" not in HASHLINE_TOOL["parameters"]["required"]


@pytest.mark.asyncio
async def test_hashline_tool_edit_single_line():
    """Hashline tool must apply a single anchor-based edit."""
    from kageko.tools.builtin.hashline_tool import hashline_edit

    source = "hello\nworld\nfoo"
    # Get anchor for 'world' line (line 2)
    import hashlib
    anchor = hashlib.sha256("world".encode()).hexdigest()[:8]

    edit = f"#2|{anchor}|replaced world"
    result = await hashline_edit({"source": source, "edit": edit})
    assert "replaced world" in result
    assert "hello" in result
    assert "foo" in result


@pytest.mark.asyncio
async def test_hashline_tool_batch_edits():
    """Hashline tool must apply multiple edits in sequence."""
    from kageko.tools.builtin.hashline_tool import hashline_edit

    source = "line one\nline two\nline three"
    import hashlib
    a1 = hashlib.sha256("line one".encode()).hexdigest()[:8]
    a2 = hashlib.sha256("line three".encode()).hexdigest()[:8]

    edits = f"#1|{a1}|FIRST\n#3|{a2}|THIRD"
    result = await hashline_edit({"source": source, "edits": edits})
    lines = result.split("\n")
    assert lines[0] == "FIRST"
    assert lines[1] == "line two"
    assert lines[2] == "THIRD"


@pytest.mark.asyncio
async def test_hashline_tool_anchor_not_found():
    """Hashline tool must return error for invalid anchor."""
    from kageko.tools.builtin.hashline_tool import hashline_edit

    source = "hello\nworld"
    edit = "#1|deadbeef|new content"
    result = await hashline_edit({"source": source, "edit": edit})
    assert "error" in result.lower() or "not found" in result.lower()


@pytest.mark.asyncio
async def test_hashline_tool_python_source_edit():
    """Hashline tool accepts source directly (no file I/O)."""
    from kageko.tools.builtin.hashline_tool import hashline_edit

    source = "def greet():\n    return 'hello'"
    import hashlib
    anchor = hashlib.sha256("def greet():".encode()).hexdigest()[:8]

    edit = f"#1|{anchor}|def greet(name):"
    result = await hashline_edit({"source": source, "edit": edit})
    assert "def greet(name):" in result
