"""Hermes-style Nudge Engine — periodic background fact review.

Counter-based trigger: every N turns, fork a mini tool-using agent loop.
The review agent gets the SAME memory/skill tools the main agent uses,
can iterate (max 5 turns), and sees results of each tool call before
deciding the next action.

Key difference from Hermes: we don't fork a full AIAgent (which requires
a separate LLM client and all the wiring). Instead we run an inline
mini-loop within the same process, reusing the same LLM client.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from kageko.types import Message, ToolCall

if TYPE_CHECKING:
    from kageko.learning.memory_store import MemoryStore

logger = logging.getLogger("kageko.learning.nudge")

_REVIEW_PROMPT = """\
You are a background curator. Your job: clean up the agent's long-term
memory after every review pass. Be ACTIVE — a pass that does nothing
is a missed opportunity, not a neutral outcome.

Tools:
- `memory_list` — see every stored fact
- `memory` — add / replace / remove (action parameter)

MANDATORY: call memory_list FIRST. Then for EVERY fact in the list,
decide: KEEP, MERGE, REPLACE, or REMOVE.

- Duplicates: two facts saying the same thing? REMOVE the weaker one,
  add a single merged one that covers both. Do NOT leave duplicates.
- Outdated: a fact is wrong or stale? REPLACE it.
- Transient: a fact about a working directory, session ID, one-off
  result, or specific file path? REMOVE it immediately.
- Missing: something NEW from the conversation worth remembering?
  ADD it (one sentence, English, user preferences first).

What to ADD: stable user preferences, recurring corrections, environment
facts (OS, tools, conventions), concrete error workarounds learned the
hard way ("native_shell needs forward slashes on Windows").

What to REMOVE: working directories, file paths, session artifacts,
one-off task results, chit-chat, transient errors that resolved by retrying.

You MUST produce at least ONE tool call per review. If the list of
existing facts already has duplicates, you MUST merge them. If there
are transient facts, you MUST delete them. "Nothing to save." is ONLY
valid when the fact list is already clean and the conversation added
nothing new — not as a default.

Transcript:
{transcript}
"""


class NudgeEngine:

    def __init__(self, store: MemoryStore, *, threshold: int = 10):
        self.store = store
        self.threshold = threshold
        self._turns = 0

    def tick(self) -> bool:
        self._turns += 1
        if self._turns >= self.threshold:
            self._turns = 0
            return True
        return False

    def reset(self) -> None:
        self._turns = 0

    async def run_review(self, recent_messages: list, llm) -> list[str]:
        """Run a tool-using mini agent loop for memory review.

        The review agent iterates with memory_list and memory tools,
        just like Hermes forks a sub-agent with access to the real tools.
        """
        transcript = self._build_transcript(recent_messages)
        if not transcript.strip():
            return []

        review_msgs = [Message(role="system", content=_REVIEW_PROMPT.format(transcript=transcript))]
        schemas = [
            {
                "name": "memory_list",
                "description": "List all stored facts.",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
            {
                "name": "memory",
                "description": "Manage facts. action: add/replace/remove. old_text identifies by substring.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "enum": ["add", "replace", "remove"]},
                        "content": {"type": "string", "description": "The fact text (for add/replace)"},
                        "old_text": {"type": "string", "description": "Substring to identify the target (for replace/remove)"},
                    },
                    "required": ["action"],
                },
            },
        ]
        results: list[str] = []

        for _ in range(5):
            try:
                response = await llm.chat(review_msgs, tools=schemas)
            except Exception:
                logger.warning("Nudge review LLM call failed", exc_info=True)
                break

            review_msgs.append(Message(
                role="assistant",
                content=response.content or "",
                tool_calls=response.tool_calls,
            ))
            if not response.has_tool_calls():
                break

            for tc in response.tool_calls:
                result = await self._dispatch(tc)
                review_msgs.append(Message(
                    role="tool", content=result,
                    tool_call_id=tc.id, tool_name=tc.name,
                ))
                results.append(result)

        return results

    async def _dispatch(self, tc: ToolCall) -> str:
        if tc.name == "memory_list":
            facts = await self.store.list(limit=100)
            if not facts:
                return "(no facts)"
            lines = [f.content for f in facts]
            return "\n".join(f"- {l}" for l in lines)

        if tc.name == "memory":
            action = tc.args.get("action", "")
            content = tc.args.get("content", "")
            old_text = tc.args.get("old_text", "")
            if action == "add":
                if not content:
                    return "[ERROR] content required"
                await self.store.add(content.strip(), source="fact")
                u = await self.store.usage()
                return f"Added. {u['pct']}% full."
            elif action == "replace":
                if not old_text or not content:
                    return "[ERROR] old_text + content required"
                cnt = await self.store.replace(old_text.strip(), content.strip())
                return f"Replaced {cnt} fact(s)." if cnt else f"No match for '{old_text[:60]}'."
            elif action == "remove":
                if not old_text:
                    return "[ERROR] old_text required"
                cnt = await self.store.delete(substring=old_text.strip())
                return f"Removed {cnt} fact(s)." if cnt else f"No match for '{old_text[:60]}'."
            return f"[ERROR] Unknown action: {action}"

        return f"[ERROR] Unknown tool: {tc.name}"

    @staticmethod
    def _build_transcript(messages: list) -> str:
        lines = []
        for m in messages[-20:]:
            role = getattr(m, "role", "?")
            content = str(getattr(m, "content", ""))[:300]
            if content.strip():
                lines.append(f"[{role}] {content}")
        return "\n".join(lines)
