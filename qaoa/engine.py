"""QAOA agent execution engine."""

from __future__ import annotations

import json

from .types import QAOAAction, QAOAObservation, QAOASkill, QAOATurn, ToolUse


def _prompt(prefix: str, message: str) -> str:
    return f"{prefix}\nUser: {message}"


class QAOAEngine:
    def __init__(self, *, llm, tools, retriever=None, context: str = "") -> None:
        self.llm = llm
        self.tools = tools
        self.retriever = retriever
        self.context = context

    def _enrich_query(self, query: str) -> str:
        if self.context:
            return f"{self.context}\n\nQuery: {query}"
        return query

    def run(
        self,
        *,
        query: str,
        tool_plan: list[ToolUse] | None = None,
        skill: QAOASkill | None = None,
        allow_skill_generation: bool = False,
    ) -> tuple[QAOATurn, list[str]]:
        enriched_query = self._enrich_query(query)
        effective_skill = skill
        if effective_skill is None and allow_skill_generation:
            effective_skill = self._generate_skill(enriched_query)
        if tool_plan:
            actions = [QAOAAction(name=tool.name, input=tool.input) for tool in tool_plan]
            trace = ["qaoa:manual_actions"]
        else:
            actions = self.plan_actions(enriched_query, effective_skill)
            trace = ["qaoa:planned_actions"] if actions else ["qaoa:no_actions_planned"]

        if effective_skill is not None:
            trace = ["qaoa:skill_applied"] + trace
        if allow_skill_generation and skill is None and effective_skill is not None:
            trace = ["qaoa:skill_generated"] + trace

        observations: list[QAOAObservation] = []
        if actions:
            for action in actions:
                output = self._run_action(action)
                observations.append(
                    QAOAObservation(action_name=action.name, output=output)
                )
            observation_text = "\n".join(
                f"{item.action_name}: {item.output}" for item in observations
            )
            skill_objective = effective_skill.objective if effective_skill is not None else "<none>"
            skill_steps = " | ".join(effective_skill.steps) if effective_skill and effective_skill.steps else "<none>"
            answer = self.llm.complete(
                "Use the observations to answer the query.\n"
                f"Query: {query}\n"
                f"Skill objective: {skill_objective}\n"
                f"Skill steps: {skill_steps}\n"
                f"Observations:\n{observation_text}"
            )
            return (
                QAOATurn(
                    query=query,
                    skill=effective_skill,
                    actions=actions,
                    observations=observations,
                    answer=answer,
                ),
                trace + ["qaoa:actions_executed", "qaoa:completed"],
            )

        if effective_skill is not None:
            answer = self.llm.complete(
                _prompt(
                    "Answer clearly and directly using this skill context:\n"
                    f"Objective: {effective_skill.objective}\n"
                    f"Steps: {' | '.join(effective_skill.steps) if effective_skill.steps else '<none>'}",
                    query,
                )
            )
        else:
            answer = self.llm.complete(_prompt("Answer clearly and directly.", query))
        return (
            QAOATurn(query=query, skill=effective_skill, actions=[], observations=[], answer=answer),
            trace + ["qaoa:direct_answer", "qaoa:completed"],
        )

    def _run_action(self, action: QAOAAction) -> str:
        if action.name == "retriever.search":
            if self.retriever is None:
                raise ValueError("retriever.search requires create_runtime(enable_rag=True).")
            docs = self.retriever.retrieve(action.input, top_k=3)
            return "\n\n".join(docs) if docs else "<no-documents>"
        return self.tools.call(action.name, action.input)

    def plan_actions(self, query: str, skill: QAOASkill | None) -> list[QAOAAction]:
        list_specs = getattr(self.tools, "list_specs", None)
        if not callable(list_specs):
            return []
        specs = list_specs()
        if not specs:
            return []
        tool_schema = [
            {
                "name": spec.name,
                "description": spec.description,
                "input_contract": spec.input_contract,
                "tags": list(spec.tags),
            }
            for spec in specs
            if not spec.name.startswith("skill.")
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
        planned_raw = self.llm.complete(planner_prompt)
        return self._parse_actions(
            planned_raw=planned_raw, allowed_names={spec.name for spec in specs}
        )

    @staticmethod
    def _parse_actions(*, planned_raw: str, allowed_names: set[str]) -> list[QAOAAction]:
        candidate = planned_raw.strip()
        if not candidate:
            return []
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = candidate[start : end + 1]
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

    def generate_skill(self, *, objective: str) -> QAOASkill:
        return self._generate_skill(objective)

    def _generate_skill(self, query: str) -> QAOASkill:
        list_specs = getattr(self.tools, "list_specs", None)
        tool_names: list[str] = []
        if callable(list_specs):
            tool_names = [spec.name for spec in list_specs() if not spec.name.startswith("skill.")]
        prompt = (
            "Generate a concise execution skill for this query.\n"
            "Return strict JSON only with shape:\n"
            '{"name":"...", "objective":"...", "tools":["tool.a"], "steps":["step 1"]}\n\n'
            f"Query: {query}\n"
            f"Available tools: {json.dumps(tool_names, ensure_ascii=False)}"
        )
        raw = self.llm.complete(prompt)
        return self._parse_skill(raw=raw, fallback_query=query, available_tools=set(tool_names))

    @staticmethod
    def _parse_skill(*, raw: str, fallback_query: str, available_tools: set[str]) -> QAOASkill:
        candidate = raw.strip()
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = candidate[start : end + 1]
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            return QAOASkill(
                name="runtime-generated-skill",
                objective=fallback_query,
                tools=[],
                steps=["Answer the query directly."],
            )

        if not isinstance(parsed, dict):
            return QAOASkill(
                name="runtime-generated-skill",
                objective=fallback_query,
                tools=[],
                steps=["Answer the query directly."],
            )

        name = str(parsed.get("name", "runtime-generated-skill")).strip() or "runtime-generated-skill"
        objective = str(parsed.get("objective", fallback_query)).strip() or fallback_query
        raw_tools = parsed.get("tools", [])
        tools = [
            str(tool).strip()
            for tool in raw_tools
            if str(tool).strip() in available_tools
        ] if isinstance(raw_tools, list) else []
        raw_steps = parsed.get("steps", [])
        steps = [str(step).strip() for step in raw_steps if str(step).strip() != ""] if isinstance(raw_steps, list) else []
        if not steps:
            steps = ["Answer the query directly."]
        return QAOASkill(name=name, objective=objective, tools=tools, steps=steps)
