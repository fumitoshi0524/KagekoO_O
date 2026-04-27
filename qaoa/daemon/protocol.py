"""JSON-RPC request dispatch logic for the Kageko daemon."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Callable

from ..runtime import KagekoRuntime, create_runtime
from ..types import AgentMode, ToolUse

EmitFn = Callable[[dict[str, Any]], None]


class RequestHandler:
    """Handles JSON-RPC method dispatch for the daemon."""

    def __init__(self, logger: Any | None = None) -> None:
        self.runtime: KagekoRuntime | None = None
        self.logger = logger

    def _log(self, level: str, message: str, **meta: Any) -> None:
        if self.logger is not None and hasattr(self.logger, level):
            getattr(self.logger, level)(message, **meta)

    def handle(self, method: str, params: dict[str, Any], emit: EmitFn) -> Any:
        if method == "daemon.ping":
            return {"pong": True, "initialized": self.runtime is not None}

        if method == "daemon.status":
            return {
                "initialized": self.runtime is not None,
                "provider": self.runtime.provider if self.runtime else None,
                "model": self.runtime.model if self.runtime else None,
            }

        if method == "daemon.shutdown":
            self._log("info", "daemon shutdown requested")
            return {"ok": True}

        if method == "init":
            self._log("info", "runtime initializing", provider=params.get("provider"), model=params.get("model"))
            self.runtime = create_runtime(
                provider=_as_optional_str(params.get("provider")),
                api_key=_as_optional_str(params.get("api_key")),
                model=_as_optional_str(params.get("model")),
                base_url=_as_optional_str(params.get("base_url")),
                workspace=_as_optional_str(params.get("workspace")),
                skills_dir=_as_optional_str(params.get("skills_dir")),
                enable_rag=_as_bool(params.get("enable_rag")),
                rag_persist_dir=_as_optional_str(params.get("rag_persist_dir")),
                enable_mcp=_as_bool(params.get("enable_mcp")),
                mcp_server_url=_as_optional_str(params.get("mcp_server_url")),
            )
            self._log("info", "runtime initialized", provider=self.runtime.provider, model=self.runtime.model)
            return {"provider": self.runtime.provider, "model": self.runtime.model}

        runtime = self._require_runtime()

        if method == "run":
            tool_plan = _as_tool_plan(params.get("tool_plan"))
            session_id = _as_optional_str(params.get("session_id"))
            auto_approve = _as_bool(params.get("auto_approve"))
            message = _as_str(params.get("message"))
            skill_name = _as_optional_str(params.get("skill_name"))
            generate_skill = _as_bool(params.get("generate_skill"))

            # Approval workflow: if auto_approve is false and no explicit tool plan,
            # plan actions first and check risk levels.
            if not auto_approve and tool_plan is None:
                selected_skill = runtime._resolve_skill(session_id=session_id, skill_name=skill_name)
                if generate_skill and selected_skill is None:
                    selected_skill = runtime.engine._generate_skill(message)
                planned_actions = runtime.engine.plan_actions(query=message, skill=selected_skill)
                risky_actions = []
                for action in planned_actions:
                    try:
                        spec = runtime.tools.describe(action.name)
                        if spec.risk_level != "read":
                            risky_actions.append({
                                "name": action.name,
                                "input": action.input,
                                "risk_level": spec.risk_level,
                            })
                    except ValueError:
                        continue
                if risky_actions:
                    self._log("info", "approval required", actions=len(risky_actions))
                    return {
                        "approval_required": True,
                        "planned_actions": [{"name": a.name, "input": a.input} for a in planned_actions],
                        "risky_actions": risky_actions,
                    }
                # No risky actions; fall through to normal execution with planned actions
                tool_plan = [ToolUse(name=a.name, input=a.input) for a in planned_actions]

            self._log("info", "running agent", session_id=session_id)
            response = runtime.run(
                AgentMode.QAOA,
                message,
                session_id=session_id,
                tool_plan=tool_plan,
                skill_name=skill_name,
                generate_skill=generate_skill,
            )
            return {
                "answer": response.answer,
                "trace": response.trace,
                "tools": [asdict(tool) for tool in response.tools],
                "qaoa_turns": [asdict(turn) for turn in response.qaoa_turns],
            }

        if method == "skills.generate":
            skill = runtime.generate_skill(
                name=_as_str(params.get("name")),
                objective=_as_str(params.get("objective")),
            )
            self._log("info", "skill generated", name=skill.name)
            return asdict(skill)

        if method == "skills.list":
            return [asdict(skill) for skill in runtime.list_skills()]

        if method == "skills.use":
            runtime.activate_skill(
                session_id=_as_str(params.get("session_id")),
                name=_as_str(params.get("name")),
            )
            return {"ok": True}

        if method == "skills.clear":
            runtime.clear_active_skill(session_id=_as_str(params.get("session_id")))
            return {"ok": True}

        if method == "skills.active":
            skill = runtime.get_active_skill(session_id=_as_str(params.get("session_id")))
            return asdict(skill) if skill is not None else None

        if method == "sessions.list":
            return runtime.list_sessions()

        if method == "sessions.clear":
            runtime.clear_session(session_id=_as_str(params.get("session_id")))
            return {"ok": True}

        if method == "pipeline.generate_tool":
            result = runtime.generate_tool_via_pipeline(
                spec=_as_str(params.get("spec")),
                name=_as_str(params.get("name")),
                category=_as_str(params.get("category") or "utility"),
                domain=_as_str(params.get("domain") or "general"),
                output_dir=_as_str(params.get("output_dir")),
            )
            return {
                "success": result.success,
                "output_path": str(result.output_path) if result.output_path else None,
                "errors": result.errors,
            }

        if method == "pipeline.generate_skill":
            result = runtime.generate_skill_via_pipeline(
                name=_as_str(params.get("name")),
                goal=_as_str(params.get("goal")),
                output_dir=_as_str(params.get("output_dir")),
            )
            return {
                "success": result.success,
                "output_path": str(result.output_path) if result.output_path else None,
                "errors": result.errors,
            }

        if method == "tools.list":
            return [asdict(spec) for spec in runtime.tools.list_specs()]

        if method == "tools.show":
            spec = runtime.tools.describe(_as_str(params.get("name")))
            return asdict(spec)

        if method == "tools.call":
            output = runtime.tools.call(
                _as_str(params.get("name")),
                _as_str(params.get("payload")),
            )
            return {"output": output}

        raise ValueError(f"Unsupported method: {method}")

    def _require_runtime(self) -> KagekoRuntime:
        if self.runtime is None:
            raise RuntimeError("Runtime not initialized. Call init first.")
        return self.runtime


def _as_str(value: object) -> str:
    if isinstance(value, str):
        return value
    raise TypeError("Expected string value.")


def _as_optional_str(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped != "" else None
    raise TypeError("Expected optional string value.")


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, int):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("true", "1", "yes", "on"):
            return True
        if lowered in ("false", "0", "no", "off"):
            return False
    raise TypeError("Expected boolean value.")


def _as_tool_plan(value: object) -> list[ToolUse] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        raise TypeError("tool_plan must be an array.")
    plan: list[ToolUse] = []
    for item in value:
        if not isinstance(item, dict):
            raise TypeError("tool_plan items must be objects.")
        name = item.get("name")
        payload = item.get("input")
        if not isinstance(name, str) or not isinstance(payload, str):
            raise TypeError("tool_plan item requires string name and input.")
        plan.append(ToolUse(name=name, input=payload))
    return plan
