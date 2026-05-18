"""Unified tool specification and invocation record types.

Parity with ClawCode clawcode/llm/tool_spec.py

Provides ToolSpec (the single source of truth for tool metadata, schema,
risk level, idempotency and examples), ErrorCategory (canonical failure
classification), and InvocationRecord (structured per-call audit trail).
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pydantic import BaseModel, ValidationError

from .tools.base import BaseTool, ToolCall, ToolInfo, ToolResponse


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SideEffectLevel(str, Enum):
    NONE = "none"
    LOCAL_FS = "local_fs"
    PROCESS = "process"
    NETWORK = "network"
    REPO = "repo"
    EXTERNAL = "external"


class ErrorCategory(str, Enum):
    """Canonical failure classification used by the repair state machine."""

    VALIDATION = "validation"
    POLICY_DENIED = "policy_denied"
    PERMISSION_DENIED = "permission_denied"
    TRANSIENT = "transient"
    HARD_ERROR = "hard_error"
    OUTCOME_MISMATCH = "outcome_mismatch"
    UNKNOWN = "unknown"


class RepairAction(str, Enum):
    """What the repair state machine should do after a failure."""

    FIX_PARAMS = "fix_params"
    RETRY_SAME = "retry_same"
    REPLAN = "replan"
    ESCALATE_TO_USER = "escalate_to_user"
    ABORT = "abort"


# ---------------------------------------------------------------------------
# ToolSpec -- wraps ToolInfo with production-grade metadata
# ---------------------------------------------------------------------------

@dataclass
class ToolExample:
    """A positive or negative example for a tool call."""

    description: str
    input: dict[str, Any]
    is_negative: bool = False


@dataclass
class ToolSpec:
    """Single source of truth for a tool's contract.

    Built from a BaseTool's ToolInfo plus optional enrichments.  The
    InvocationPipeline and RepairStateMachine consume this rather than
    raw ToolInfo dicts.
    """

    tool_info: ToolInfo
    tool_instance: BaseTool

    # Risk & side-effect metadata (defaults are conservative)
    risk_level: RiskLevel = RiskLevel.LOW
    side_effect: SideEffectLevel = SideEffectLevel.NONE
    idempotent: bool = True

    # Which ErrorCategory values are auto-repairable for this tool
    recoverable_errors: frozenset[ErrorCategory] = frozenset({ErrorCategory.VALIDATION})

    # Pydantic model class for input validation (optional)
    input_model: type[BaseModel] | None = None

    examples: list[ToolExample] = field(default_factory=list)
    postcondition_hint: str = ""

    # ---- derived helpers ----

    @property
    def name(self) -> str:
        return self.tool_info.name

    @property
    def schema_dict(self) -> dict[str, Any]:
        """Return the JSON Schema dict sent to the LLM, with hardened defaults."""
        schema = dict(self.tool_info.parameters) if self.tool_info.parameters else {}
        if schema.get("type") == "object" and "additionalProperties" not in schema:
            schema["additionalProperties"] = False
        return schema

    def validate_input(self, raw: dict[str, Any]) -> dict[str, Any] | ValidationError:
        """Validate *raw* against input_model if available, else pass through."""
        if self.input_model is None:
            return raw
        try:
            obj = self.input_model.model_validate(raw)
            return obj.model_dump()
        except ValidationError as exc:
            return exc

    @classmethod
    def from_tool(cls, tool: BaseTool, **overrides: Any) -> "ToolSpec":
        """Build a ToolSpec from an existing BaseTool."""
        info = tool.info()
        defaults: dict[str, Any] = {}
        if getattr(tool, "is_dangerous", False):
            defaults["risk_level"] = RiskLevel.HIGH
            defaults["side_effect"] = SideEffectLevel.LOCAL_FS
            defaults["idempotent"] = False
        elif getattr(tool, "requires_permission", True):
            defaults["risk_level"] = RiskLevel.MEDIUM
        merged = {**defaults, **overrides}
        return cls(tool_info=info, tool_instance=tool, **merged)


# ---------------------------------------------------------------------------
# InvocationRecord -- structured audit trail per tool call
# ---------------------------------------------------------------------------

class InvocationPhase(str, Enum):
    PENDING = "pending"
    NORMALIZED = "normalized"
    VALIDATED = "validated"
    POLICY_CHECKED = "policy_checked"
    HOOK_CHECKED = "hook_checked"
    PERMISSION_REQUESTED = "permission_requested"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    REPAIRED = "repaired"


@dataclass
class InvocationRecord:
    """Structured record of a single tool invocation through the pipeline."""

    record_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    tool_name: str = ""
    tool_call_id: str = ""
    session_id: str = ""
    timestamp: float = field(default_factory=time.time)

    # Input tracking
    raw_input: dict[str, Any] = field(default_factory=dict)
    normalized_input: dict[str, Any] = field(default_factory=dict)
    validation_errors: list[str] = field(default_factory=list)

    # Pipeline progression
    phase: InvocationPhase = InvocationPhase.PENDING
    risk_level: RiskLevel = RiskLevel.LOW
    policy_blocked: bool = False
    policy_reason: str = ""
    hook_blocked: bool = False
    hook_reason: str = ""
    permission_granted: bool | None = None

    # Execution outcome
    duration_ms: float = 0.0
    is_error: bool = False
    error_category: ErrorCategory = ErrorCategory.UNKNOWN
    error_message: str = ""
    output_preview: str = ""

    # Repair tracking
    repair_attempts: int = 0
    repair_succeeded: bool = False

    def mark_failed(self, category: ErrorCategory, message: str) -> None:
        self.phase = InvocationPhase.FAILED
        self.is_error = True
        self.error_category = category
        self.error_message = message

    def mark_completed(self, output: str, is_error: bool = False) -> None:
        self.phase = InvocationPhase.COMPLETED
        self.is_error = is_error
        self.output_preview = output[:500] if output else ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "tool_name": self.tool_name,
            "tool_call_id": self.tool_call_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "phase": self.phase.value,
            "risk_level": self.risk_level.value,
            "is_error": self.is_error,
            "error_category": self.error_category.value,
            "error_message": self.error_message,
            "repair_attempts": self.repair_attempts,
            "repair_succeeded": self.repair_succeeded,
            "duration_ms": self.duration_ms,
            "policy_blocked": self.policy_blocked,
            "hook_blocked": self.hook_blocked,
            "permission_granted": self.permission_granted,
        }


# ---------------------------------------------------------------------------
# ToolSpec registry -- builds specs for all tools once
# ---------------------------------------------------------------------------

# Per-tool overrides keyed by tool name.
_TOOL_SPEC_OVERRIDES: dict[str, dict[str, Any]] = {
    "bash": {
        "risk_level": RiskLevel.HIGH,
        "side_effect": SideEffectLevel.PROCESS,
        "idempotent": False,
        "recoverable_errors": frozenset({
            ErrorCategory.VALIDATION,
            ErrorCategory.TRANSIENT,
        }),
    },
    "write": {
        "risk_level": RiskLevel.HIGH,
        "side_effect": SideEffectLevel.LOCAL_FS,
        "idempotent": True,
        "recoverable_errors": frozenset({ErrorCategory.VALIDATION}),
    },
    "edit": {
        "risk_level": RiskLevel.HIGH,
        "side_effect": SideEffectLevel.LOCAL_FS,
        "idempotent": False,
        "recoverable_errors": frozenset({ErrorCategory.VALIDATION}),
    },
    "patch": {
        "risk_level": RiskLevel.HIGH,
        "side_effect": SideEffectLevel.LOCAL_FS,
        "idempotent": False,
        "recoverable_errors": frozenset({ErrorCategory.VALIDATION}),
    },
    "Agent": {
        "risk_level": RiskLevel.HIGH,
        "side_effect": SideEffectLevel.LOCAL_FS,
        "idempotent": False,
        "recoverable_errors": frozenset({ErrorCategory.VALIDATION, ErrorCategory.TRANSIENT}),
    },
    "view": {
        "risk_level": RiskLevel.LOW,
        "side_effect": SideEffectLevel.NONE,
        "idempotent": True,
    },
    "ls": {
        "risk_level": RiskLevel.LOW,
        "side_effect": SideEffectLevel.NONE,
        "idempotent": True,
    },
    "glob": {
        "risk_level": RiskLevel.LOW,
        "side_effect": SideEffectLevel.NONE,
        "idempotent": True,
    },
    "grep": {
        "risk_level": RiskLevel.LOW,
        "side_effect": SideEffectLevel.NONE,
        "idempotent": True,
    },
    "fetch": {
        "risk_level": RiskLevel.MEDIUM,
        "side_effect": SideEffectLevel.NETWORK,
        "idempotent": True,
        "recoverable_errors": frozenset({ErrorCategory.VALIDATION, ErrorCategory.TRANSIENT}),
    },
    "TodoWrite": {
        "risk_level": RiskLevel.LOW,
        "side_effect": SideEffectLevel.LOCAL_FS,
        "idempotent": True,
    },
    "TodoRead": {
        "risk_level": RiskLevel.LOW,
        "side_effect": SideEffectLevel.NONE,
        "idempotent": True,
    },
}


def build_tool_specs(tools: list[BaseTool]) -> dict[str, ToolSpec]:
    """Build a ToolSpec registry from a list of tools."""
    specs: dict[str, ToolSpec] = {}
    for tool in tools:
        name = tool.info().name
        overrides = _TOOL_SPEC_OVERRIDES.get(name, {})
        specs[name] = ToolSpec.from_tool(tool, **overrides)
    return specs
