"""MCP (Model Context Protocol) integration — client, server, and adapters."""

from __future__ import annotations

from .client import MCPClient, MCPTool, MCPToolAdapter
from .server import KagekoMCPServer, TOOL_DEFINITIONS

__all__ = ["MCPClient", "MCPTool", "MCPToolAdapter", "KagekoMCPServer", "TOOL_DEFINITIONS"]
