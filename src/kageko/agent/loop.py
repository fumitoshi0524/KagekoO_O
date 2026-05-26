# src/kageko/agent/loop.py
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from kageko.agent.permissions import Decision, PermissionPipeline
from kageko.llm import LLMAdapter
from kageko.tools.registry import ToolRegistry
from kageko.types import AgentMode, AgentResult, Message, QAOATrajectory, StreamToken, ToolCall, ToolResult


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

    async def run_stream(
        self,
        message: str,
        mode: AgentMode = AgentMode.TOOL_USE,
        ttsr_rules: list | None = None,
    ) -> AsyncIterator:
        """Stream agent responses token-by-token, optionally through TTSR interceptor."""
        from kageko.agent.ttsr import Correction, StreamInterceptor

        messages = [Message(role="user", content=message)]
        schemas = self.tool_registry.schemas()

        for _turn in range(self.max_turns):
            token_stream = self.llm.chat_stream(messages, tools=schemas)

            if ttsr_rules:
                interceptor = StreamInterceptor(rules=ttsr_rules)
                text_stream = self._extract_text(token_stream)
                full_content = ""
                async for item in interceptor.intercept(text_stream):
                    if isinstance(item, Correction):
                        yield item
                        return
                    full_content += item
                    yield StreamToken(text=item)
                messages.append(Message(role="assistant", content=full_content))
                return

            full_content = ""
            tool_tokens: list = []
            finish_reason = ""

            async for tok in token_stream:
                if tok.is_tool_call:
                    tool_tokens.append(tok)
                elif tok.text:
                    full_content += tok.text
                    yield tok
                if tok.finish_reason:
                    finish_reason = tok.finish_reason

            if finish_reason == "stop" or not tool_tokens:
                messages.append(Message(role="assistant", content=full_content))
                return

            tool_calls = self._reconstruct_tool_calls(tool_tokens)
            messages.append(Message(role="assistant", content=full_content, tool_calls=tool_calls))
            results = await self._execute_tool_calls(tool_calls)
            for result in results:
                messages.append(result.to_message())
            continue

        yield StreamToken(text="(max turns reached)")

    async def _extract_text(self, token_stream) -> AsyncIterator[str]:
        """Extract text from StreamToken stream for TTSR consumption."""
        async for tok in token_stream:
            yield tok.text

    def _reconstruct_tool_calls(self, tokens: list) -> list[ToolCall]:
        """Reconstruct tool calls from streamed tool call tokens."""
        import json
        from collections import defaultdict

        by_id: dict[str, dict] = {}
        for tok in tokens:
            if tok.tool_call_id not in by_id:
                by_id[tok.tool_call_id] = {"name": "", "args_str": ""}
            if tok.tool_name:
                by_id[tok.tool_call_id]["name"] = tok.tool_name
            if tok.tool_args:
                by_id[tok.tool_call_id]["args_str"] += tok.tool_args

        result = []
        for tc_id, data in by_id.items():
            try:
                args = json.loads(data["args_str"]) if data["args_str"] else {}
            except json.JSONDecodeError:
                args = {}
            result.append(ToolCall(id=tc_id, name=data["name"], args=args))
        return result
