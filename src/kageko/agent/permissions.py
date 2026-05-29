# src/kageko/agent/permissions.py
from __future__ import annotations

import re
from enum import Enum
from typing import Any, Awaitable, Callable

from kageko.types import ToolCall


class Decision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    EXECUTE_IN_SANDBOX = "sandbox"
    ASK_USER = "ask"


class SecurityMode(str, Enum):
    PERMISSIVE = "permissive"
    READ_ONLY = "read-only"
    INTERACTIVE = "interactive"


class RuleEngine:
    """Layer 1: Dangerous pattern detection."""

    DANGEROUS_PATTERNS: list[re.Pattern[str]] = [
        re.compile(r"rm\s+(-rf?|--recursive)\s+[/~]", re.IGNORECASE),
        re.compile(r":\(\)\s*\{.*\|.*&\s*\}", re.DOTALL),  # fork bomb
        re.compile(r"chmod\s+777", re.IGNORECASE),
        re.compile(r"curl.*\|\s*(ba)?sh", re.IGNORECASE),
        re.compile(r"mkfs\.", re.IGNORECASE),
        re.compile(r"dd\s+if=/dev/(zero|random)\s+of=/", re.IGNORECASE),
    ]

    def check(self, tool_call: ToolCall) -> Decision | None:
        if tool_call.name in ("bash", "native_shell"):
            command = tool_call.args.get("command", "")
            for pattern in self.DANGEROUS_PATTERNS:
                if pattern.search(command):
                    return Decision.DENY
        return None


PromptFn = Callable[[ToolCall], Awaitable[Decision]]


class PermissionPipeline:
    """4-layer permission pipeline: rules -> sandbox -> mode -> interactive."""

    HIGH_RISK_TOOLS: set[str] = {"bash", "eval"}

    def __init__(
        self,
        mode: SecurityMode = SecurityMode.INTERACTIVE,
        prompt_fn: PromptFn | None = None,
        sandbox_enabled: bool = False,
    ):
        self.mode = mode
        self.sandbox_enabled = sandbox_enabled
        self.prompt_fn = prompt_fn
        self.rule_engine = RuleEngine()
        self._session_allow_all: set[str] = set()

    async def check(self, tool_call: ToolCall) -> Decision:
        # Layer 1: Rule engine
        if decision := self.rule_engine.check(tool_call):
            return decision

        # Layer 2: Sandbox for high-risk tools
        if self.sandbox_enabled and tool_call.name in self.HIGH_RISK_TOOLS:
            return Decision.EXECUTE_IN_SANDBOX

        # Layer 3: Mode guard
        if decision := self._check_mode(tool_call):
            return decision

        # Layer 3.5: Session-wide "always allow" cache
        if tool_call.name in self._session_allow_all:
            return Decision.ALLOW

        # Layer 4: Interactive prompt
        if self.prompt_fn:
            decision = await self.prompt_fn(tool_call)
            if decision == Decision.ALLOW and self._is_always_decision(decision):
                pass  # handled by the prompt function
            return decision
        if self.mode == SecurityMode.INTERACTIVE:
            raise PermissionError("Interactive mode requires a prompt function")
        return Decision.ALLOW

    def _is_always_decision(self, decision: Decision) -> bool:
        """Override point — actual always-tracking is done by the prompt function."""
        return False

    def allow_always(self, tool_name: str) -> None:
        """Mark a tool as always-allowed for the rest of the session."""
        self._session_allow_all.add(tool_name)

    def _check_mode(self, tool_call: ToolCall) -> Decision | None:
        if self.mode == SecurityMode.READ_ONLY:
            write_tools = {"file_write", "hashline_edit", "bash", "eval", "native_shell"}
            if tool_call.name in write_tools:
                return Decision.DENY
        return None
