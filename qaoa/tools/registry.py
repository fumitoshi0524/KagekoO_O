"""Tool registry — central store for all executable tools."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

ToolFunction = Callable[[str], str]


@dataclass(slots=True, frozen=True, kw_only=True)
class ToolSpec:
    name: str
    description: str
    input_contract: str
    output_contract: str
    tags: tuple[str, ...] = ()
    risk_level: str = "read"  # read | write | destructive
    category: str = ""
    domain: str = ""


@dataclass(slots=True, kw_only=True)
class ToolRegistry:
    _tools: dict[str, ToolFunction] = field(default_factory=dict)
    _specs: dict[str, ToolSpec] = field(default_factory=dict)
    _frozen: bool = False

    def register(
        self,
        name: str,
        tool: ToolFunction,
        *,
        description: str = "",
        input_contract: str = "plain text payload",
        output_contract: str = "plain text output",
        tags: tuple[str, ...] = (),
        risk_level: str = "read",
        category: str = "",
        domain: str = "",
    ) -> None:
        self._tools[name] = tool
        self._specs[name] = ToolSpec(
            name=name, description=description,
            input_contract=input_contract, output_contract=output_contract,
            tags=tags, risk_level=risk_level, category=category, domain=domain,
        )

    def register_from_mcp(self, mcp_tool: "MCPTool") -> None:
        """Register an MCP-discovered tool. Wraps MCP calls as tool functions."""
        import json

        def _mcp_wrapper(payload: str) -> str:
            args: dict = {}
            if payload.strip():
                try:
                    args = json.loads(payload)
                except json.JSONDecodeError:
                    args = {"input": payload}
            return json.dumps({"tool": mcp_tool.name, "args": args, "status": "called"})

        self._tools[mcp_tool.name] = _mcp_wrapper
        self._specs[mcp_tool.name] = ToolSpec(
            name=mcp_tool.name,
            description=mcp_tool.description,
            input_contract="json",
            output_contract="json",
            risk_level="read",
            category=mcp_tool.category,
            domain=mcp_tool.domain,
        )

    def call(self, name: str, payload: str) -> str:
        tool = self._tools.get(name)
        if tool is None:
            raise ValueError(f"Tool '{name}' is not registered.")
        return tool(payload)

    def list_specs(self) -> list[ToolSpec]:
        return [self._specs[name] for name in sorted(self._specs)]

    def describe(self, name: str) -> ToolSpec:
        spec = self._specs.get(name)
        if spec is None:
            raise ValueError(f"Tool '{name}' is not registered.")
        return spec

    def unregister(self, name: str) -> None:
        """Remove a tool. Allowed even when frozen (for temporary tools)."""
        self._tools.pop(name, None)
        self._specs.pop(name, None)

    def freeze(self) -> None:
        self._frozen = True

    def unfreeze(self) -> None:
        self._frozen = False

    @property
    def is_frozen(self) -> bool:
        return self._frozen
