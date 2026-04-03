"""Tooling integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


ToolFunction = Callable[[str], str]


@dataclass(slots=True, kw_only=True)
class ToolRegistry:
    _tools: dict[str, ToolFunction] = field(default_factory=dict)

    def register(self, name: str, tool: ToolFunction) -> None:
        self._tools[name] = tool

    def call(self, name: str, payload: str) -> str:
        tool = self._tools.get(name)
        if tool is None:
            raise ValueError(f"Tool '{name}' is not registered.")
        return tool(payload)
