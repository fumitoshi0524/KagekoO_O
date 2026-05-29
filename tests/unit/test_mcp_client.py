"""Tests for MCP client module."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from kageko.tools.mcp_client import MCPClient, MCPServerConfig


def test_mcp_server_config_defaults():
    cfg = MCPServerConfig(name="test")
    assert cfg.command == ""
    assert cfg.args == []
    assert cfg.transport == "stdio"


def test_mcp_client_init_empty():
    client = MCPClient()
    assert client.servers == {}
    assert client.get_all_tools() == []


def test_mcp_client_init_with_servers():
    servers = [
        MCPServerConfig(name="fs", command="npx", args=["-y", "server"]),
        MCPServerConfig(name="db", command="python", args=["db_server.py"]),
    ]
    client = MCPClient(servers=servers)
    assert "fs" in client.servers
    assert "db" in client.servers


def test_mcp_client_get_tool_handler():
    client = MCPClient()
    handler = client.get_tool_handler("server1", "my_tool")
    assert callable(handler)


@pytest.mark.asyncio
async def test_mcp_client_disconnect():
    client = MCPClient()
    await client.disconnect_all()
    assert not client._connected
    assert client.get_all_tools() == []


def test_mcp_client_get_all_tools_empty():
    client = MCPClient()
    assert client.get_all_tools() == []
