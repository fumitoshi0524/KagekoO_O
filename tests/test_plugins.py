from __future__ import annotations

import pytest
import tempfile
import yaml
from pathlib import Path

from kageko.plugins import PluginManager, PluginManifest, PluginContext
from kageko.tools.registry import ToolRegistry, Tool


def test_discover_plugin_yaml(tmp_path):
    plugin_dir = tmp_path / ".kageko" / "plugins" / "test-plugin"
    plugin_dir.mkdir(parents=True)
    manifest = {
        "name": "test-plugin",
        "version": "0.1.0",
        "description": "A test plugin",
        "tools": ["my_tool"],
    }
    (plugin_dir / "plugin.yaml").write_text(yaml.dump(manifest))
    (plugin_dir / "__init__.py").write_text(
        "def register(ctx):\n    pass\n"
    )
    manager = PluginManager(plugin_dirs=[tmp_path / ".kageko" / "plugins"])
    plugins = manager.discover()
    assert len(plugins) == 1
    assert plugins[0].name == "test-plugin"


def test_plugin_context_register_tool():
    registry = ToolRegistry()
    ctx = PluginContext(registry=registry)
    tool = Tool(
        name="my_plugin_tool",
        description="A test tool",
        parameters={"type": "object", "properties": {}},
        handler=lambda **kw: "result",
        category="plugin",
    )
    ctx.register_tool(tool)
    names = [s["name"] for s in registry.schemas()]
    assert "my_plugin_tool" in names


def test_plugin_context_register_hook():
    ctx = PluginContext(registry=ToolRegistry())
    called = []
    def my_hook(tool_call):
        called.append(tool_call)
    ctx.register_hook("pre_tool_call", my_hook)
    assert "pre_tool_call" in ctx.hooks
    assert len(ctx.hooks["pre_tool_call"]) == 1
