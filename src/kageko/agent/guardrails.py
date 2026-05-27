from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field


IDEMPOTENT_TOOLS = frozenset({
    "read_file", "search_files", "grep", "ast_grep",
    "web_search", "browser_snapshot", "list_files",
})

MUTATING_TOOLS = frozenset({
    "run_bash", "write_file", "edit_file", "hashline_edit", "execute_code",
})


@dataclass
class GuardrailConfig:
    same_call_warn: int = 2
    same_call_block: int = 5
    failure_warn: int = 3
    failure_halt: int = 8
    idempotent_warn: int = 2
    idempotent_block: int = 5


@dataclass
class ToolCallSignature:
    tool_name: str
    args: dict
    hash: str = ""

    def __post_init__(self):
        if not self.hash:
            canonical = json.dumps(
                {"tool": self.tool_name, "args": self.args},
                sort_keys=True,
            )
            self.hash = hashlib.sha256(canonical.encode()).hexdigest()


@dataclass
class ToolGuardrailDecision:
    action: str  # "allow" | "warn" | "block" | "halt"
    code: str
    message: str


class ToolGuardrail:
    """Pure-function tool call loop detector. No side effects on tool execution."""

    def __init__(self, config: GuardrailConfig | None = None):
        self.config = config or GuardrailConfig()
        self._call_counts: dict[str, int] = {}
        self._failure_counts: dict[str, int] = {}

    def check(self, sig: ToolCallSignature, failed: bool = False) -> ToolGuardrailDecision:
        h = sig.hash
        self._call_counts[h] = self._call_counts.get(h, 0) + 1
        if failed:
            self._failure_counts[h] = self._failure_counts.get(h, 0) + 1

        call_count = self._call_counts[h]
        fail_count = self._failure_counts.get(h, 0)
        is_idempotent = sig.tool_name in IDEMPOTENT_TOOLS

        # Failure-based halt (highest priority)
        if fail_count >= self.config.failure_halt:
            return ToolGuardrailDecision(
                action="halt", code="FAILURE_HALT",
                message=f"Tool '{sig.tool_name}' failed {fail_count} times. Halting.",
            )

        # Idempotent no-progress
        if is_idempotent and fail_count >= self.config.idempotent_block:
            return ToolGuardrailDecision(
                action="block", code="IDEMPOTENT_NO_PROGRESS",
                message=f"Idempotent tool '{sig.tool_name}' making no progress ({fail_count} failures).",
            )
        if is_idempotent and fail_count >= self.config.idempotent_warn:
            return ToolGuardrailDecision(
                action="warn", code="IDEMPOTENT_NO_PROGRESS",
                message=f"Idempotent tool '{sig.tool_name}' making no progress ({fail_count} failures).",
            )

        # Failure-based warn
        if fail_count >= self.config.failure_warn:
            return ToolGuardrailDecision(
                action="warn", code="FAILURE_WARN",
                message=f"Tool '{sig.tool_name}' failed {fail_count} times.",
            )

        # Repeated call block
        if call_count >= self.config.same_call_block:
            return ToolGuardrailDecision(
                action="block", code="REPEATED_CALL_BLOCK",
                message=f"Same call repeated {call_count} times. Possible loop.",
            )

        # Repeated call warn
        if call_count >= self.config.same_call_warn:
            return ToolGuardrailDecision(
                action="warn", code="REPEATED_CALL_WARN",
                message=f"Same call repeated {call_count} times.",
            )

        return ToolGuardrailDecision(action="allow", code="OK", message="")

    def reset(self) -> None:
        self._call_counts.clear()
        self._failure_counts.clear()
