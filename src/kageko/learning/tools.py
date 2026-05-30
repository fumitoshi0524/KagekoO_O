from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from kageko.types import Message

logger = logging.getLogger("kageko.learning.tools")


@dataclass
class GeneratedTool:
    name: str
    category: str
    description: str
    parameters: dict
    implementation: str
    source: str = "generated"
    enabled: bool = True


class ToolGenerator:
    """Layer 2: Periodic QAOA-driven tool generation from repeated trajectory patterns."""

    def __init__(self, db, llm, registry=None, curator=None):
        self.db = db
        self.llm = llm
        self.registry = registry
        self.curator = curator

    async def analyze_and_generate(self) -> dict | None:
        """Analyze recent trajectories and generate a tool if a repeated pattern is found."""
        trajectories = await self.db.get_recent_trajectories(days=30)
        if not trajectories:
            return None

        # Find repeated action patterns (>=3 occurrences)
        pattern_counts: dict[str, int] = {}
        for traj in trajectories:
            for action in traj.get("actions", []):
                key = f"{action['tool']}:{json.dumps(action.get('args', {}), sort_keys=True)}"
                pattern_counts[key] = pattern_counts.get(key, 0) + 1

        repeated = {k: v for k, v in pattern_counts.items() if v >= 3}
        if not repeated:
            return None

        # Ask LLM to generate tool from the most repeated pattern
        top_pattern = max(repeated, key=repeated.get)
        prompt = (
            f"This tool call pattern appeared {repeated[top_pattern]} times in recent work:\n"
            f"Pattern: {top_pattern}\n\n"
            "Generate a standalone tool definition as JSON with: name, category, description, "
            "parameters (JSON Schema), and implementation (Python function body).\n"
            "Return ONLY valid JSON."
        )
        response = await self.llm.chat([Message(role="user", content=prompt)])
        try:
            tool_def = json.loads(response.content)
        except json.JSONDecodeError:
            logger.warning("LLM returned invalid JSON for tool generation")
            return None

        # Safety audit via curator
        if self.curator and not await self.curator.audit_tool_safety(
            tool_def.get("name", "unknown"),
            tool_def.get("implementation", ""),
        ):
            logger.warning("Generated tool %s failed safety audit", tool_def.get("name"))
            return None

        # Save to DB
        await self.db.write_with_retry(
            "INSERT OR REPLACE INTO tools (name, schema_json, implementation, category, source) "
            "VALUES (?, ?, ?, ?, 'generated')",
            (
                tool_def["name"],
                json.dumps(tool_def.get("parameters", {})),
                tool_def.get("implementation", ""),
                tool_def.get("category", "utility"),
            ),
        )

        # Hot load into registry
        if self.registry:
            self.hot_load(tool_def)

        return tool_def

    def hot_load(self, tool_def: dict) -> None:
        """Dynamically register a generated tool into the ToolRegistry."""
        if not self.registry:
            return

        from kageko.tools.registry import Tool

        impl_code = tool_def.get("implementation", "")

        def _make_handler(code: str):
            def handler(**kwargs):
                local_ns = {}
                exec(code, {}, local_ns)
                if "execute" in local_ns:
                    return local_ns["execute"](**kwargs)
                return "[generated tool: no execute function]"
            return handler

        tool = Tool(
            name=tool_def["name"],
            description=tool_def.get("description", ""),
            parameters=tool_def.get("parameters", {"type": "object", "properties": {}}),
            handler=_make_handler(impl_code),
            category=tool_def.get("category", "utility"),
        )
        self.registry.register(tool)
        logger.info("Hot-loaded generated tool: %s", tool_def["name"])
