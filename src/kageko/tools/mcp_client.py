"""MCP client for connecting to external tool servers."""
from __future__ import annotations

import asyncio
import logging
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class MCPServerConfig:
    name: str
    command: str = ""          # for stdio transport
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    url: str = ""              # for HTTP/SSE transport
    transport: str = "stdio"   # stdio | http | sse


class MCPClient:
    """Manages connections to MCP tool servers and exposes their tools."""

    def __init__(self, servers: list[MCPServerConfig] | None = None) -> None:
        self.servers: dict[str, MCPServerConfig] = {}
        for s in (servers or []):
            self.servers[s.name] = s
        self._tools: dict[str, list[dict]] = {}
        self._connected = False
        self._sessions: dict[str, Any] = {}       # server_name -> ClientSession
        self._exit_stacks: dict[str, AsyncExitStack] = {}

    async def connect_all(self) -> None:
        """Connect to all configured MCP servers and discover their tools."""
        any_connected = False
        for name, config in self.servers.items():
            try:
                await self._connect_and_discover(name, config)
                logger.info("Connected to MCP server %s: %d tools", name, len(self._tools.get(name, [])))
                any_connected = True
            except Exception as e:
                logger.warning("Failed to connect to MCP server %s: %s", name, e)
                self._tools[name] = []
        self._connected = any_connected

    async def _connect_and_discover(self, name: str, config: MCPServerConfig) -> None:
        """Open a persistent session and discover tools."""
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        if config.transport != "stdio":
            logger.warning("Transport %s not yet supported for %s", config.transport, name)
            self._tools[name] = []
            return

        params = StdioServerParameters(
            command=config.command,
            args=config.args,
            env=config.env or None,
        )

        stack = AsyncExitStack()
        try:
            read_stream, write_stream = await stack.enter_async_context(stdio_client(params))
            session = await stack.enter_async_context(ClientSession(read_stream, write_stream))
            await session.initialize()

            self._sessions[name] = session
            self._exit_stacks[name] = stack

            result = await session.list_tools()
            self._tools[name] = [
                {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.inputSchema or {},
                    "_mcp_server": name,
                }
                for tool in result.tools
            ]
        except Exception:
            await stack.aclose()
            raise

    async def call_tool(self, server_name: str, tool_name: str, arguments: dict) -> str:
        """Call a tool on an MCP server and return the result text."""
        session = self._sessions.get(server_name)
        if session is None:
            return f"[ERROR] No active session for MCP server: {server_name}"

        try:
            result = await session.call_tool(tool_name, arguments)
            texts = []
            for content in result.content:
                if hasattr(content, "text"):
                    texts.append(content.text)
                else:
                    texts.append(str(content))
            return "\n".join(texts)
        except Exception as e:
            # Session may have died — try to reconnect once
            logger.warning("MCP tool call failed for %s/%s, attempting reconnect: %s", server_name, tool_name, e)
            try:
                await self._reconnect(server_name)
                session = self._sessions.get(server_name)
                if session is None:
                    return f"[ERROR] Reconnect failed for: {server_name}"
                result = await session.call_tool(tool_name, arguments)
                texts = []
                for content in result.content:
                    if hasattr(content, "text"):
                        texts.append(content.text)
                    else:
                        texts.append(str(content))
                return "\n".join(texts)
            except Exception as e2:
                return f"[ERROR] MCP tool call failed after reconnect: {e2}"

    async def _reconnect(self, server_name: str) -> None:
        """Tear down and re-establish a single server connection."""
        config = self.servers.get(server_name)
        if not config:
            return
        # Tear down old session
        stack = self._exit_stacks.pop(server_name, None)
        if stack:
            await stack.aclose()
        self._sessions.pop(server_name, None)
        # Reconnect
        await self._connect_and_discover(server_name, config)

    async def disconnect_all(self) -> None:
        """Clean up all connections."""
        for stack in self._exit_stacks.values():
            await stack.aclose()
        self._sessions.clear()
        self._exit_stacks.clear()
        self._tools.clear()
        self._connected = False

    def get_all_tools(self) -> list[dict]:
        """Return all discovered tools from all connected servers."""
        result = []
        for tools in self._tools.values():
            result.extend(tools)
        return result

    def get_tool_handler(self, server_name: str, tool_name: str):
        """Return an async handler function for a specific MCP tool."""
        async def handler(arguments: dict) -> str:
            return await self.call_tool(server_name, tool_name, arguments)
        return handler
