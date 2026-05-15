"""QAOA agent execution engine with native function calling."""

from __future__ import annotations

import json

from .adapters.llm import tool_spec_to_schema, build_name_map, ToolSchema, ToolCallResult
from .types import QAOAAction, QAOAObservation, QAOASkill, QAOATurn, ToolUse, SkillSpec
from .tools.registry import ToolSpec


class QAOAEngine:
    MAX_TURNS: int = 25
    MAX_CONTEXT_CHARS: int = 100_000

    def __init__(self, *, llm, tools, retriever=None, context: str = "",
                 provider: str = "", model: str = "") -> None:
        self.llm = llm
        self.tools = tools
        self.retriever = retriever
        self.context = context
        self.provider = provider
        self.model = model
        self._name_map: dict[str, str] = {}  # API-safe name → original name

    def run(
        self,
        *,
        query: str,
        tool_plan: list[ToolUse] | None = None,
        skill: SkillSpec | QAOASkill | None = None,
        allow_skill_generation: bool = False,
        max_turns: int | None = None,
        permission_callback: object | None = None,
    ) -> tuple[QAOATurn, list[str]]:
        """Iterative QAOA execution with native function calling.

        If the LLM adapter supports native tools, they are passed as callable
        functions. Otherwise, falls back to text-based planning (legacy mode).

        permission_callback(tool_name, tool_input, risk_level) -> bool
          Called before each tool execution. Return False to skip the tool.
        """
        limit = max_turns or self.MAX_TURNS
        skill = self._normalize_skill(skill)
        effective_skill = skill
        trace: list[str] = ["qaoa:start"]

        # Skill generation if allowed and no skill provided
        if effective_skill is None and allow_skill_generation:
            effective_skill = self._generate_skill(query)
            trace.append("qaoa:skill_generated")

        if effective_skill is not None:
            trace.append("qaoa:skill_applied")

        # Handle explicit tool plans (manual mode)
        if tool_plan:
            return self._run_manual_plan(query=query, tool_plan=tool_plan,
                                         skill=effective_skill, trace=trace)

        # Build initial messages
        messages = self._build_messages(query=query, skill=effective_skill)
        tool_schemas = self._build_tool_schemas(skill=effective_skill)

        actions: list[QAOAAction] = []
        observations: list[QAOAObservation] = []

        # ── Iterative agentic loop ───────────────────────────────────
        for turn_idx in range(limit):
            # Trim context if needed
            if self._context_too_large(messages):
                messages = self._trim_context(messages)
                trace.append(f"qaoa:context_trimmed@{turn_idx}")

            # Check if adapter supports native tools
            if hasattr(self.llm, 'complete') and tool_schemas:
                response = self._llm_complete(messages=messages, tools=tool_schemas)
            else:
                response = self._llm_text_complete(messages=messages)

            # Text response = final answer
            if not response.tool_calls and response.content:
                return QAOATurn(
                    query=query, skill=effective_skill,
                    actions=actions, observations=observations,
                    answer=response.content,
                ), trace + ["qaoa:completed"]

            # Tool calls returned — execute them
            if response.tool_calls:
                trace.append(f"qaoa:tool_calls@{turn_idx}")
                for tc in response.tool_calls:
                    original_name = self._name_map.get(tc.name, tc.name)
                    payload = self._args_to_payload(tc.arguments)

                    # Permission check
                    if permission_callback is not None:
                        risk = self._tool_risk(original_name)
                        if not permission_callback(original_name, payload, risk):
                            observations.append(QAOAObservation(
                                action_name=original_name,
                                output="User denied permission for this tool call."
                            ))
                            messages.append(self._format_tool_result(tc, "User denied permission."))
                            continue

                    try:
                        output = self._execute_tool_call(tc)
                    except Exception as exc:
                        output = f"Error: {exc}"
                        trace.append(f"qaoa:tool_error:{original_name}")

                    actions.append(QAOAAction(name=original_name, input=payload))
                    observations.append(QAOAObservation(action_name=original_name, output=output))

                    # Append tool call + result to messages for next turn
                    messages.append(self._format_assistant_tool_call(tc))
                    messages.append(self._format_tool_result(tc, output))
                continue

            # No tool calls and no content — stop
            trace.append("qaoa:empty_response")
            break

        # Max turns exceeded — generate best-effort answer
        answer = self._generate_final_answer(query=query, observations=observations, skill=effective_skill)
        return QAOATurn(
            query=query, skill=effective_skill,
            actions=actions, observations=observations,
            answer=answer,
        ), trace + ["qaoa:max_turns", "qaoa:completed"]

    # ── Streaming execution ────────────────────────────────────────────

    def run_stream(
        self,
        *,
        query: str,
        skill: SkillSpec | QAOASkill | None = None,
        max_turns: int | None = None,
        permission_callback: object | None = None,
    ) -> Iterator:
        """Iterative QAOA with streaming — yields StreamEvent for real-time display."""
        from .streaming import StreamEvent, StreamEventType

        limit = max_turns or self.MAX_TURNS
        skill = self._normalize_skill(skill)

        messages = self._build_messages(query=query, skill=skill)
        tool_schemas = self._build_tool_schemas(skill=skill)
        actions: list[QAOAAction] = []
        observations: list[QAOAObservation] = []

        for _turn_idx in range(limit):
            if self._context_too_large(messages):
                messages = self._trim_context(messages)

            # Check if adapter supports streaming
            stream_fn = getattr(self.llm, 'complete_stream', None)
            if callable(stream_fn) and tool_schemas:
                event_iter = stream_fn(messages=messages, tools=tool_schemas, tool_choice="auto")
            else:
                # Fallback: non-streaming complete
                response = self._llm_complete(messages=messages, tools=tool_schemas)
                if response.content:
                    yield StreamEvent(type=StreamEventType.TEXT_DELTA, text=response.content)
                yield StreamEvent(type=StreamEventType.DONE)
                return

            # Collect tool calls from this turn
            collected_tool_calls: list[dict] = []
            current_tool: dict | None = None
            text_content: list[str] = []

            for event in event_iter:
                if event.type == StreamEventType.TEXT_DELTA:
                    text_content.append(event.text or "")
                    yield event

                elif event.type == StreamEventType.TOOL_CALL_START:
                    current_tool = {
                        "id": event.tool_id, "name": event.tool_name, "arguments": ""
                    }

                elif event.type == StreamEventType.TOOL_CALL_ARGS:
                    if current_tool:
                        current_tool["arguments"] += (event.text or "")
                        current_tool["name"] = event.tool_name or current_tool["name"]
                    yield event

                elif event.type == StreamEventType.TOOL_CALL_END:
                    if current_tool:
                        current_tool["name"] = event.tool_name or current_tool["name"]
                        current_tool["tool_input"] = event.tool_input or current_tool["arguments"]
                        collected_tool_calls.append(current_tool)
                    current_tool = None
                    yield event

                elif event.type == StreamEventType.DONE:
                    break

            # Execute collected tool calls
            if collected_tool_calls:
                for tc_data in collected_tool_calls:
                    original_name = self._name_map.get(tc_data["name"], tc_data["name"])
                    payload = tc_data.get("tool_input", "")

                    # Permission check
                    if permission_callback is not None:
                        risk = self._tool_risk(original_name)
                        if not permission_callback(original_name, payload, risk):
                            observations.append(QAOAObservation(
                                action_name=original_name,
                                output="User denied permission."
                            ))
                            yield StreamEvent(
                                type=StreamEventType.TOOL_RESULT,
                                tool_name=original_name,
                                tool_output="User denied permission."
                            )
                            continue

                    try:
                        tc = ToolCallResult(
                            id=tc_data.get("id", ""),
                            name=tc_data["name"],
                            arguments=json.loads(payload) if payload else {},
                        )
                        output = self._execute_tool_call(tc)
                    except Exception as exc:
                        output = f"Error: {exc}"
                        yield StreamEvent(type=StreamEventType.ERROR, text=str(exc))

                    actions.append(QAOAAction(name=original_name, input=payload))
                    observations.append(QAOAObservation(action_name=original_name, output=output))
                    yield StreamEvent(
                        type=StreamEventType.TOOL_RESULT,
                        tool_name=original_name, tool_input=payload,
                        tool_output=output,
                    )

                    # Append to messages for next turn
                    tc2 = ToolCallResult(
                        id=tc_data.get("id", ""), name=tc_data["name"],
                        arguments=json.loads(payload) if payload else {},
                    )
                    messages.append(self._format_assistant_tool_call(tc2))
                    messages.append(self._format_tool_result(tc2, output))
                continue  # loop for replanning

            # No tool calls — text is final answer
            yield StreamEvent(type=StreamEventType.DONE)
            return

        # Max turns exceeded
        answer = self._generate_final_answer(query=query, observations=observations, skill=skill)
        yield StreamEvent(type=StreamEventType.TEXT_DELTA, text=answer)
        yield StreamEvent(type=StreamEventType.DONE)

    # ── Manual tool plan ──────────────────────────────────────────────

    def _run_manual_plan(self, *, query: str, tool_plan: list[ToolUse],
                         skill, trace: list[str]) -> tuple[QAOATurn, list[str]]:
        actions = [QAOAAction(name=t.name, input=t.input) for t in tool_plan]
        observations: list[QAOAObservation] = []
        for action in actions:
            output = self._run_action(action)
            observations.append(QAOAObservation(action_name=action.name, output=output))

        observation_text = "\n".join(f"{o.action_name}: {o.output}" for o in observations)
        skill_name = skill.name if skill else "none"
        skill_obj = skill.objective if hasattr(skill, 'objective') else getattr(skill, 'description', 'none')
        skill_steps = " | ".join(getattr(skill, 'steps', [])) if hasattr(skill, 'steps') and skill.steps else "none"

        answer = self.llm.complete_text(
            "Use the observations to answer the query.\n"
            f"Query: {query}\n"
            f"Skill: {skill_name} — {skill_obj}\n"
            f"Skill steps: {skill_steps}\n"
            f"Observations:\n{observation_text}"
        )
        return QAOATurn(
            query=query, skill=skill, actions=actions,
            observations=observations, answer=answer,
        ), trace + ["qaoa:manual_actions", "qaoa:completed"]

    # ── Message building ──────────────────────────────────────────────

    def _build_messages(self, *, query: str, skill) -> list[dict]:
        messages: list[dict] = []

        # System context
        system_parts: list[str] = []
        # Runtime identity — so the LLM knows what it's running on
        if self.provider:
            import platform as _platform
            system_parts.append(
                f"# Runtime\n"
                f"Provider: {self.provider}, Model: {self.model}\n"
                f"Platform: {_platform.system()} ({_platform.release()})\n"
                f"Shell: bash (Git Bash on Windows) — Unix commands work\n"
                f"Prefer file.read over bash.run for reading files"
            )
        if self.context:
            system_parts.append(self.context)
        if skill is not None:
            skill_name = skill.name
            if hasattr(skill, 'instructions'):
                system_parts.append(
                    f"# Active Skill: {skill_name}\n"
                    f"{skill.instructions}\n\n"
                    f"Follow the skill instructions above. "
                    f"You may use tools to accomplish the task."
                )
            elif hasattr(skill, 'objective'):
                steps = " | ".join(getattr(skill, 'steps', []))
                system_parts.append(
                    f"# Active Skill: {skill_name}\n"
                    f"Objective: {skill.objective}\n"
                    f"Steps: {steps}"
                )

        if system_parts:
            messages.append({"role": "system", "content": "\n\n".join(system_parts)})

        messages.append({"role": "user", "content": query})
        return messages

    def _build_tool_schemas(self, *, skill) -> list[ToolSchema]:
        """Get tool schemas, optionally scoped to skill's allowed_tools."""
        list_specs = getattr(self.tools, "list_specs", None)
        if not callable(list_specs):
            return []
        specs = list_specs()
        if not specs:
            return []

        allowed: set[str] | None = None
        if skill is not None:
            raw_tools = getattr(skill, 'allowed_tools', None) or getattr(skill, 'tools', None)
            if raw_tools:
                allowed = set(raw_tools)

        schemas: list[ToolSchema] = []
        for spec in specs:
            # Filter out read-only skill inspection tools, keep skill.generate
            if spec.name.startswith("skill.") and spec.name != "skill.generate":
                continue
            if allowed is not None and spec.name not in allowed:
                continue
            schemas.append(tool_spec_to_schema(spec))
        self._name_map = build_name_map(schemas, specs)
        return schemas

    # ── LLM interaction ───────────────────────────────────────────────

    def _llm_complete(self, *, messages: list[dict], tools: list[ToolSchema]):
        """Call LLM with native tool support."""
        return self.llm.complete(messages=messages, tools=tools, tool_choice="auto")

    def _llm_text_complete(self, *, messages: list[dict]):
        """Fallback text-only LLM call."""
        prompt = "\n".join(
            f"{m['role']}: {m['content']}" for m in messages
        )
        text = self.llm.complete_text(prompt)
        from .adapters.llm import LLMResponse
        return LLMResponse(content=text, stop_reason="stop")

    # ── Tool execution ────────────────────────────────────────────────

    def _execute_tool_call(self, tc: ToolCallResult) -> str:
        original_name = self._name_map.get(tc.name, tc.name)
        payload = self._args_to_payload(tc.arguments)
        return self.tools.call(original_name, payload)

    def _tool_risk(self, tool_name: str) -> str:
        try:
            spec = self.tools.describe(tool_name)
            return getattr(spec, 'risk_level', 'read')
        except ValueError:
            return "read"

    @staticmethod
    def _args_to_payload(args: dict) -> str:
        """Convert structured LLM arguments to string payload for tool execution."""
        if not args:
            return ""
        # file.write: {path/filepath/file_path, content} → "path\ncontent"
        path_key = next((k for k in ("path", "filepath", "file_path") if k in args), None)
        content_key = next((k for k in ("content", "text", "data") if k in args), None)
        if path_key and content_key:
            return f"{args[path_key]}\n{args[content_key]}"
        # bash.run: {command/script/cmd} → command
        cmd_key = next((k for k in ("command", "script", "cmd") if k in args), None)
        if cmd_key:
            return str(args[cmd_key])
        # file.read / echo / todo: single key
        if len(args) == 1:
            val = next(iter(args.values()))
            return str(val)
        # Multi-key but unknown pattern: dump as JSON
        return json.dumps(args)

    def _run_action(self, action: QAOAAction) -> str:
        if action.name == "retriever.search":
            if self.retriever is None:
                raise ValueError("retriever.search requires create_runtime(enable_rag=True).")
            docs = self.retriever.retrieve(action.input, top_k=3)
            return "\n\n".join(docs) if docs else "<no-documents>"
        return self.tools.call(action.name, action.input)

    # ── Message formatting for tool calls ─────────────────────────────

    @staticmethod
    def _format_assistant_tool_call(tc: ToolCallResult) -> dict:
        return {
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.name,
                    "arguments": json.dumps(tc.arguments),
                },
            }],
        }

    @staticmethod
    def _format_tool_result(tc: ToolCallResult, output: str) -> dict:
        return {
            "role": "tool",
            "tool_call_id": tc.id,
            "name": tc.name,
            "content": output,
        }

    # ── Context management ────────────────────────────────────────────

    def _context_too_large(self, messages: list[dict]) -> bool:
        total = sum(len(json.dumps(m, ensure_ascii=False)) for m in messages)
        return total > self.MAX_CONTEXT_CHARS

    def _trim_context(self, messages: list[dict]) -> list[dict]:
        """Remove oldest tool call+result PAIRS, keeping pairs intact."""
        # Find pair boundaries: (assistant_tool_calls_index, tool_result_index)
        pairs: list[tuple[int, int]] = []
        i = 0
        while i < len(messages):
            m = messages[i]
            if m.get("role") == "assistant" and m.get("tool_calls"):
                # Next message should be the tool result
                if i + 1 < len(messages) and messages[i + 1].get("role") == "tool":
                    pairs.append((i, i + 1))
                    i += 2
                    continue
            i += 1

        if len(pairs) <= 2:
            return messages

        # Remove oldest half of pairs, keep system + user messages
        remove_count = len(pairs) // 2
        remove_indices: set[int] = set()
        for tc_idx, tr_idx in pairs[:remove_count]:
            remove_indices.add(tc_idx)
            remove_indices.add(tr_idx)

        return [m for i, m in enumerate(messages) if i not in remove_indices]

    # ── Final answer generation ───────────────────────────────────────

    def _generate_final_answer(self, *, query: str,
                                observations: list[QAOAObservation],
                                skill) -> str:
        if observations:
            obs_text = "\n".join(f"{o.action_name}: {o.output}" for o in observations)
            prompt = f"Summarize findings and answer the query.\nQuery: {query}\nObservations:\n{obs_text}"
        else:
            prompt = f"Answer the query directly.\nQuery: {query}"
        try:
            return self.llm.complete_text(prompt)
        except Exception:
            return "Unable to generate answer after maximum turns."

    # ── Skill generation ──────────────────────────────────────────────

    def generate_skill(self, *, objective: str) -> QAOASkill:
        return self._generate_skill(objective)

    def _generate_skill(self, query: str) -> QAOASkill:
        list_specs = getattr(self.tools, "list_specs", None)
        tool_names: list[str] = []
        if callable(list_specs):
            tool_names = [s.name for s in list_specs() if not s.name.startswith("skill.")]

        prompt = (
            "Generate a concise execution skill for this query.\n"
            "Return strict JSON only with shape:\n"
            '{"name":"...", "objective":"...", "tools":["tool.a"], "steps":["step 1"]}\n\n'
            f"Query: {query}\n"
            f"Available tools: {json.dumps(tool_names, ensure_ascii=False)}"
        )
        raw = self.llm.complete_text(prompt)
        return self._parse_skill(raw=raw, fallback_query=query, available_tools=set(tool_names))

    @staticmethod
    def _parse_skill(*, raw: str, fallback_query: str, available_tools: set[str]) -> QAOASkill:
        candidate = raw.strip()
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = candidate[start:end + 1]
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            return QAOASkill(
                name="runtime-generated-skill",
                objective=fallback_query, tools=[], steps=["Answer the query directly."],
            )
        if not isinstance(parsed, dict):
            return QAOASkill(
                name="runtime-generated-skill",
                objective=fallback_query, tools=[], steps=["Answer the query directly."],
            )
        name = str(parsed.get("name", "runtime-generated-skill")).strip() or "runtime-generated-skill"
        objective = str(parsed.get("objective", fallback_query)).strip() or fallback_query
        raw_tools = parsed.get("tools", [])
        tools = [str(t).strip() for t in raw_tools if str(t).strip() in available_tools] if isinstance(raw_tools, list) else []
        raw_steps = parsed.get("steps", [])
        steps = [str(s).strip() for s in raw_steps if str(s).strip()] if isinstance(raw_steps, list) else []
        if not steps:
            steps = ["Answer the query directly."]
        return QAOASkill(name=name, objective=objective, tools=tools, steps=steps)

    # ── Skill normalization ───────────────────────────────────────────

    @staticmethod
    def _normalize_skill(skill) -> QAOASkill | None:
        """Accept SkillSpec or QAOASkill, return QAOASkill for engine use."""
        if skill is None:
            return None
        if isinstance(skill, QAOASkill):
            return skill
        # SkillSpec → QAOASkill conversion
        return QAOASkill(
            name=skill.name,
            objective=skill.description,
            tools=list(skill.allowed_tools),
            steps=[skill.instructions],
        )

    # ── Legacy plan_actions (kept for pipeline compat) ────────────────

    def plan_actions(self, query: str, skill: QAOASkill | None) -> list[QAOAAction]:
        """Legacy text-based planning. Prefer the native iterative loop in run()."""
        list_specs = getattr(self.tools, "list_specs", None)
        if not callable(list_specs):
            return []
        specs = list_specs()
        if not specs:
            return []
        tool_schema = [
            {"name": s.name, "description": s.description,
             "input_contract": s.input_contract, "tags": list(s.tags)}
            for s in specs if not s.name.startswith("skill.")
        ]
        planner_prompt = (
            "You are a tool planner. Pick up to 3 tools that help answer the query.\n"
            "Return strict JSON only in this shape:\n"
            '{"actions":[{"name":"tool.name","input":"payload"}]}\n'
            "If no tool is needed return: {\"actions\":[]}\n\n"
            f"Query: {query}\n"
            f"Skill: {json.dumps({'name': skill.name, 'objective': skill.objective, 'tools': skill.tools, 'steps': skill.steps}, ensure_ascii=False) if skill is not None else '<none>'}\n"
            f"Tools: {json.dumps(tool_schema, ensure_ascii=False)}"
        )
        planned_raw = self.llm.complete_text(planner_prompt)
        return self._parse_actions(planned_raw=planned_raw, allowed_names={s.name for s in specs})

    @staticmethod
    def _parse_actions(*, planned_raw: str, allowed_names: set[str]) -> list[QAOAAction]:
        candidate = planned_raw.strip()
        if not candidate:
            return []
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = candidate[start:end + 1]
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            return []
        raw_actions = parsed.get("actions", [])
        if not isinstance(raw_actions, list):
            return []
        actions: list[QAOAAction] = []
        for raw_action in raw_actions:
            if not isinstance(raw_action, dict):
                continue
            name = str(raw_action.get("name", "")).strip()
            payload = str(raw_action.get("input", "")).strip()
            if name == "" or name not in allowed_names:
                continue
            actions.append(QAOAAction(name=name, input=payload))
            if len(actions) >= 3:
                break
        return actions
