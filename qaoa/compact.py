"""Context auto-compaction — LLM-based summarization of old messages."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

# Rough token estimate: ~4 chars per token for English text
CHARS_PER_TOKEN = 4


@dataclass(slots=True, kw_only=True)
class ContextCompactor:
    """Summarizes old messages to stay within context window limits."""

    max_context_chars: int = 100_000
    compaction_threshold: int = 80_000  # trigger when context exceeds this
    keep_recent_count: int = 10  # keep last N messages uncompressed
    max_summary_chars: int = 5000

    def should_compact(self, messages: list[dict]) -> bool:
        total = sum(len(json.dumps(m, ensure_ascii=False)) for m in messages)
        return total > self.compaction_threshold

    def compact(self, messages: list[dict], llm) -> list[dict]:
        """Return compacted messages: summary + recent messages."""
        if len(messages) <= self.keep_recent_count:
            return messages

        recent = messages[-self.keep_recent_count:]
        old = messages[:-self.keep_recent_count]

        summary = self._generate_summary(old, llm)
        boundary_marker = {
            "role": "system",
            "content": f"[Context compacted: previous {len(old)} messages summarized below]\n\n{summary}",
        }
        return [boundary_marker] + recent

    def _generate_summary(self, messages: list[dict], llm) -> str:
        """Ask LLM to summarize old messages, preserving critical info."""
        # Build a compressed representation of old messages
        parts: list[str] = []
        for m in messages:
            role = m.get("role", "?")
            content = m.get("content", "")
            if content:
                # Truncate very long messages
                short = content[:1000] + ("..." if len(content) > 1000 else "")
                parts.append(f"[{role}]: {short}")

        prompt = (
            "Summarize the following conversation history. Preserve:\n"
            "1. User requests and intent\n"
            "2. Key technical concepts and decisions\n"
            "3. Files examined or modified\n"
            "4. Errors encountered and fixes applied\n"
            "5. Current work in progress and next steps\n\n"
            f"Conversation:\n{chr(10).join(parts)}\n\n"
            "Summary:"
        )

        try:
            summary = llm.complete_text(prompt)
            return summary[: self.max_summary_chars]
        except Exception:
            # Fallback: simple truncation summary
            user_msgs = [m.get("content", "") for m in messages if m.get("role") == "user"]
            return f"Previous conversation with {len(user_msgs)} user queries. "
    def estimate_tokens(self, messages: list[dict]) -> int:
        return sum(len(json.dumps(m, ensure_ascii=False)) for m in messages) // CHARS_PER_TOKEN
