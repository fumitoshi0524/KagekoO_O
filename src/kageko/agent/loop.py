# src/kageko/agent/loop.py
from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from kageko.agent.context import ContextBudget, ContextCompressor
from kageko.llm import LLMAdapter
from kageko.tools.registry import ToolRegistry
from kageko.types import AgentMode, AgentResult, Message, QAOATrajectory, StreamToken, ToolCall, ToolResult

if TYPE_CHECKING:
    from kageko.agent.guardrails import ToolGuardrail
    from kageko.agent.ttsr import StreamRule
    from kageko.learning.memory import MemoryManager


@dataclass
class AgentContext:
    messages: list[Message] = field(default_factory=list)
    turn_count: int = 0
    tokens_used: int = 0
    trajectory: QAOATrajectory | None = None


class AgentEngine:
    def __init__(
        self,
        config: "AgentConfig | None" = None,
        registry: ToolRegistry | None = None,
        memory: "MemoryManager | None" = None,
        compressor: "ContextCompressor | None" = None,
        guardrails: "ToolGuardrail | None" = None,
        ttsr_rules: list[StreamRule] | None = None,
        # Legacy direct-parameter support
        llm: LLMAdapter | None = None,
        tool_registry: ToolRegistry | None = None,
        permissions: Any = None,
        max_turns: int = 20,
        system_prompt: str = "",
        context_window_size: int = 8000,
        on_tool_start: Any = None,
        on_tool_end: Any = None,
    ):
        from kageko.config import AgentConfig

        # Support both new (config-based) and legacy (direct param) construction
        if config is not None:
            self.config = config
            self.llm = llm or LLMAdapter(config.model, config.api_key, config.base_url)
            self.max_turns = config.max_turns
            self.system_prompt = config.system_prompt
            self.context_window_size = config.context_window_size
        else:
            # Legacy path
            self.config = AgentConfig(
                model=getattr(llm, "model", "") if llm else "",
                max_turns=max_turns,
                system_prompt=system_prompt,
                context_window_size=context_window_size,
            )
            self.llm = llm  # type: ignore[assignment]
            self.max_turns = max_turns
            self.system_prompt = system_prompt
            self.context_window_size = context_window_size

        self.registry = registry or tool_registry or ToolRegistry()
        self.memory = memory
        self.compressor = compressor
        self.guardrails = guardrails
        self.permissions = permissions
        self.on_tool_start = on_tool_start
        self.on_tool_end = on_tool_end

        # TTSR interceptor
        from kageko.agent.ttsr import StreamInterceptor
        self.stream_interceptor = StreamInterceptor(rules=ttsr_rules) if ttsr_rules else None

        # If no compressor was injected, create one from the budget
        if self.compressor is None and self.memory is not None:
            budget = ContextBudget(max_tokens=self.context_window_size)
            self.compressor = ContextCompressor(memory=self.memory, llm=self.llm, budget=budget)

        # Register builtin tools
        from kageko.tools.builtin import register_all
        register_all(self.registry)

    def _prepare_messages(self, message: str | list[Message]) -> list[Message]:
        """Convert input to message list and prepend system prompt if configured."""
        if isinstance(message, str):
            messages = [Message(role="user", content=message)]
        else:
            messages = list(message)

        # Prepend system prompt if configured and not already present
        if self.system_prompt:
            has_system = any(m.role == "system" for m in messages)
            if not has_system:
                messages.insert(0, Message(role="system", content=self.system_prompt))

        return messages

    async def run(self, message: str, context: "AgentContext | None" = None) -> AgentResult:
        """Main agent loop with memory, compression, and guardrails integration."""
        context = context or AgentContext()
        messages = self._prepare_messages(message)
        context.messages = messages

        # Memory prefetch
        if self.memory:
            try:
                memories = await self.memory.prefetch(message, limit=5)
                if memories:
                    memory_text = "\n".join(f"- {m.content}" for m in memories)
                    messages.insert(
                        0,
                        Message(role="system", content=f"[Relevant memories]\n{memory_text}"),
                    )
            except Exception:
                logging.getLogger("kageko.agent.loop").debug("Memory prefetch failed", exc_info=True)

        schemas = self.registry.schemas()

        for turn in range(self.max_turns):
            context.turn_count = turn + 1

            # Check context budget and compress if needed
            if self.compressor:
                estimated = self.compressor.estimate_tokens(messages)
                if estimated > self.context_window_size * 0.8:
                    messages = self.compressor.compress(messages, estimated)

            # Get LLM response
            response = await self.llm.chat(messages, tools=schemas)
            context.tokens_used += response.tokens_used

            assistant_msg = Message(
                role="assistant",
                content=response.content or "",
                tool_calls=response.tool_calls,
            )
            messages.append(assistant_msg)

            if not response.has_tool_calls():
                # Memory sync after completion
                if self.memory:
                    try:
                        await self.memory.sync_turn(type("Turn", (), {
                            "user": message,
                            "assistant": response.content,
                        })())
                    except Exception:
                        logging.getLogger("kageko.agent.loop").debug("Memory sync failed", exc_info=True)

                return AgentResult(
                    answer=response.content,
                    turn_count=turn + 1,
                    tokens_used=context.tokens_used,
                    messages=messages,
                )

            for tc in response.tool_calls:
                # Guardrails check
                if self.guardrails:
                    from kageko.agent.guardrails import ToolCallSignature
                    sig = ToolCallSignature(tc.name, tc.args)
                    decision = self.guardrails.check(sig)
                    if decision.action == "block":
                        result = ToolResult(
                            tool_call_id=tc.id,
                            content=decision.message,
                            is_error=True,
                        )
                        messages.append(result.to_message())
                        continue
                    elif decision.action == "halt":
                        return AgentResult(
                            answer=f"Stopped: {decision.message}",
                            turn_count=turn + 1,
                            tokens_used=context.tokens_used,
                            messages=messages,
                        )

                # Permission check (legacy support)
                if self.permissions:
                    from kageko.agent.permissions import Decision
                    decision = await self.permissions.check(tc)
                    if decision == Decision.DENY:
                        result = ToolResult(
                            tool_call_id=tc.id,
                            content=f"[DENIED] Tool '{tc.name}' blocked by security policy",
                            is_error=True,
                        )
                        messages.append(result.to_message())
                        if self.on_tool_end:
                            await self.on_tool_end(tc.name, result.content, result.is_error)
                        continue
                    if decision == Decision.EXECUTE_IN_SANDBOX:
                        result = ToolResult(
                            tool_call_id=tc.id,
                            content="[SANDBOX ERROR] Sandbox execution is not available.",
                            is_error=True,
                        )
                        messages.append(result.to_message())
                        if self.on_tool_end:
                            await self.on_tool_end(tc.name, result.content, result.is_error)
                        continue

                if self.on_tool_start:
                    await self.on_tool_start(tc.name, tc.args)

                try:
                    content = await self.registry.execute(tc.name, tc.args)
                    result = ToolResult(tool_call_id=tc.id, content=content)
                except Exception as e:
                    result = ToolResult(
                        tool_call_id=tc.id,
                        content=f"[ERROR] {type(e).__name__}: {e}",
                        is_error=True,
                    )

                if self.on_tool_end:
                    await self.on_tool_end(tc.name, result.content, result.is_error)

                messages.append(result.to_message())

        return AgentResult(
            answer="(max turns reached)",
            turn_count=self.max_turns,
            tokens_used=context.tokens_used,
            messages=messages,
        )

    async def run_stream(
        self,
        message: str | list[Message],
        mode: AgentMode = AgentMode.TOOL_USE,
        ttsr_rules: list | None = None,
    ) -> AsyncIterator:
        """Stream agent responses token-by-token, optionally through TTSR interceptor."""
        from kageko.agent.ttsr import Correction, StreamInterceptor

        messages = self._prepare_messages(message)
        schemas = self.registry.schemas()

        for _turn in range(self.max_turns):
            if self.compressor:
                estimated = self.compressor.estimate_tokens(messages)
                if estimated > self.context_window_size * 0.8:
                    messages = self.compressor.compress(messages, estimated)

            token_stream = self.llm.chat_stream(messages, tools=schemas)

            if ttsr_rules:
                interceptor = StreamInterceptor(rules=ttsr_rules)
                tool_tokens: list = []
                full_content = ""
                correction_fired = False

                text_gen = self._text_generator(token_stream, tool_tokens)
                async for item in interceptor.intercept(text_gen):
                    if isinstance(item, Correction):
                        yield item
                        correction_fired = True
                        break
                    full_content += item
                    yield StreamToken(text=item)

                if correction_fired:
                    return

                if tool_tokens:
                    tool_calls = self._reconstruct_tool_calls(tool_tokens)
                    messages.append(Message(
                        role="assistant",
                        content=full_content,
                        tool_calls=tool_calls,
                    ))
                    for tc in tool_calls:
                        if self.guardrails:
                            from kageko.agent.guardrails import ToolCallSignature
                            sig = ToolCallSignature(tc.name, tc.args)
                            decision = self.guardrails.check(sig)
                            if decision.action in ("block", "halt"):
                                messages.append(Message(
                                    role="tool",
                                    content=decision.message,
                                    tool_call_id=tc.id,
                                ))
                                continue
                        try:
                            content = await self.registry.execute(tc.name, tc.args)
                            messages.append(Message(role="tool", content=content, tool_call_id=tc.id))
                        except Exception as e:
                            messages.append(Message(
                                role="tool",
                                content=f"[ERROR] {type(e).__name__}: {e}",
                                tool_call_id=tc.id,
                            ))
                    continue

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
            for tc in tool_calls:
                try:
                    content = await self.registry.execute(tc.name, tc.args)
                    messages.append(Message(role="tool", content=content, tool_call_id=tc.id))
                except Exception as e:
                    messages.append(Message(
                        role="tool",
                        content=f"[ERROR] {type(e).__name__}: {e}",
                        tool_call_id=tc.id,
                    ))
            continue

        yield StreamToken(text="(max turns reached)")

    async def _text_generator(self, token_stream, tool_tokens: list) -> AsyncIterator[str]:
        """Extract text tokens for TTSR consumption while collecting tool call tokens."""
        async for tok in token_stream:
            if tok.is_tool_call:
                tool_tokens.append(tok)
            elif tok.text:
                yield tok.text

    def _reconstruct_tool_calls(self, tokens: list) -> list[ToolCall]:
        """Reconstruct tool calls from streamed tool call tokens."""
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
            except json.JSONDecodeError as e:
                logging.getLogger("kageko.agent.loop").warning(
                    "Failed to parse tool call args for %s: %s (raw: %r)",
                    data["name"], e, data["args_str"]
                )
                args = {}
            result.append(ToolCall(id=tc_id, name=data["name"], args=args))
        return result
