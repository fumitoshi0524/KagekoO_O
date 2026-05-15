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
        if self._frozen:
            raise RuntimeError("Tool registry is frozen.")
        self._tools[name] = tool
        self._specs[name] = ToolSpec(
            name=name, description=description,
            input_contract=input_contract, output_contract=output_contract,
            tags=tags, risk_level=risk_level, category=category, domain=domain,
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

    def freeze(self) -> None:
        self._frozen = True

    @property
    def is_frozen(self) -> bool:
        return self._frozen
