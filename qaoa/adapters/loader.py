"""Auto-load generated tools from the tools directory."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

from .tools import ToolRegistry, ToolSpec


class GeneratedToolPack:
    """Loads pipeline-generated tool modules from a directory."""

    def __init__(self, tools_dir: str | Path | None = None) -> None:
        self.tools_dir = Path(tools_dir) if tools_dir else None

    def register(self, registry: ToolRegistry) -> None:
        if self.tools_dir is None or not self.tools_dir.exists():
            return
        for path in sorted(self.tools_dir.glob("*.py")):
            if path.name.startswith("_"):
                continue
            self._load_module(path, registry)

    def _load_module(self, path: Path, registry: ToolRegistry) -> None:
        spec = importlib.util.spec_from_file_location(path.stem, path)
        if spec is None or spec.loader is None:
            return
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        tool_spec = getattr(module, "TOOL_SPEC", None)
        run_fn = getattr(module, "run", None)
        if tool_spec is None or run_fn is None:
            return

        name = str(tool_spec.get("name", path.stem))
        description = str(tool_spec.get("description", ""))
        category = str(tool_spec.get("category", ""))
        domain = str(tool_spec.get("domain", ""))
        schema = tool_spec.get("schema", {})
        risk_level = str(tool_spec.get("risk_level", "read"))
        tags_val = tool_spec.get("tags", ())
        tags: tuple[str, ...] = ()
        if isinstance(tags_val, (list, tuple)):
            tags = tuple(str(t) for t in tags_val)

        input_contract = self._schema_to_contract(schema)

        registry.register(
            name,
            lambda payload, fn=run_fn: str(fn(payload)),
            description=description,
            input_contract=input_contract,
            output_contract="tool execution result as string",
            tags=tags,
            risk_level=risk_level,
            category=category,
            domain=domain,
        )

    @staticmethod
    def _schema_to_contract(schema: dict[str, Any]) -> str:
        if not schema:
            return "plain text payload"
        try:
            return json.dumps(schema, ensure_ascii=False)
        except (TypeError, ValueError):
            return "plain text payload"
