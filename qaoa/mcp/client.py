"""MCP client — connects to MCP servers and discovers tools."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import subprocess
from typing import Any

from ..types import FUNCTIONAL_CATEGORIES, APPLICATION_DOMAINS


@dataclass(slots=True, frozen=True, kw_only=True)
class MCPTool:
    """An MCP-discovered tool with UniToolCall classification."""
    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)
    server_name: str = ""
    category: str = ""
    domain: str = ""


@dataclass(slots=True, kw_only=True)
class MCPClient:
    """MCP protocol client for external tool discovery and execution via stdio."""

    _servers: dict[str, subprocess.Popen] = field(default_factory=dict)
    _tools: dict[str, MCPTool] = field(default_factory=dict)
    _next_id: int = field(default=1, init=False)

    def connect_stdio(self, name: str, command: str, args: list[str] | None = None) -> None:
        """Connect to an MCP server via stdio. Handles initialize handshake."""
        cmd = [command] + (args or [])
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self._servers[name] = proc

        init_request = json.dumps({
            "jsonrpc": "2.0",
            "id": self._next_id,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "kageko", "version": "0.1.0"},
            },
        }) + "\n"
        self._next_id += 1

        try:
            proc.stdin.write(init_request)
            proc.stdin.flush()
            response_line = proc.stdout.readline()
            if not response_line:
                raise RuntimeError(f"MCP server '{name}' closed connection during init")
            response = json.loads(response_line)
            if "error" in response:
                raise RuntimeError(f"MCP initialize failed for '{name}': {response['error']}")
        except (json.JSONDecodeError, BrokenPipeError, OSError) as e:
            proc.kill()
            self._servers.pop(name, None)
            raise RuntimeError(f"MCP connection failed for '{name}': {e}") from e

    def discover_tools(self, server_name: str) -> list[MCPTool]:
        """List tools from a connected MCP server."""
        proc = self._servers.get(server_name)
        if proc is None:
            raise ValueError(f"Server '{server_name}' not connected")

        list_request = json.dumps({
            "jsonrpc": "2.0",
            "id": self._next_id,
            "method": "tools/list",
            "params": {},
        }) + "\n"
        self._next_id += 1

        proc.stdin.write(list_request)
        proc.stdin.flush()
        response_line = proc.stdout.readline()
        if not response_line:
            raise RuntimeError(f"MCP server '{server_name}' closed connection")
        response = json.loads(response_line)

        tools: list[MCPTool] = []
        for tool_data in response.get("result", {}).get("tools", []):
            mcp_name = tool_data.get("name", "unknown")
            description = tool_data.get("description", "")
            input_schema = tool_data.get("inputSchema", {})
            full_name = f"mcp.{server_name}.{mcp_name}"
            category = self._classify_category(tool_data)
            domain = self._classify_domain(tool_data)

            tool = MCPTool(
                name=full_name,
                description=description,
                input_schema=input_schema,
                server_name=server_name,
                category=category,
                domain=domain,
            )
            tools.append(tool)
            self._tools[full_name] = tool

        return tools

    def call_tool(self, server_name: str, tool_name: str, arguments: dict[str, Any]) -> str:
        """Execute a tool on a connected MCP server. Returns the result as a string."""
        proc = self._servers.get(server_name)
        if proc is None:
            raise ValueError(f"Server '{server_name}' not connected")

        short_name = tool_name
        if tool_name.startswith(f"mcp.{server_name}."):
            short_name = tool_name[len(f"mcp.{server_name}."):]

        call_request = json.dumps({
            "jsonrpc": "2.0",
            "id": self._next_id,
            "method": "tools/call",
            "params": {"name": short_name, "arguments": arguments},
        }) + "\n"
        self._next_id += 1

        proc.stdin.write(call_request)
        proc.stdin.flush()
        response_line = proc.stdout.readline()
        if not response_line:
            raise RuntimeError(f"MCP server '{server_name}' closed connection during tool call")
        response = json.loads(response_line)

        if "error" in response:
            return f"mcp_error: {response['error']}"
        result = response.get("result", {})
        content = result.get("content", [])
        if isinstance(content, list) and content:
            return "\n".join(
                item.get("text", str(item)) if isinstance(item, dict) else str(item)
                for item in content
            )
        return json.dumps(result)

    def classify_tools(self) -> list[MCPTool]:
        """Return all discovered tools with category/domain assigned."""
        return list(self._tools.values())

    def list_tools(self) -> list[str]:
        """List names of all discovered tools."""
        return sorted(self._tools)

    def get_tool(self, name: str) -> MCPTool | None:
        """Get a specific tool by name."""
        return self._tools.get(name)

    def disconnect(self, server_name: str) -> None:
        """Disconnect from an MCP server and remove its tools."""
        proc = self._servers.pop(server_name, None)
        if proc is not None:
            proc.stdin.close()
            proc.stdout.close()
            proc.stderr.close()
            proc.kill()
            proc.wait()
            self._tools = {
                k: v for k, v in self._tools.items()
                if v.server_name != server_name
            }

    @staticmethod
    def _classify_category(tool_data: dict[str, Any]) -> str:
        desc = tool_data.get("description", "").lower()
        name = tool_data.get("name", "").lower()
        text = f"{name} {desc}"
        if any(w in text for w in ("search", "find", "query", "lookup", "read")):
            return "search"
        if any(w in text for w in ("create", "write", "update", "delete", "deploy")):
            return "operations"
        if any(w in text for w in ("analyze", "compute", "calculate", "evaluate")):
            return "analysis"
        if any(w in text for w in ("generate", "create", "build", "produce")):
            return "generate"
        if any(w in text for w in ("system", "config", "manage", "admin")):
            return "system"
        if any(w in text for w in ("chart", "plot", "display", "show", "visualize")):
            return "visualization"
        return "operations"

    @staticmethod
    def _classify_domain(tool_data: dict[str, Any]) -> str:
        desc = tool_data.get("description", "").lower()
        name = tool_data.get("name", "").lower()
        text = f"{name} {desc}"
        for domain in APPLICATION_DOMAINS:
            if domain in text:
                return domain
        return "technology"


@dataclass(slots=True, kw_only=True)
class MCPToolAdapter:
    """Adapter to bridge MCP tools into the ToolRegistry via ToolFunction interface."""

    mcp_client: MCPClient
    server_name: str

    def call(self, name: str, payload: str) -> str:
        """Call MCP tool by name, parsing payload as JSON arguments."""
        args: dict[str, Any] = {}
        if payload.strip():
            try:
                args = json.loads(payload)
            except json.JSONDecodeError:
                args = {"input": payload}
        return self.mcp_client.call_tool(self.server_name, name, args)
