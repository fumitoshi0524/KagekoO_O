"""Subagent delegation — spawn isolated agent instances for parallel tasks."""
from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass
from typing import Any

from kageko.types import AgentMode, Message

logger = logging.getLogger(__name__)


@dataclass
class SubagentResult:
    task_id: str
    answer: str
    turn_count: int = 0
    tokens_used: int = 0
    is_error: bool = False


class DelegationEngine:
    """Manages subagent spawning with isolated contexts."""

    def __init__(self, parent_engine: Any) -> None:
        self.parent = parent_engine

    async def delegate(
        self,
        task: str,
        mode: AgentMode = AgentMode.TOOL_USE,
        max_turns: int = 10,
        allowed_tools: list[str] | None = None,
    ) -> SubagentResult:
        """Spawn a subagent for the given task."""
        import kageko.agent.loop as loop_mod
        from kageko.agent.permissions import PermissionPipeline, SecurityMode
        from kageko.tools.registry import ToolRegistry

        task_id = uuid.uuid4().hex[:12]

        # Create filtered registry if allowed_tools specified
        if allowed_tools:
            sub_registry = ToolRegistry()
            for name in self.parent.tool_registry.list_names():
                if name in allowed_tools:
                    tool = self.parent.tool_registry.get(name)
                    sub_registry.register(tool)
        else:
            sub_registry = self.parent.tool_registry

        # Inherit parent's security mode instead of always using PERMISSIVE
        parent_mode = SecurityMode.PERMISSIVE
        if self.parent.permissions is not None:
            parent_mode = self.parent.permissions.mode
        sub_engine = loop_mod.AgentEngine(
            llm=self.parent.llm,
            tool_registry=sub_registry,
            permissions=PermissionPipeline(mode=parent_mode),
            max_turns=max_turns,
            system_prompt=f"You are a subagent working on: {task}\nComplete this task concisely and report back.",
        )

        try:
            result = await sub_engine.run([Message(role="user", content=task)], mode=mode)
            return SubagentResult(
                task_id=task_id,
                answer=result.answer,
                turn_count=result.turn_count,
                tokens_used=result.tokens_used,
            )
        except Exception as e:
            logger.exception("Subagent failed for task: %s", task)
            return SubagentResult(
                task_id=task_id,
                answer=f"Subagent failed: {e}",
                is_error=True,
            )

    async def delegate_parallel(
        self,
        tasks: list[str],
        **kwargs: Any,
    ) -> list[SubagentResult]:
        """Spawn multiple subagents in parallel."""
        results = await asyncio.gather(
            *[self.delegate(task, **kwargs) for task in tasks],
            return_exceptions=True,
        )
        return [
            r if isinstance(r, SubagentResult) else SubagentResult(
                task_id="", answer=str(r), is_error=True,
            )
            for r in results
        ]


def make_delegate_handler(engine: Any) -> Any:
    """Create a delegate tool handler bound to the given engine."""
    async def delegate_handler(arguments: dict) -> str:
        task = arguments.get("task", "")
        allowed_tools = arguments.get("allowed_tools", None)
        max_turns = arguments.get("max_turns", 10)

        if not task:
            return "[ERROR] No task provided"

        delegation = DelegationEngine(engine)
        result = await delegation.delegate(
            task=task,
            max_turns=max_turns,
            allowed_tools=allowed_tools,
        )

        if result.is_error:
            return f"[ERROR] {result.answer}"
        return f"[Subagent {result.task_id}] {result.answer}"

    return delegate_handler
