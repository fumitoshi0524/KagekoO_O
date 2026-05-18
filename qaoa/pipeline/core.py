"""Unified generation pipeline for tools and skills — UniToolCall-aligned."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..adapters.llm import create_llm_adapter
from ..types import APPLICATION_DOMAINS, FUNCTIONAL_CATEGORIES


@dataclass(slots=True, frozen=True, kw_only=True)
class PipelineResult:
    success: bool
    output_path: Path | None = None
    content: str = ""
    errors: list[str] = field(default_factory=list)


@dataclass(slots=True, frozen=True, kw_only=True)
class QAOADataResult:
    success: bool
    turns: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass(slots=True, frozen=True, kw_only=True)
class QualityEvalResult:
    passed: bool
    scores: dict[str, float] = field(default_factory=dict)
    reason: str = ""
    details: dict[str, Any] = field(default_factory=dict)


class PipelineCore:
    """Core pipeline for generating tools and skills — aligned with UniToolCall."""

    def __init__(self, *, provider: str, api_key: str, model: str | None = None, base_url: str | None = None) -> None:
        self.llm = create_llm_adapter(
            provider=provider,
            api_key=api_key,
            model=model,
            base_url=base_url,
        )

    # ── Tool Generation ──────────────────────────────────────────────

    def generate_tool(
        self,
        *,
        spec: str,
        name: str,
        category: str = "operations",
        domain: str = "technology",
        output_dir: str | Path,
    ) -> PipelineResult:
        """Generate a single tool module from a natural-language specification."""
        if category not in FUNCTIONAL_CATEGORIES:
            return PipelineResult(success=False, errors=[f"Invalid category '{category}'. Must be one of: {FUNCTIONAL_CATEGORIES}"])
        if domain not in APPLICATION_DOMAINS:
            return PipelineResult(success=False, errors=[f"Invalid domain '{domain}'. Must be one of: {APPLICATION_DOMAINS}"])

        prompt = self._tool_generation_prompt(spec=spec, name=name, category=category, domain=domain)
        raw = self.llm.complete(prompt)
        parsed = self._extract_json(raw)
        if parsed is None:
            return PipelineResult(success=False, errors=["Failed to parse LLM response as JSON."])

        required = ["description", "schema", "implementation"]
        missing = [f for f in required if f not in parsed]
        if missing:
            return PipelineResult(success=False, errors=[f"Missing fields: {missing}"])

        risk_level = str(parsed.get("risk_level", "read")).strip().lower()
        if risk_level not in ("read", "write", "destructive"):
            risk_level = "read"

        module_content = self._render_tool_module(
            name=name, category=category, domain=domain,
            description=str(parsed.get("description", "")),
            schema=parsed.get("schema", {}),
            implementation=str(parsed.get("implementation", "")),
            risk_level=risk_level,
        )
        output_path = Path(output_dir) / f"{name.replace('.', '_')}.py"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(module_content, encoding="utf-8")
        return PipelineResult(success=True, output_path=output_path, content=module_content)

    def generate_tool_batch(
        self,
        *,
        specs: list[dict[str, str]],
        output_dir: str | Path,
    ) -> list[PipelineResult]:
        """Generate multiple tools from a list of {name, spec, category, domain} dicts."""
        results: list[PipelineResult] = []
        for item in specs:
            result = self.generate_tool(
                spec=item.get("spec", item.get("name", "")),
                name=item["name"],
                category=item.get("category", "operations"),
                domain=item.get("domain", "technology"),
                output_dir=output_dir,
            )
            results.append(result)
        return results

    # ── QAOA Data Generation ─────────────────────────────────────────

    def generate_qaoa_single_hop(
        self,
        *,
        tool_specs: list[dict[str, Any]],
        count: int = 10,
    ) -> QAOADataResult:
        """Generate single-hop QAOA training data (1 tool call per query)."""
        if not tool_specs:
            return QAOADataResult(success=False, errors=["No tool specs provided."])

        turns: list[dict[str, Any]] = []
        for i in range(count):
            tool = tool_specs[i % len(tool_specs)]
            prompt = self._single_hop_prompt(tool)
            raw = self.llm.complete(prompt)
            parsed = self._extract_json(raw)
            if parsed is None:
                continue
            turn = self._build_conversation_record(
                conv_id=i,
                turn_index=0,
                human=parsed.get("query", ""),
                tool_name=tool["name"],
                tool_args=parsed.get("arguments", {}),
                observation=parsed.get("observation", ""),
                answer=parsed.get("answer", ""),
            )
            turn["_tool_name"] = tool["name"]
            turns.append(turn)
        return QAOADataResult(success=len(turns) > 0, turns=turns)

    def generate_qaoa_multi_hop(
        self,
        *,
        tool_specs: list[dict[str, Any]],
        count: int = 10,
        min_steps: int = 2,
        max_steps: int = 5,
    ) -> QAOADataResult:
        """Generate multi-hop QAOA training data (sequential tool calls)."""
        if len(tool_specs) < 2:
            return QAOADataResult(success=False, errors=["Need at least 2 tool specs for multi-hop."])

        turns: list[dict[str, Any]] = []
        for i in range(count):
            num_steps = min(min_steps + (i % (max_steps - min_steps + 1)), len(tool_specs))
            selected = [tool_specs[j % len(tool_specs)] for j in range(num_steps)]
            prompt = self._multi_hop_prompt(selected)
            raw = self.llm.complete(prompt)
            parsed = self._extract_json(raw)
            if parsed is None:
                continue
            turn = self._build_multi_hop_record(
                conv_id=i,
                data=parsed,
                tools=selected,
            )
            turns.append(turn)
        return QAOADataResult(success=len(turns) > 0, turns=turns)

    def generate_qaoa_multi_turn(
        self,
        *,
        tool_specs: list[dict[str, Any]],
        count: int = 5,
        min_turns: int = 2,
        max_turns: int = 4,
    ) -> QAOADataResult:
        """Generate multi-turn QAOA training data (stateful dialogue)."""
        if not tool_specs:
            return QAOADataResult(success=False, errors=["No tool specs provided."])

        turns: list[dict[str, Any]] = []
        for i in range(count):
            num_turns = min(min_turns + (i % (max_turns - min_turns + 1)), 4)
            selected_pool = [tool_specs[j % len(tool_specs)] for j in range(min(num_turns * 2, len(tool_specs)))]
            prompt = self._multi_turn_prompt(selected_pool, num_turns=num_turns)
            raw = self.llm.complete(prompt)
            parsed = self._extract_json(raw)
            if parsed is None:
                continue
            turn = self._build_multi_turn_record(conv_id=i, data=parsed)
            turns.append(turn)
        return QAOADataResult(success=len(turns) > 0, turns=turns)

    # ── Quality Evaluation ───────────────────────────────────────────

    def evaluate_query_quality(self, *, query: str, tool_spec: dict[str, Any]) -> QualityEvalResult:
        """Evaluate query quality: toolfit, clarity, naturalness."""
        prompt = (
            "Evaluate this query for tool-use quality. Score each dimension 1-10.\n\n"
            f"Tool: {json.dumps(tool_spec, ensure_ascii=False)}\n"
            f"Query: {query}\n\n"
            "Return JSON: {\"toolfit\": <1-10>, \"clarity\": <1-10>, \"naturalness\": <1-10>, \"reason\": \"<brief>\"}"
        )
        raw = self.llm.complete(prompt)
        parsed = self._extract_json(raw) or {}
        scores = {
            "toolfit": float(parsed.get("toolfit", 0)),
            "clarity": float(parsed.get("clarity", 0)),
            "naturalness": float(parsed.get("naturalness", 0)),
        }
        avg = sum(scores.values()) / 3 if scores else 0
        passed = avg >= 7.0
        return QualityEvalResult(
            passed=passed,
            scores=scores,
            reason=str(parsed.get("reason", "")),
            details=parsed,
        )

    def evaluate_trajectory_quality(
        self, *, query: str, tool_name: str, args: dict[str, Any],
        observation: str, answer: str, tool_spec: dict[str, Any],
    ) -> QualityEvalResult:
        """Evaluate trajectory quality: success, grounding, efficiency."""
        prompt = (
            "Evaluate this tool-use trajectory. Score each dimension 1-10.\n\n"
            f"Tool: {json.dumps(tool_spec, ensure_ascii=False)}\n"
            f"Query: {query}\n"
            f"Tool call: {tool_name}({json.dumps(args, ensure_ascii=False)})\n"
            f"Observation: {observation}\n"
            f"Answer: {answer}\n\n"
            "Return JSON: {\"success\": <1-10>, \"grounding\": <1-10>, \"efficiency\": <1-10>, \"reason\": \"<brief>\"}"
        )
        raw = self.llm.complete(prompt)
        parsed = self._extract_json(raw) or {}
        scores = {
            "success": float(parsed.get("success", 0)),
            "grounding": float(parsed.get("grounding", 0)),
            "efficiency": float(parsed.get("efficiency", 0)),
        }
        avg = sum(scores.values()) / 3 if scores else 0
        passed = avg >= 7.0
        return QualityEvalResult(
            passed=passed,
            scores=scores,
            reason=str(parsed.get("reason", "")),
            details=parsed,
        )

    # ── Skill Evaluation ─────────────────────────────────────────────

    def evaluate_skill(
        self,
        *,
        skill: "SkillSpec",
        benchmark_queries: list[str],
    ) -> "EvalScore":
        """Evaluate a skill against benchmark queries. Returns aggregated EvalScore."""
        from ..types import EvalScore
        scores: list[EvalScore] = []
        for query in benchmark_queries[:5]:
            tool_name = skill.allowed_tools[0] if skill.allowed_tools else "echo"
            tool_spec = {"name": tool_name, "description": skill.description}
            result = self.evaluate_query_quality(query=query, tool_spec=tool_spec)
            scores.append(EvalScore(
                toolfit=result.scores.get("toolfit", 0),
                clarity=result.scores.get("clarity", 0),
                naturalness=result.scores.get("naturalness", 0),
            ))
        if not scores:
            return EvalScore(toolfit=0, clarity=0, naturalness=0)
        return EvalScore(
            toolfit=sum(s.toolfit for s in scores) / len(scores),
            clarity=sum(s.clarity for s in scores) / len(scores),
            naturalness=sum(s.naturalness for s in scores) / len(scores),
        )

    # ── Skill Generation ─────────────────────────────────────────────

    def generate_skill(
        self,
        *,
        name: str,
        goal: str,
        output_dir: str | Path,
    ) -> PipelineResult:
        """Generate a skill document from a natural-language goal."""
        prompt = self._skill_generation_prompt(name=name, goal=goal)
        raw = self.llm.complete(prompt)
        parsed = self._extract_json(raw)
        if parsed is None:
            return PipelineResult(success=False, errors=["Failed to parse LLM response as JSON."])
        required = ["objective", "steps"]
        missing = [f for f in required if f not in parsed]
        if missing:
            return PipelineResult(success=False, errors=[f"Missing fields in generated skill: {missing}"])
        content = self._render_skill_document(name=name, data=parsed)
        output_path = Path(output_dir) / f"{name}.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
        return PipelineResult(success=True, output_path=output_path, content=content)

    # ── Prompt Templates ─────────────────────────────────────────────

    @staticmethod
    def _tool_generation_prompt(*, spec: str, name: str, category: str, domain: str) -> str:
        cat_defs = {
            "analysis": "Data analysis and insights (statistical analysis, trend analysis, data mining, predictive analysis, business intelligence)",
            "operations": "Business process operations (create, update, delete, workflow management, business logic execution)",
            "system": "System administration and maintenance (system configuration, user management, system monitoring, technical maintenance)",
            "visualization": "Data visualization and presentation (chart generation, report creation, data display, dashboard creation)",
            "search": "Information retrieval and search (full-text search, fuzzy search, index query, structured query, data lookup)",
            "generate": "Content and data generation (content generation, code generation, intelligent recommendation, AI generation, automated creation)",
        }
        dom_defs = {
            "finance": "Finance related (payment, investment, wealth management, insurance, trading)",
            "technology": "Technology and software development (programming, system management, software tools, IT infrastructure)",
            "education": "Education and learning (academic courses, training programs, educational content, learning management)",
            "healthcare": "Medical and health services (medical treatment, health monitoring, medical devices, healthcare management)",
            "entertainment": "Entertainment and media (music, games, film/TV, social entertainment, news, content creation)",
            "travel": "Travel and transportation (tourism, transportation, accommodation, attractions, travel planning)",
            "business": "Business management (enterprise operations, marketing, customer relations, business processes)",
            "lifestyle": "Daily life services (shopping, food, housekeeping, personal tools, consumer services)",
            "science": "Scientific research and analysis (research projects, scientific experiments, academic studies, data analysis)",
            "social": "Social communication and community (social networking, communication tools, community management, collaboration)",
            "sports": "Sports and fitness (sports activities, fitness training, sports events, athletic performance)",
            "environment": "Environment and sustainability (environmental protection, climate monitoring, ecology, sustainable development)",
            "culture": "Culture and arts (art, literature, history, cultural events, language learning, creative content)",
        }
        return (
            "You are a tool generator for an AI agent runtime following the UniToolCall standard. "
            "Generate a production-quality tool based on the specification.\n\n"
            f"Tool name: {name}\n"
            f"Category: {category} — {cat_defs.get(category, category)}\n"
            f"Domain: {domain} — {dom_defs.get(domain, domain)}\n"
            f"Specification: {spec}\n\n"
            "Requirements:\n"
            "- description: Clear one-sentence summary of core functionality using action verbs. Include key business entities and what the tool returns.\n"
            "- schema: JSON Schema object (type: object, with properties). Each property must have type, description (business meaning, format, constraints). Use enum for fixed option sets. Use examples field for format examples (NOT in description).\n"
            '- implementation: Complete Python function "def run(payload: str) -> str:" that parses JSON payload, executes logic, returns result string. Handle errors gracefully.\n'
            '- risk_level: "read" (no side effects), "write" (creates/modifies data), or "destructive" (deletes/executes code)\n\n'
            "Return strict JSON only:\n"
            '{"description": "...", "schema": {"type": "object", "properties": {...}, "required": [...]}, "implementation": "def run(payload: str) -> str:\\n    ...", "risk_level": "read"}'
        )

    @staticmethod
    def _single_hop_prompt(tool: dict[str, Any]) -> str:
        return (
            "Generate a single-hop QAOA trajectory for this tool.\n\n"
            f"Tool: {json.dumps(tool, ensure_ascii=False)}\n\n"
            "Create a realistic user query that requires exactly one call to this tool. "
            "Return strict JSON:\n"
            '{"query": "<natural language user request>", '
            '"arguments": {<valid tool arguments from query>}, '
            '"observation": "<simulated tool output as text>", '
            '"answer": "<natural language final answer to user>"}'
        )

    @staticmethod
    def _multi_hop_prompt(tools: list[dict[str, Any]]) -> str:
        tools_json = json.dumps([{"name": t["name"], "description": t.get("description", ""), "inputSchema": t.get("schema", t.get("inputSchema", {}))} for t in tools], ensure_ascii=False)
        return (
            "Generate a multi-hop QAOA trajectory using these tools sequentially.\n\n"
            f"Tools: {tools_json}\n\n"
            "The user query should require {n} sequential tool calls where later calls depend on earlier results. "
            "Return strict JSON:\n"
            '{{"query": "<user request>", '
            '"steps": [{{"tool": "<name>", "arguments": {{...}}, "observation": "<output>"}}], '
            '"answer": "<final answer>"}}'.format(n=len(tools))
        )

    @staticmethod
    def _multi_turn_prompt(tools: list[dict[str, Any]], num_turns: int) -> str:
        tools_json = json.dumps([{"name": t["name"], "description": t.get("description", ""), "inputSchema": t.get("schema", t.get("inputSchema", {}))} for t in tools], ensure_ascii=False)
        return (
            f"Generate a {num_turns}-turn QAOA dialogue using these tools.\n\n"
            f"Tools: {tools_json}\n\n"
            "Create a multi-turn conversation where each user turn builds on previous context (anchor linkage). "
            "Return strict JSON:\n"
            '{"turns": [{"user": "<turn query>", "steps": [{"tool": "<name>", "arguments": {}, "observation": "<output>"}], "assistant": "<turn response>"}]}'
        )

    @staticmethod
    def _skill_generation_prompt(*, name: str, goal: str) -> str:
        return (
            "You are a skill generator for an AI agent runtime. "
            "Generate a skill based on the following goal.\n\n"
            f"Skill name: {name}\n"
            f"Goal: {goal}\n\n"
            "Return strict JSON with these keys:\n"
            '- "objective": concise objective statement\n'
            '- "tools": list of tool names this skill may use\n'
            '- "steps": ordered list of execution steps\n'
            "\nExample: {\"objective\": \"...\", \"tools\": [\"file.read\", \"bash.run\"], \"steps\": [\"Step 1\", \"Step 2\"]}"
        )

    # ── Renderers ────────────────────────────────────────────────────

    @staticmethod
    def _render_tool_module(
        *, name: str, category: str, domain: str,
        description: str, schema: dict[str, Any],
        implementation: str, risk_level: str,
    ) -> str:
        impl = implementation.strip()
        if not impl.startswith("def run("):
            body_lines = impl.splitlines()
            indented_body = "\n".join(f"    {line}" for line in body_lines)
            impl = f'def run(payload: str) -> str:\n    """{description}"""\n{indented_body}'

        schema_json = json.dumps(schema, indent=4, ensure_ascii=False)

        def _py_str(s: str) -> str:
            return json.dumps(s, ensure_ascii=False)

        lines = [
            '"""Auto-generated tool module."""',
            "",
            "from __future__ import annotations",
            "",
            "import json",
            "",
            "",
            impl,
            "",
            "",
            "TOOL_SPEC = {",
            f'    "name": {_py_str(name)},',
            f'    "description": {_py_str(description)},',
            f'    "category": {_py_str(category)},',
            f'    "domain": {_py_str(domain)},',
            f'    "risk_level": {_py_str(risk_level)},',
            '    "schema": ' + schema_json + ",",
            "}",
        ]
        return "\n".join(lines) + "\n"

    @staticmethod
    def _render_skill_document(*, name: str, data: dict[str, Any]) -> str:
        lines = [
            "---",
            f"name: {name}",
            f"description: {data.get('objective', '')}",
            "tools:",
        ]
        for tool in data.get("tools", []):
            lines.append(f"  - {tool}")
        lines.append("---")
        lines.append("")
        lines.append(f"# {name}")
        lines.append("")
        lines.append("## Objective")
        lines.append("")
        lines.append(data.get("objective", ""))
        lines.append("")
        lines.append("## Steps")
        lines.append("")
        for i, step in enumerate(data.get("steps", []), start=1):
            lines.append(f"{i}. {step}")
        lines.append("")
        return "\n".join(lines)

    # ── Record Builders ──────────────────────────────────────────────

    @staticmethod
    def _build_conversation_record(
        *, conv_id: int, turn_index: int, human: str,
        tool_name: str, tool_args: dict[str, Any],
        observation: str, answer: str,
    ) -> dict[str, Any]:
        fc_value = json.dumps({"name": tool_name, "arguments": tool_args}, ensure_ascii=False)
        return {
            "conversation_id": f"conv-{conv_id:06d}",
            "turn_index": turn_index,
            "query": human,
            "actions": [{"name": tool_name, "input": json.dumps(tool_args, ensure_ascii=False)}],
            "observations": [{"action_name": tool_name, "output": observation}],
            "answer": answer,
            "_conv_format": [
                {"from": "human", "value": human},
                {"from": "function_call", "value": fc_value},
                {"from": "observation", "value": observation},
                {"from": "gpt", "value": answer},
            ],
        }

    @staticmethod
    def _build_multi_hop_record(
        *, conv_id: int, data: dict[str, Any],
        tools: list[dict[str, Any]],
    ) -> dict[str, Any]:
        query = str(data.get("query", ""))
        steps = data.get("steps", [])
        if not isinstance(steps, list):
            steps = []
        conv_format: list[dict[str, str]] = [{"from": "human", "value": query}]
        actions: list[dict[str, str]] = []
        observations: list[dict[str, str]] = []
        for step in steps:
            if not isinstance(step, dict):
                continue
            t_name = str(step.get("tool", ""))
            t_args = step.get("arguments", {})
            t_obs = str(step.get("observation", ""))
            fc_value = json.dumps({"name": t_name, "arguments": t_args}, ensure_ascii=False)
            conv_format.append({"from": "function_call", "value": fc_value})
            conv_format.append({"from": "observation", "value": t_obs})
            actions.append({"name": t_name, "input": json.dumps(t_args, ensure_ascii=False)})
            observations.append({"action_name": t_name, "output": t_obs})
        answer = str(data.get("answer", ""))
        conv_format.append({"from": "gpt", "value": answer})
        return {
            "conversation_id": f"conv-{conv_id:06d}",
            "turn_index": 0,
            "query": query,
            "actions": actions,
            "observations": observations,
            "answer": answer,
            "_conv_format": conv_format,
        }

    @staticmethod
    def _build_multi_turn_record(
        *, conv_id: int, data: dict[str, Any],
    ) -> dict[str, Any]:
        turns_data = data.get("turns", [])
        if not isinstance(turns_data, list):
            turns_data = []
        all_conv: list[dict[str, str]] = []
        qaoa_turns: list[dict[str, Any]] = []
        for t_idx, turn in enumerate(turns_data):
            if not isinstance(turn, dict):
                continue
            user_msg = str(turn.get("user", ""))
            all_conv.append({"from": "human", "value": user_msg})
            t_actions: list[dict[str, str]] = []
            t_observations: list[dict[str, str]] = []
            for step in (turn.get("steps", []) if isinstance(turn.get("steps"), list) else []):
                if not isinstance(step, dict):
                    continue
                t_name = str(step.get("tool", ""))
                t_args = step.get("arguments", {})
                t_obs = str(step.get("observation", ""))
                fc_value = json.dumps({"name": t_name, "arguments": t_args}, ensure_ascii=False)
                all_conv.append({"from": "function_call", "value": fc_value})
                all_conv.append({"from": "observation", "value": t_obs})
                t_actions.append({"name": t_name, "input": json.dumps(t_args, ensure_ascii=False)})
                t_observations.append({"action_name": t_name, "output": t_obs})
            assistant_msg = str(turn.get("assistant", ""))
            all_conv.append({"from": "gpt", "value": assistant_msg})
            qaoa_turns.append({
                "query": user_msg,
                "actions": t_actions,
                "observations": t_observations,
                "answer": assistant_msg,
            })
        return {
            "conversation_id": f"conv-{conv_id:06d}",
            "turns": qaoa_turns,
            "_conv_format": all_conv,
        }

    # ── JSON Helpers ─────────────────────────────────────────────────

    @staticmethod
    def _extract_json(raw: str) -> dict[str, Any] | None:
        candidate = raw.strip()
        if not candidate:
            return None
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = candidate[start : end + 1]
        try:
            parsed = json.loads(candidate)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None
