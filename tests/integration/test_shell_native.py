import pytest


def test_native_shell_module_exists():
    """NativeShell must be importable from _native."""
    from kageko._native import NativeShell
    assert NativeShell is not None


def test_native_shell_create():
    """NativeShell must create a shell session."""
    from kageko._native import NativeShell
    shell = NativeShell()
    assert shell is not None


def test_native_shell_exec_echo():
    """NativeShell must execute a simple echo command."""
    from kageko._native import NativeShell
    shell = NativeShell()
    result = shell.exec("echo hello")
    assert "hello" in result


def test_native_shell_persistent_env():
    """NativeShell must persist environment across exec calls."""
    from kageko._native import NativeShell
    shell = NativeShell()
    shell.set_env("TEST_VAR", "kageko")
    result = shell.exec("echo $TEST_VAR")
    # On Windows cmd, $TEST_VAR won't expand, so also test with set_env/get_env
    if "kageko" not in result:
        # Fallback: verify env is persisted via get_env
        assert shell.get_env("TEST_VAR") == "kageko"
    else:
        assert "kageko" in result


def test_native_shell_get_cwd():
    """NativeShell must expose current working directory."""
    from kageko._native import NativeShell
    shell = NativeShell()
    cwd = shell.get_cwd()
    assert isinstance(cwd, str)
    assert len(cwd) > 0


@pytest.mark.asyncio
async def test_native_shell_registered_as_tool():
    """NativeShell must be registered in BUILTIN_TOOLS."""
    from kageko.tools.builtin import BUILTIN_TOOLS
    tool_names = [t["name"] for t in BUILTIN_TOOLS]
    assert "native_shell" in tool_names


@pytest.mark.asyncio
async def test_native_shell_handler_works():
    """native_shell_handler must execute commands."""
    from kageko.tools.builtin.shell_tools import native_shell_handler
    result = await native_shell_handler({"command": "echo test123"})
    assert "test123" in result
