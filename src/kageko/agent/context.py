from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from kageko.types import Message

if TYPE_CHECKING:
    from kageko.learning.memory import MemoryManager

logger = logging.getLogger("kageko.agent.context")


@dataclass
class ContextBudget:
    max_tokens: int = 8000
    head_count: int = 2
    tail_count: int = 2


class ContextCompressor:
    """3-layer context compression: tool pruning -> image stripping -> LLM summarization."""

    def __init__(
        self,
        memory: MemoryManager,
        llm,
        budget: ContextBudget | None = None,
    ):
        self.memory = memory
        self.llm = llm
        self.budget = budget or ContextBudget()
        self._previous_summary: str | None = None
        self._consecutive_low_savings: int = 0

    def estimate_tokens(self, messages: list[Message]) -> int:
        total = 0
        for msg in messages:
            total += len(msg.content) // 4
            if msg.reasoning_content:
                total += len(msg.reasoning_content) // 4
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    total += len(json.dumps(tc.args)) // 4
                    total += len(tc.name) // 4
                    total += 4
            total += 4
        return total

    def compress(self, messages: list[Message], current_tokens: int) -> list[Message]:
        """Compress messages using 3-layer strategy."""
        if current_tokens <= self.budget.max_tokens:
            return messages
        if len(messages) <= self.budget.head_count + self.budget.tail_count:
            return messages
        if self._consecutive_low_savings >= 2:
            logger.info("Skipping compression: anti-thrashing")
            self._consecutive_low_savings = 0
            return messages

        head = messages[: self.budget.head_count]
        tail = messages[-self.budget.tail_count :]
        middle = messages[self.budget.head_count : -self.budget.tail_count]
        if not middle:
            return messages

        # Layer 1: Tool output pruning
        middle = self._prune_tool_outputs(middle)

        # Layer 2: Image stripping
        middle = self._strip_images(middle)

        # Layer 3: LLM summarization if still over budget
        estimated = self.estimate_tokens(head + middle + tail)
        if estimated > self.budget.max_tokens:
            summary_parts = []
            for msg in middle:
                preview = msg.content[:100]
                if len(msg.content) > 100:
                    preview += "..."
                summary_parts.append(f"[{msg.role}]: {preview}")
            summary_content = (
                f"[Context compressed: {len(middle)} messages summarized]\n"
                + "\n".join(summary_parts)
            )
            self._previous_summary = summary_content
            middle = [Message(role="system", content=summary_content)]

        compressed = head + middle + tail
        new_tokens = self.estimate_tokens(compressed)
        savings = (current_tokens - new_tokens) / current_tokens if current_tokens > 0 else 0
        if savings < 0.10:
            self._consecutive_low_savings += 1
        else:
            self._consecutive_low_savings = 0

        logger.info("Context compressed: %d -> %d tokens (%.1f%% savings)",
                     current_tokens, new_tokens, savings * 100)
        return compressed

    def _prune_tool_outputs(self, messages: list[Message]) -> list[Message]:
        """Layer 1: Replace old tool results with meaningful summaries."""
        result = []
        for msg in messages:
            if msg.role == "tool" and msg.tool_call_id is not None:
                summary = self.memory.summarize_tool_result(
                    msg.tool_name or "unknown", msg.content,
                )
                result.append(Message(
                    role="tool", content=summary,
                    tool_call_id=msg.tool_call_id, tool_name=msg.tool_name,
                ))
            else:
                result.append(msg)
        return result

    def _strip_images(self, messages: list[Message]) -> list[Message]:
        """Layer 2: Replace old images with text placeholders."""
        result = []
        for msg in messages:
            if msg.images:
                result.append(Message(
                    role=msg.role,
                    content=msg.content + "\n[image removed during compression]",
                    tool_calls=msg.tool_calls,
                    tool_call_id=msg.tool_call_id, tool_name=msg.tool_name,
                    reasoning_content=msg.reasoning_content,
                ))
            else:
                result.append(msg)
        return result
