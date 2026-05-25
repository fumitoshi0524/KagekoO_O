from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[[dict[str, Any]], Awaitable[str]]
    category: str

    def to_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}
        self._categories: dict[str, list[str]] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered")
        self._tools[tool.name] = tool
        self._categories.setdefault(tool.category, []).append(tool.name)

    def get(self, name: str) -> Tool:
        return self._tools[name]

    def list_names(self) -> list[str]:
        return list(self._tools.keys())

    def categories(self) -> dict[str, list[str]]:
        return dict(self._categories)

    def schemas(self) -> list[dict[str, Any]]:
        return [tool.to_schema() for tool in self._tools.values()]

    async def execute(self, name: str, args: dict[str, Any]) -> str:
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not found")
        tool = self._tools[name]
        return await tool.handler(args)
