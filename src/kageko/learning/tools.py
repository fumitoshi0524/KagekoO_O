from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from kageko.data.db import KagekoDB
from kageko.tools.registry import Tool, ToolRegistry


@dataclass
class GeneratedTool:
    name: str
    description: str
    parameters: dict[str, Any]
    implementation: str
    category: str

    def is_valid(self) -> bool:
        if not re.match(r"^[a-z][a-z0-9_]*$", self.name):
            return False
        if not self.description:
            return False
        return True


class ToolGenerator:
    def __init__(self, db: KagekoDB, registry: ToolRegistry):
        self.db = db
        self.registry = registry

    async def hot_load(self, tool_def: dict[str, Any]) -> None:
        """Compile a tool definition and register it in the registry."""
        gen_tool = GeneratedTool(
            name=tool_def["name"],
            description=tool_def["description"],
            parameters=tool_def["parameters"],
            implementation=tool_def["implementation"],
            category=tool_def.get("category", "generated"),
        )

        if not gen_tool.is_valid():
            raise ValueError(f"Invalid tool definition: {gen_tool.name}")

        handler = _compile_handler(gen_tool.implementation)

        tool = Tool(
            name=gen_tool.name,
            description=gen_tool.description,
            parameters=gen_tool.parameters,
            handler=handler,
            category=gen_tool.category,
        )
        self.registry.register(tool)

        await self.db.save_tool(
            name=gen_tool.name,
            description=gen_tool.description,
            schema_json=json.dumps(gen_tool.parameters),
        )


def _compile_handler(code: str):
    """Compile a tool implementation string into an async handler function."""
    namespace: dict[str, Any] = {}
    exec(code, namespace)
    handler = namespace.get("handler")
    if handler is None:
        raise ValueError("Tool implementation must define a 'handler' function")
    return handler
