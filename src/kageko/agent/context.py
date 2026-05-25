from __future__ import annotations

from kageko.types import Message


class ContextCompressor:
    """Compress conversation context when approaching token limits."""

    def __init__(self, max_tokens: int = 8000, head_count: int = 2, tail_count: int = 2):
        self.max_tokens = max_tokens
        self.head_count = head_count
        self.tail_count = tail_count

    def estimate_tokens(self, messages: list[Message]) -> int:
        """Rough token estimation: ~4 characters per token."""
        total = 0
        for msg in messages:
            total += len(msg.content) // 4
            total += 4
        return total

    def compress(self, messages: list[Message], current_tokens: int) -> list[Message]:
        """Compress messages if over budget. Preserves head and tail."""
        if current_tokens <= self.max_tokens:
            return messages

        if len(messages) <= self.head_count + self.tail_count:
            return messages

        head = messages[: self.head_count]
        tail = messages[-self.tail_count :]
        middle = messages[self.head_count : -self.tail_count]

        if not middle:
            return messages

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
        summary = Message(role="system", content=summary_content)

        return head + [summary] + tail
