"""Multi-layer permission pipeline for tool execution safety.

Pipeline (in order):
  1. validateInput()      — reject invalid args before any permission check
  2. isReadOnly            — auto-approve reads
  3. Dangerous patterns    — block known-dangerous commands (rm -rf /, etc.)
  4. Permission rules      — user-defined allow/deny/ask lists
  5. Interactive prompt    — ask user for confirmation
  6. Tool-specific checks  — per-tool overrides
  7. Session memory        — "always for this session" cache
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from .types import SkillSpec

# ── Mode ────────────────────────────────────────────────────────────────

class PermissionMode(StrEnum):
    DEFAULT = "default"         # every write/destructive tool needs confirmation
    PLAN = "plan"               # AI plans only, no writes
    ACCEPT_EDITS = "acceptEdits"  # file edits auto-allowed, others need confirm
    AUTO = "auto"               # auto-approve everything except dangerous patterns
    BYPASS = "bypass"           # skip all except hard-coded safety


# ── Rule types ──────────────────────────────────────────────────────────

@dataclass(slots=True, frozen=True, kw_only=True)
class PermissionRule:
    pattern: str                # tool name or wildcard pattern
    action: str                 # "allow" | "deny" | "ask"
    tool_input_pattern: str = ""  # optional input matching

    def matches(self, tool_name: str, tool_input: str = "") -> bool:
        # Exact match
        if self.pattern == tool_name:
            if self.tool_input_pattern and self.tool_input_pattern not in tool_input:
                return False
            return True
        # Wildcard match: "bash.*" matches "bash.run", "bash.ls"
        if self.pattern.endswith(".*") and tool_name.startswith(self.pattern[:-2]):
            return True
        # Prefix match: "bash:" matches tools starting with "bash."
        if self.pattern.endswith(":") and tool_name.startswith(self.pattern[:-1]):
            return True
        return False


# ── Dangerous pattern detection ─────────────────────────────────────────

DANGEROUS_PATTERNS: list[tuple[str, str]] = [
    (r"rm\s+-rf\s+/", "Recursive root deletion"),
    (r"rm\s+-rf\s+~", "Home directory deletion"),
    (r"dd\s+if=", "Raw disk write"),
    (r">\s*/dev/sd", "Raw device overwrite"),
    (r"mkfs\.", "Filesystem format"),
    (r":\(\)\s*\{\s*:\|:&\s*\};:", "Fork bomb"),
    (r"chmod\s+-R\s+777\s+/", "Recursive world-writable root"),
    (r"git\s+push\s+--force.*main", "Force push to main"),
    (r"git\s+push\s+--force.*master", "Force push to master"),
]
SENSITIVE_PATHS: set[str] = {".git", ".claude", ".kageko", ".vscode", ".bashrc", ".zshrc",
                              ".env", "credentials.json", "id_rsa", "id_ed25519"}


def _check_dangerous(tool_name: str, tool_input: str) -> str | None:
    """Returns a reason string if the tool call is blocked."""
    import re
    for pattern, reason in DANGEROUS_PATTERNS:
        if re.search(pattern, tool_input):
            return f"Blocked dangerous pattern: {reason} (matched '{pattern}')"
    # Sensitive path check
    if tool_name in ("file.write", "bash.run"):
        for sp in SENSITIVE_PATHS:
            if sp in tool_input:
                return f"Warning: operation touches sensitive path '{sp}' — requires confirmation"
    return None


# ── Main permission handler ─────────────────────────────────────────────

@dataclass(slots=True, kw_only=True)
class PermissionHandler:
    mode: PermissionMode = PermissionMode.DEFAULT
    rules: list[PermissionRule] = field(default_factory=list)
    session_approvals: dict[str, set[str]] = field(default_factory=dict)
    tool_risk_cache: dict[str, str] = field(default_factory=dict)

    # Layer 1: Input validation
    def validate_input(self, tool_name: str, tool_input: str) -> str | None:
        """Returns error string if input is invalid, None if OK."""
        if not tool_input.strip():
            return "Empty input"
        # Bash-specific: reject empty commands
        if tool_name == "bash.run" and not tool_input.strip():
            return "Empty bash command"
        return None

    # Layer 2: Read-only check
    def is_read_only(self, tool_name: str) -> bool:
        risk = self.tool_risk_cache.get(tool_name, "write")  # fail-closed: unknown = write
        return risk == "read"

    # Layer 3+4+5: Full permission check
    def check(self, tool_name: str, tool_input: str, skill: object | None = None) -> tuple[bool, str]:
        """Returns (allowed, reason). The full pipeline."""
        # Layer 1: validate input
        error = self.validate_input(tool_name, tool_input)
        if error:
            return False, f"Invalid input: {error}"

        # Layer 2: read-only auto-approve (only if cache has been populated)
        if self.tool_risk_cache and self.is_read_only(tool_name):
            return True, "auto-approve-read"

        # Layer 3: dangerous pattern check
        danger = _check_dangerous(tool_name, tool_input)
        if danger:
            if "Warning:" not in danger:
                return False, danger
            # Warning only — continue to next layers

        # Layer 4: permission rules
        rule_result = self._check_rules(tool_name, tool_input)
        if rule_result is not None:
            return rule_result

        # Layer 5: mode-based decision
        if self.mode == PermissionMode.BYPASS:
            return True, "bypass-mode"
        if self.mode == PermissionMode.PLAN:
            return False, "plan-mode-read-only"
        if self.mode == PermissionMode.AUTO:
            # In auto mode, allow unless dangerous
            if danger:
                return False, f"auto-mode-blocked: {danger}"
            return True, "auto-mode"

        # Layer 6: session memory
        if tool_name in self.session_approvals.get("__global__", set()):
            return True, "session-approved"

        # Layer 7: need user approval
        return False, "requires-approval"

    def _check_rules(self, tool_name: str, tool_input: str) -> tuple[bool, str] | None:
        """Check user-defined rules. Returns None if no rule matches."""
        for rule in self.rules:
            if rule.matches(tool_name, tool_input):
                if rule.action == "deny":
                    return False, f"rule-deny:{rule.pattern}"
                if rule.action == "allow":
                    return True, f"rule-allow:{rule.pattern}"
                if rule.action == "ask":
                    return False, "rule-ask"
        return None

    def approve_for_session(self, tool_name: str) -> None:
        self.session_approvals.setdefault("__global__", set()).add(tool_name)

    def reset_session(self) -> None:
        self.session_approvals.clear()

    # ── Rule management ────────────────────────────────────────────────

    def add_rule(self, pattern: str, action: str, tool_input_pattern: str = "") -> None:
        self.rules.append(PermissionRule(pattern=pattern, action=action,
                                          tool_input_pattern=tool_input_pattern))

    def load_rules_from_file(self, path: Path) -> None:
        if not path.exists():
            return
        import json
        data = json.loads(path.read_text(encoding="utf-8"))
        rules_data = data.get("permissions", data.get("rules", []))
        for r in rules_data:
            if isinstance(r, dict):
                self.add_rule(
                    pattern=r.get("pattern", r.get("tool", "")),
                    action=r.get("action", "ask"),
                    tool_input_pattern=r.get("input", ""),
                )

    def load_rules_from_config(self) -> None:
        path = Path.home() / ".kageko" / "permissions.json"
        self.load_rules_from_file(path)


# ── Factory ─────────────────────────────────────────────────────────────

def create_permission_handler(mode: str = "default") -> PermissionHandler:
    handler = PermissionHandler(
        mode=PermissionMode(mode) if mode in PermissionMode.__members__ else PermissionMode.DEFAULT,
    )
    handler.load_rules_from_config()
    return handler
