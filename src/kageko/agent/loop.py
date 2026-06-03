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
            self._config = config
            self.llm = llm or LLMAdapter(config.model, config.api_key, config.base_url)
        else:
            # Legacy path
            self._config = AgentConfig(
                model=getattr(llm, "model", "") if llm else "",
                max_turns=max_turns,
                system_prompt=system_prompt,
                context_window_size=context_window_size,
            )
            self.llm = llm  # type: ignore[assignment]

        self.registry = registry or tool_registry or ToolRegistry()
        self.memory = memory
        self._compressor = compressor
        self.guardrails = guardrails
        self.permissions = permissions
        self.on_tool_start = on_tool_start
        self.on_tool_end = on_tool_end

        # TTSR interceptor
        from kageko.agent.ttsr import StreamInterceptor
        self.stream_interceptor = StreamInterceptor(rules=ttsr_rules) if ttsr_rules else None
        self.last_tokens: int = 0

        # If no compressor was injected, create one from the budget
        if self._compressor is None and self.memory is not None:
            budget = ContextBudget(max_tokens=self.context_window_size)
            self._compressor = ContextCompressor(memory=self.memory, llm=self.llm, budget=budget)

    # ---- config-aware properties (read dynamically so /config changes apply immediately) ----

    @property
    def max_turns(self) -> int:
        return self._config.max_turns

    @max_turns.setter
    def max_turns(self, value: int) -> None:
        self._config.max_turns = value

    @property
    def system_prompt(self) -> str:
        return self._config.system_prompt

    @system_prompt.setter
    def system_prompt(self, value: str) -> None:
        self._config.system_prompt = value

    @property
    def context_window_size(self) -> int:
        """Return effective context window size. 0 means unlimited."""
        return self._config.get_context_window_size()

    @context_window_size.setter
    def context_window_size(self, value: int) -> None:
        self._config.context_window_size = value

    @property
    def compressor(self):
        """Return the compressor (may be None)."""
        return self._compressor

    @compressor.setter
    def compressor(self, value):
        self._compressor = value

    def reload_config(self) -> None:
        """Called after external config changes (e.g. /config slash command).
        Updates compressor budget if context_window_size changed."""
        if self._compressor is not None:
            self._compressor.budget.max_tokens = self.context_window_size

    async def sync_memory(self, user_text: str, assistant_text: str, session_id: str = "") -> None:
        """Persist a conversation turn to long-term memory.
        Called by the CLI after each complete user↔assistant exchange.
        """
        if not self.memory:
            return
        try:
            Turn = type("Turn", (), {})  # noqa: N806
            turn = Turn()
            turn.user = user_text
            turn.assistant = assistant_text
            turn.session_id = session_id
            await self.memory.sync_turn(turn)
        except Exception:
            logging.getLogger("kageko.agent.loop").debug("Memory sync failed", exc_info=True)

        # Register builtin tools
        from kageko.tools.builtin import register_all
        register_all(self.registry)

    async def _check_tool_allowed(self, tc: ToolCall) -> str | None:
        """Check guardrails and permissions for a tool call.

        Returns an error message string if the tool should be blocked,
        or None if execution should proceed.
        """
        # Guardrails check
        if self.guardrails:
            from kageko.agent.guardrails import ToolCallSignature
            sig = ToolCallSignature(tc.name, tc.args)
            decision = self.guardrails.check(sig)
            if decision.action == "block":
                return decision.message
            if decision.action == "halt":
                return f"HALT: {decision.message}"

        # Permission check
        if self.permissions:
            from kageko.agent.permissions import Decision
            decision = await self.permissions.check(tc)
            if decision == Decision.DENY:
                return f"[DENIED] Tool '{tc.name}' blocked by security policy"
            if decision == Decision.EXECUTE_IN_SANDBOX:
                return "[SANDBOX ERROR] Sandbox execution is not available."

        return None

    def _prepare_messages(self, message: str | list[Message]) -> list[Message]:
        """Convert input to message list and prepend system prompt if configured.

        When given a list, the caller's list is used directly (not copied) so
        that tool results, assistant messages, and reasoning_content appended
        by the agent loop are visible to the caller for subsequent turns.
        """
        if isinstance(message, str):
            messages: list[Message] = [Message(role="user", content=message)]
        else:
            messages = message

        # Prepend system prompt if configured and not already present
        if self.system_prompt:
            has_system = any(m.role == "system" for m in messages)
            if not has_system:
                messages.insert(0, Message(role="system", content=self.system_prompt))

        return messages

    async def run(self, message: str | list[Message], context: "AgentContext | None" = None, mode: AgentMode = AgentMode.TOOL_USE) -> AgentResult:
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

        turn = 0
        while self.max_turns == 0 or turn < self.max_turns:
            turn += 1
            context.turn_count = turn

            # Check context budget and compress if needed
            # context_window_size == 0 means unlimited — skip compression entirely
            cw_size = self.context_window_size
            if cw_size > 0 and self.compressor:
                estimated = self.compressor.estimate_tokens(messages)
                if estimated > cw_size * 0.8:
                    messages = self.compressor.compress(messages, estimated)

            # Get LLM response
            response = await self.llm.chat(messages, tools=schemas)
            context.tokens_used += response.tokens_used

            assistant_msg = Message(
                role="assistant",
                content=response.content or "",
                tool_calls=response.tool_calls,
                reasoning_content=response.reasoning_content,
            )
            messages.append(assistant_msg)

            if not response.has_tool_calls():
                return AgentResult(
                    answer=response.content,
                    turn_count=turn,
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
                        return AgentResult(
                            answer=response.content or f"[BLOCKED] {decision.message}",
                            turn_count=turn,
                            tokens_used=context.tokens_used,
                            messages=messages,
                        )
                    elif decision.action == "halt":
                        return AgentResult(
                            answer=f"Stopped: {decision.message}",
                            turn_count=turn,
                            tokens_used=context.tokens_used,
                            messages=messages,
                        )

                # Permission check
                if self.permissions:
                    from kageko.agent.permissions import Decision
                    decision = await self.permissions.check(tc)
                    if decision == Decision.DENY:
                        # User denied — return to conversation immediately.
                        return AgentResult(
                            answer=response.content or "(tool execution denied by user)",
                            turn_count=turn,
                            tokens_used=context.tokens_used,
                            messages=messages,
                        )
                    if decision == Decision.EXECUTE_IN_SANDBOX:
                        result = ToolResult(
                            tool_call_id=tc.id,
                            content="[SANDBOX ERROR] Sandbox execution is not available.",
                            is_error=True,
                            tool_name=tc.name,
                        )
                        messages.append(result.to_message())
                        if self.on_tool_end:
                            await self.on_tool_end(tc.name, result.content, result.is_error)
                        continue

                if self.on_tool_start:
                    await self.on_tool_start(tc.name, tc.args)

                try:
                    content = await self.registry.execute(tc.name, tc.args)
                    result = ToolResult(tool_call_id=tc.id, content=content, tool_name=tc.name)
                except Exception as e:
                    if self.guardrails:
                        from kageko.agent.guardrails import ToolCallSignature
                        self.guardrails.check(ToolCallSignature(tc.name, tc.args), failed=True)
                    result = ToolResult(
                        tool_call_id=tc.id,
                        content=f"[ERROR] {type(e).__name__}: {e}",
                        is_error=True,
                        tool_name=tc.name,
                    )

                if self.on_tool_end:
                    await self.on_tool_end(tc.name, result.content, result.is_error)

                messages.append(result.to_message())

        return AgentResult(
            answer="(max turns reached)",
            turn_count=turn,
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

        total_tokens = 0
        _turn = 0
        while self.max_turns == 0 or _turn < self.max_turns:
            _turn += 1
            # context_window_size == 0 means unlimited — skip compression entirely
            cw_size = self.context_window_size
            if cw_size > 0 and self.compressor:
                estimated = self.compressor.estimate_tokens(messages)
                if estimated > cw_size * 0.8:
                    messages = self.compressor.compress(messages, estimated)

            token_stream = self.llm.chat_stream(messages, tools=schemas)

            if ttsr_rules:
                interceptor = StreamInterceptor(rules=ttsr_rules)
                tool_tokens: list = []
                full_content = ""
                reasoning_parts: list[str] = []
                tokens_list: list[int] = []
                correction_fired = False

                text_gen = self._text_generator(token_stream, tool_tokens, reasoning_parts, tokens_list)
                async for item in interceptor.intercept(text_gen):
                    if isinstance(item, Correction):
                        yield item
                        correction_fired = True
                        break
                    full_content += item
                    yield StreamToken(text=item)

                if correction_fired:
                    self.last_tokens = total_tokens + sum(tokens_list)
                    return

                total_tokens += sum(tokens_list)
                if tool_tokens:
                    tool_calls = self._reconstruct_tool_calls(tool_tokens)
                    messages.append(Message(
                        role="assistant",
                        content=full_content,
                        tool_calls=tool_calls,
                        reasoning_content="".join(reasoning_parts) or None,
                    ))
                    for tc in tool_calls:
                        error = await self._check_tool_allowed(tc)
                        if error:
                            is_stop = error.startswith("HALT:") or error.startswith("[DENIED]")
                            messages.append(Message(
                                role="tool",
                                content=error,
                                tool_call_id=tc.id,
                                tool_name=tc.name,
                            ))
                            if is_stop:
                                # User denied or guardrails halted — return to conversation.
                                if error.startswith("[DENIED]"):
                                    yield StreamToken(text=f"\n[DENIED] Returning to conversation.\n")
                                self.last_tokens = total_tokens
                                return
                            continue
                        try:
                            content = await self.registry.execute(tc.name, tc.args)
                            messages.append(Message(role="tool", content=content, tool_call_id=tc.id, tool_name=tc.name))
                        except Exception as e:
                            if self.guardrails:
                                from kageko.agent.guardrails import ToolCallSignature
                                self.guardrails.check(ToolCallSignature(tc.name, tc.args), failed=True)
                            messages.append(Message(
                                role="tool",
                                content=f"[ERROR] {type(e).__name__}: {e}",
                                tool_call_id=tc.id,
                                tool_name=tc.name,
                            ))
                    continue

                messages.append(Message(
                    role="assistant",
                    content=full_content,
                    reasoning_content="".join(reasoning_parts) or None,
                ))
                self.last_tokens = total_tokens
                return

            full_content = ""
            tool_tokens: list = []
            finish_reason = ""
            reasoning_parts: list[str] = []

            async for tok in token_stream:
                if tok.is_tool_call:
                    tool_tokens.append(tok)
                elif tok.text:
                    full_content += tok.text
                    yield tok
                if tok.reasoning_content:
                    reasoning_parts.append(tok.reasoning_content)
                if tok.finish_reason:
                    finish_reason = tok.finish_reason
                if tok.tokens_used:
                    total_tokens += tok.tokens_used

            if finish_reason == "stop" or not tool_tokens:
                messages.append(Message(
                    role="assistant",
                    content=full_content,
                    reasoning_content="".join(reasoning_parts) or None,
                ))
                self.last_tokens = total_tokens
                return

            tool_calls = self._reconstruct_tool_calls(tool_tokens)
            messages.append(Message(
                role="assistant",
                content=full_content,
                tool_calls=tool_calls,
                reasoning_content="".join(reasoning_parts) or None,
            ))
            for tc in tool_calls:
                error = await self._check_tool_allowed(tc)
                if error:
                    is_stop = error.startswith("HALT:") or error.startswith("[DENIED]")
                    messages.append(Message(
                        role="tool",
                        content=error,
                        tool_call_id=tc.id,
                        tool_name=tc.name,
                    ))
                    if is_stop:
                        if error.startswith("[DENIED]"):
                            yield StreamToken(text=f"\n[DENIED] Returning to conversation.\n")
                        self.last_tokens = total_tokens
                        return
                    continue
                if self.on_tool_start:
                    await self.on_tool_start(tc.name, tc.args)
                tool_ok = False
                tool_result = ""
                try:
                    tool_result = await self.registry.execute(tc.name, tc.args)
                    tool_ok = True
                    messages.append(Message(role="tool", content=tool_result, tool_call_id=tc.id, tool_name=tc.name))
                except Exception as e:
                    if self.guardrails:
                        from kageko.agent.guardrails import ToolCallSignature
                        self.guardrails.check(ToolCallSignature(tc.name, tc.args), failed=True)
                    tool_result = f"[ERROR] {type(e).__name__}: {e}"
                    messages.append(Message(
                        role="tool",
                        content=tool_result,
                        tool_call_id=tc.id,
                        tool_name=tc.name,
                    ))
                if self.on_tool_end:
                    await self.on_tool_end(tc.name, tool_result, not tool_ok)
            continue

        self.last_tokens = total_tokens
        yield StreamToken(text="(max turns reached)")

    async def _text_generator(self, token_stream, tool_tokens: list, reasoning_parts: list | None = None, tokens_used: list | None = None) -> AsyncIterator[str]:
        """Extract text tokens for TTSR consumption while collecting tool call tokens."""
        async for tok in token_stream:
            if tok.is_tool_call:
                tool_tokens.append(tok)
            elif tok.text:
                yield tok.text
            if reasoning_parts is not None and tok.reasoning_content:
                reasoning_parts.append(tok.reasoning_content)
            if tokens_used is not None and tok.tokens_used:
                tokens_used.append(tok.tokens_used)

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
            if not data["name"]:
                continue  # skip phantom entries from orphan continuation chunks
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
