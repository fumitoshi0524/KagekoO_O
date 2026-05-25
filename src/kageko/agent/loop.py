# src/kageko/agent/loop.py
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from kageko.agent.permissions import Decision, PermissionPipeline
from kageko.llm import LLMAdapter
from kageko.tools.registry import ToolRegistry
from kageko.types import AgentMode, AgentResult, Message, QAOATrajectory, ToolCall, ToolResult


@dataclass
class AgentContext:
    messages: list[Message] = field(default_factory=list)
    turn_count: int = 0
    tokens_used: int = 0
    trajectory: QAOATrajectory | None = None


class AgentEngine:
    def __init__(
        self,
        llm: LLMAdapter,
        tool_registry: ToolRegistry,
        permissions: PermissionPipeline,
        max_turns: int = 20,
    ):
        self.llm = llm
        self.tool_registry = tool_registry
        self.permissions = permissions
        self.max_turns = max_turns

    async def run(self, message: str, mode: AgentMode = AgentMode.TOOL_USE) -> AgentResult:
        if mode == AgentMode.QAOA:
            return await self._qaoa_loop(message)
        return await self._tool_use_loop(message)

    async def _tool_use_loop(self, message: str) -> AgentResult:
        ctx = AgentContext(messages=[Message(role="user", content=message)])
        return await self._run_loop(ctx, record_trajectory=False)

    async def _qaoa_loop(self, message: str) -> AgentResult:
        trajectory = QAOATrajectory(query=message)
        ctx = AgentContext(
            messages=[Message(role="user", content=message)],
            trajectory=trajectory,
        )
        return await self._run_loop(ctx, record_trajectory=True)

    async def _run_loop(self, ctx: AgentContext, record_trajectory: bool) -> AgentResult:
        schemas = self.tool_registry.schemas()

        while ctx.turn_count < self.max_turns:
            ctx.turn_count += 1
            response = await self.llm.chat(ctx.messages, tools=schemas)
            ctx.tokens_used += response.tokens_used

            if not response.has_tool_calls():
                ctx.messages.append(Message(role="assistant", content=response.content))
                if ctx.trajectory:
                    ctx.trajectory.set_answer(response.content)
                return AgentResult(
                    answer=response.content,
                    turn_count=ctx.turn_count,
                    tokens_used=ctx.tokens_used,
                    trajectory=ctx.trajectory,
                )

            results = await self._execute_tool_calls(response.tool_calls)
            ctx.messages.append(Message(
                role="assistant",
                content=response.content or "",
                tool_calls=response.tool_calls,
            ))
            for result in results:
                ctx.messages.append(result.to_message())
                if record_trajectory and ctx.trajectory:
                    matching_call = next(
                        (tc for tc in response.tool_calls if tc.id == result.tool_call_id),
                        None,
                    )
                    if matching_call:
                        ctx.trajectory.step(matching_call, result)

        return AgentResult(
            answer="(max turns reached)",
            turn_count=ctx.turn_count,
            tokens_used=ctx.tokens_used,
            trajectory=ctx.trajectory,
        )

    async def _execute_tool_calls(self, tool_calls: list[ToolCall]) -> list[ToolResult]:
        """Execute tool calls in parallel using asyncio.gather."""

        async def _execute_one(tc: ToolCall) -> ToolResult:
            decision = await self.permissions.check(tc)
            if decision == Decision.DENY:
                return ToolResult(
                    tool_call_id=tc.id,
                    content=f"[DENIED] Tool '{tc.name}' blocked by security policy",
                    is_error=True,
                )
            if decision == Decision.EXECUTE_IN_SANDBOX:
                return ToolResult(
                    tool_call_id=tc.id,
                    content="[SANDBOX] Not yet implemented",
                    is_error=True,
                )
            try:
                content = await self.tool_registry.execute(tc.name, tc.args)
                return ToolResult(tool_call_id=tc.id, content=content)
            except Exception as e:
                return ToolResult(
                    tool_call_id=tc.id,
                    content=f"[ERROR] {type(e).__name__}: {e}",
                    is_error=True,
                )

        results = await asyncio.gather(*[_execute_one(tc) for tc in tool_calls])
        return list(results)
