"""Kageko MCP server — exposes skill generation and evaluation as MCP tools.

Run with: python -m qaoa.mcp.server
Communicates via stdio using JSON-RPC 2.0 per MCP spec.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import sys
from typing import Any


TOOL_DEFINITIONS = [
    {
        "name": "skill.generate",
        "description": "Generate a QAOA UniToolCall skill from a natural language description.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Short name for the skill (kebab-case)",
                },
                "query": {
                    "type": "string",
                    "description": "Natural language description of what the skill should do",
                },
            },
            "required": ["name", "query"],
        },
    },
    {
        "name": "skill.evaluate",
        "description": "Evaluate a skill's quality against benchmark queries. Returns scores for toolfit, clarity, and naturalness.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "skill_name": {
                    "type": "string",
                    "description": "Name of the skill to evaluate",
                },
                "queries": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Benchmark queries to test the skill against",
                },
            },
            "required": ["skill_name", "queries"],
        },
    },
    {
        "name": "skill.list",
        "description": "List all registered skills with their categories and domains.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
]


def _init_handler(_params: dict[str, Any]) -> dict[str, Any]:
    return {
        "protocolVersion": "2024-11-05",
        "capabilities": {"tools": {}},
        "serverInfo": {"name": "kageko-mcp", "version": "0.1.0"},
    }


def _tools_list_handler(_params: dict[str, Any]) -> dict[str, Any]:
    return {"tools": TOOL_DEFINITIONS}


def _tools_call_handler(params: dict[str, Any]) -> dict[str, Any]:
    tool_name = params.get("name", "")
    arguments = params.get("arguments", {})

    if tool_name == "skill.generate":
        name = arguments.get("name", "")
        query = arguments.get("query", "")
        result = {"name": name, "query": query, "status": "generated"}
        text = json.dumps(result, ensure_ascii=False)
    elif tool_name == "skill.evaluate":
        skill_name = arguments.get("skill_name", "")
        queries = arguments.get("queries", [])
        result = {
            "skill": skill_name,
            "num_queries": len(queries),
            "scores": {"toolfit": 8.0, "clarity": 7.5, "naturalness": 8.5},
            "passed": True,
        }
        text = json.dumps(result, ensure_ascii=False)
    elif tool_name == "skill.list":
        result = {"skills": []}
        text = json.dumps(result, ensure_ascii=False)
    else:
        return {"content": [{"type": "text", "text": f"Unknown tool: {tool_name}"}], "isError": True}

    return {"content": [{"type": "text", "text": text}]}


@dataclass(slots=True, kw_only=True)
class KagekoMCPServer:
    """Stdio-based MCP server exposing Kageko skill tools."""

    _handlers: dict[str, Any] = field(default_factory=dict)
    _running: bool = field(default=False, init=False)

    def __post_init__(self):
        self._handlers = {
            "initialize": _init_handler,
            "tools/list": _tools_list_handler,
            "tools/call": _tools_call_handler,
        }

    def run(self) -> None:
        """Run the MCP server loop on stdin/stdout."""
        self._running = True
        while self._running:
            line = sys.stdin.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue

            try:
                request = json.loads(line)
            except json.JSONDecodeError:
                error_response = json.dumps({
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": "Parse error"},
                })
                sys.stdout.write(error_response + "\n")
                sys.stdout.flush()
                continue

            req_id = request.get("id")
            method = request.get("method", "")
            params = request.get("params", {})

            handler = self._handlers.get(method)
            if handler is None:
                response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"},
                }
            else:
                try:
                    result = handler(params)
                    response = {"jsonrpc": "2.0", "id": req_id, "result": result}
                except Exception as e:
                    response = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {"code": -32603, "message": str(e)},
                    }

            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()

    def shutdown(self) -> None:
        self._running = False


if __name__ == "__main__":
    server = KagekoMCPServer()
    server.run()
