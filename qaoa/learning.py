"""QAOA data pipeline utilities: trajectory generation, export, and evaluation."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re

from .types import QAOAAction, QAOAObservation, QAOASkill, QAOATurn


_SPACE_PATTERN = re.compile(r"\s+")


@dataclass(slots=True, frozen=True, kw_only=True)
class QAOAEvalMetrics:
    function_call_precision: float
    function_call_recall: float
    function_call_f1: float
    turn_exact_match: float
    conversation_exact_match: float
    predicted_calls: int
    reference_calls: int
    matched_calls: int
    matched_turns: int
    compared_turns: int
    matched_conversations: int
    compared_conversations: int


def synthesize_qaoa_turns(
    *,
    tool_specs: list[object],
    examples_per_tool: int = 2,
) -> list[QAOATurn]:
    if examples_per_tool <= 0:
        raise ValueError("examples_per_tool must be > 0.")
    turns: list[QAOATurn] = []
    for spec in tool_specs:
        name = str(getattr(spec, "name", "")).strip()
        if name == "":
            continue
        for example_index in range(examples_per_tool):
            payload = _sample_payload(name=name, spec=spec, example_index=example_index)
            turns.append(
                QAOATurn(
                    query=_sample_query(name=name, spec=spec, payload=payload),
                    actions=[QAOAAction(name=name, input=payload)],
                    observations=[],
                    answer="",
                )
            )
    return turns


def export_qaoa_jsonl(*, turns: list[QAOATurn], output_path: Path) -> None:
    conversations = {f"conv-{index:06d}": [turn] for index, turn in enumerate(turns)}
    export_qaoa_conversations_jsonl(conversations=conversations, output_path=output_path)


def export_qaoa_conversations_jsonl(
    *, conversations: dict[str, list[QAOATurn]], output_path: Path
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for conversation_id in sorted(conversations):
        turns = conversations[conversation_id]
        for turn_index, turn in enumerate(turns):
            record = {
                "conversation_id": conversation_id,
                "turn_index": turn_index,
                "query": turn.query,
                "skill": (
                    {
                        "name": turn.skill.name,
                        "objective": turn.skill.objective,
                        "tools": turn.skill.tools,
                        "steps": turn.skill.steps,
                    }
                    if turn.skill is not None
                    else None
                ),
                "actions": [{"name": action.name, "input": action.input} for action in turn.actions],
                "observations": [
                    {"action_name": observation.action_name, "output": observation.output}
                    for observation in turn.observations
                ],
                "answer": turn.answer,
            }
            lines.append(json.dumps(record, ensure_ascii=False))
    output_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def load_qaoa_jsonl(path: Path) -> dict[str, list[QAOATurn]]:
    if not path.exists():
        raise FileNotFoundError(f"QAOA dataset not found: {path}")
    conversations_with_index: dict[str, list[tuple[int, QAOATurn]]] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if stripped == "":
            continue
        try:
            item = json.loads(stripped)
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid JSON at {path}:{line_number}: {error.msg}") from error
        conv_id = str(item.get("conversation_id", f"conv-{line_number:06d}"))
        actions = [
            QAOAAction(name=str(action.get("name", "")), input=str(action.get("input", "")))
            for action in item.get("actions", [])
            if isinstance(action, dict)
        ]
        observations = [
            QAOAObservation(
                action_name=str(observation.get("action_name", "")),
                output=str(observation.get("output", "")),
            )
            for observation in item.get("observations", [])
            if isinstance(observation, dict)
        ]
        raw_skill = item.get("skill")
        skill = None
        if isinstance(raw_skill, dict):
            skill = QAOASkill(
                name=str(raw_skill.get("name", "")).strip() or "runtime-generated-skill",
                objective=str(raw_skill.get("objective", "")).strip(),
                tools=[
                    str(tool).strip()
                    for tool in raw_skill.get("tools", [])
                    if str(tool).strip() != ""
                ]
                if isinstance(raw_skill.get("tools", []), list)
                else [],
                steps=[
                    str(step).strip()
                    for step in raw_skill.get("steps", [])
                    if str(step).strip() != ""
                ]
                if isinstance(raw_skill.get("steps", []), list)
                else [],
            )
        turn = QAOATurn(
            query=str(item.get("query", "")),
            skill=skill,
            actions=actions,
            observations=observations,
            answer=str(item.get("answer", "")),
        )
        turn_index = int(item.get("turn_index", 0))
        conversations_with_index.setdefault(conv_id, []).append((turn_index, turn))
    conversations: dict[str, list[QAOATurn]] = {}
    for conv_id, indexed_turns in conversations_with_index.items():
        indexed_turns.sort(key=lambda pair: pair[0])
        conversations[conv_id] = [turn for _, turn in indexed_turns]
    return conversations


def export_sft_jsonl(*, turns: list[QAOATurn], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for turn in turns:
        prompt = _render_qaoa_prompt(turn.query, turn.actions, turn.observations)
        target = turn.answer
        lines.append(
            json.dumps(
                {
                    "prompt": prompt,
                    "completion": target,
                },
                ensure_ascii=False,
            )
        )
    output_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def evaluate_qaoa_predictions(
    *,
    reference: dict[str, list[QAOATurn]],
    predicted: dict[str, list[QAOATurn]],
) -> QAOAEvalMetrics:
    conv_ids = sorted(set(reference) & set(predicted))
    compared_conversations = len(conv_ids)
    matched_conversations = 0

    predicted_calls = 0
    reference_calls = 0
    matched_calls = 0
    compared_turns = 0
    matched_turns = 0

    for conv_id in conv_ids:
        ref_turns = reference[conv_id]
        pred_turns = predicted[conv_id]
        turn_count = min(len(ref_turns), len(pred_turns))
        conversation_ok = len(ref_turns) == len(pred_turns)

        for i in range(turn_count):
            compared_turns += 1
            ref = ref_turns[i]
            pred = pred_turns[i]
            ref_calls = [(a.name, a.input) for a in ref.actions]
            pred_calls = [(a.name, a.input) for a in pred.actions]
            reference_calls += len(ref_calls)
            predicted_calls += len(pred_calls)
            matched_calls += _count_multiset_intersection(ref_calls, pred_calls)

            if _turn_exact(ref, pred):
                matched_turns += 1
            else:
                conversation_ok = False

        if len(ref_turns) != len(pred_turns):
            reference_calls += sum(len(turn.actions) for turn in ref_turns[turn_count:])
            predicted_calls += sum(len(turn.actions) for turn in pred_turns[turn_count:])
            conversation_ok = False

        if conversation_ok:
            matched_conversations += 1

    precision = _safe_div(matched_calls, predicted_calls)
    recall = _safe_div(matched_calls, reference_calls)
    f1 = _safe_div(2 * precision * recall, precision + recall) if (precision + recall) > 0 else 0.0

    return QAOAEvalMetrics(
        function_call_precision=precision,
        function_call_recall=recall,
        function_call_f1=f1,
        turn_exact_match=_safe_div(matched_turns, compared_turns),
        conversation_exact_match=_safe_div(matched_conversations, compared_conversations),
        predicted_calls=predicted_calls,
        reference_calls=reference_calls,
        matched_calls=matched_calls,
        matched_turns=matched_turns,
        compared_turns=compared_turns,
        matched_conversations=matched_conversations,
        compared_conversations=compared_conversations,
    )


def load_toolset_json(path: Path) -> list[dict[str, object]]:
    """Load tools from a UniToolCall-format toolset.json file.

    Returns a list of tool dicts with keys: name, description, inputSchema, category, domain.
    """
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        # UniToolCall format: {"1": {...}, "2": {...}} or array
        return [v for v in data.values() if isinstance(v, dict)]
    raise ValueError(f"Unsupported toolset format in {path}")


def export_conversations_jsonl(
    *, turns: list[dict[str, object]], output_path: Path,
) -> None:
    """Export QAOA turns in UniToolCall conversation JSONL format.

    Each line is a JSON object with: conversations, system, tools.
    Uses the _conv_format field if present, otherwise builds from actions/observations.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    system_prompt = (
        "# Role\n\nYou are an AI assistant capable of calling various functions to help users solve their problems.\n\n"
        "# Tool Selection\n\n**Important**: The available function signatures are provided in the <tools></tools> section. "
        "You must carefully select one or more appropriate tools from this section that can solve the user's request.\n\n"
        "# Output Rules\n\n"
        "## 1. Function Call Format\nWhen you need to call a function, output only one function call per round:\n"
        "<tool_call>\n{\"name\": <function-name>, \"arguments\": <args-json-object>}\n</tool_call>\n\n"
        "## 2. Answer Format\nWhen all necessary tools have been called, provide the final answer:\n"
        "<answer>\nYour final answer here\n</answer>"
    )
    lines: list[str] = []
    for turn in turns:
        conv_format = turn.get("_conv_format")
        if isinstance(conv_format, list):
            conversations = conv_format
        else:
            conversations = _build_conv_format(turn)
        tool_name = str(turn.get("_tool_name", turn.get("actions", [{}])[0].get("name", "") if turn.get("actions") else ""))
        tools_json = json.dumps([{"name": tool_name}], ensure_ascii=False)
        record = {
            "conversations": conversations,
            "system": system_prompt,
            "tools": tools_json,
        }
        lines.append(json.dumps(record, ensure_ascii=False))
    output_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def load_conversations_jsonl(path: Path) -> list[dict[str, object]]:
    """Load QAOA data from UniToolCall conversation JSONL format.

    Returns a list of records, each with conversations, system, tools fields.
    """
    if not path.exists():
        raise FileNotFoundError(f"QAOA conversation file not found: {path}")
    records: list[dict[str, object]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if stripped == "":
            continue
        try:
            item = json.loads(stripped)
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid JSON at {path}:{line_number}: {error.msg}") from error
        records.append(item)
    return records


def _build_conv_format(turn: dict[str, object]) -> list[dict[str, str]]:
    conv: list[dict[str, str]] = []
    query = str(turn.get("query", ""))
    conv.append({"from": "human", "value": query})
    actions = turn.get("actions", [])
    observations = turn.get("observations", [])
    if isinstance(actions, list):
        for i, action in enumerate(actions):
            if isinstance(action, dict):
                name = str(action.get("name", ""))
                inp = str(action.get("input", ""))
                fc_value = json.dumps({"name": name, "arguments": _parse_args(inp)}, ensure_ascii=False)
                conv.append({"from": "function_call", "value": fc_value})
                if isinstance(observations, list) and i < len(observations):
                    obs = observations[i]
                    if isinstance(obs, dict):
                        conv.append({"from": "observation", "value": str(obs.get("output", ""))})
    answer = str(turn.get("answer", ""))
    conv.append({"from": "gpt", "value": answer})
    return conv


def _parse_args(input_str: str) -> dict[str, object]:
    try:
        parsed = json.loads(input_str)
        return parsed if isinstance(parsed, dict) else {"value": input_str}
    except (json.JSONDecodeError, TypeError):
        return {"value": input_str}


def _count_multiset_intersection(left: list[tuple[str, str]], right: list[tuple[str, str]]) -> int:
    remaining = list(right)
    matched = 0
    for item in left:
        try:
            idx = remaining.index(item)
        except ValueError:
            continue
        matched += 1
        del remaining[idx]
    return matched


def _turn_exact(reference: QAOATurn, predicted: QAOATurn) -> bool:
    if _normalize_text(reference.query) != _normalize_text(predicted.query):
        return False
    if _normalize_text(reference.answer) != _normalize_text(predicted.answer):
        return False
    if not _skill_exact(reference.skill, predicted.skill):
        return False
    ref_actions = [(a.name, _normalize_text(a.input)) for a in reference.actions]
    pred_actions = [(a.name, _normalize_text(a.input)) for a in predicted.actions]
    if ref_actions != pred_actions:
        return False
    ref_observations = [(o.action_name, _normalize_text(o.output)) for o in reference.observations]
    pred_observations = [(o.action_name, _normalize_text(o.output)) for o in predicted.observations]
    return ref_observations == pred_observations


def _skill_exact(reference: QAOASkill | None, predicted: QAOASkill | None) -> bool:
    if reference is None and predicted is None:
        return True
    if reference is None or predicted is None:
        return False
    if _normalize_text(reference.name) != _normalize_text(predicted.name):
        return False
    if _normalize_text(reference.objective) != _normalize_text(predicted.objective):
        return False
    ref_tools = [_normalize_text(tool) for tool in reference.tools]
    pred_tools = [_normalize_text(tool) for tool in predicted.tools]
    if ref_tools != pred_tools:
        return False
    ref_steps = [_normalize_text(step) for step in reference.steps]
    pred_steps = [_normalize_text(step) for step in predicted.steps]
    return ref_steps == pred_steps


def _normalize_text(value: str) -> str:
    return _SPACE_PATTERN.sub(" ", value.strip().lower())


def _safe_div(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _sample_query(*, name: str, spec: object, payload: str) -> str:
    description = str(getattr(spec, "description", "")).strip()
    if description:
        return f"Use `{name}` to complete this: {description}"
    return f"Use `{name}` with payload: {payload}"


def _sample_payload(*, name: str, spec: object, example_index: int) -> str:
    tags = tuple(str(tag).lower() for tag in getattr(spec, "tags", ()))
    if "filesystem" in tags and "read" in tags:
        return "README.md"
    if "filesystem" in tags and "write" in tags:
        return f"qaoa_dataset_example_{example_index + 1}.txt\nsynthetic example"
    if "skills" in tags:
        return ""
    if "retrieval" in tags:
        if "write" in tags:
            return "QAOA training note one\nQAOA training note two"
        return "qaoa training notes"
    if name == "echo":
        return f"synthetic-echo-{example_index + 1}"
    return f"sample-input-{example_index + 1}"


def _render_qaoa_prompt(
    query: str, actions: list[QAOAAction], observations: list[QAOAObservation]
) -> str:
    parts = [f"Query: {query}"]
    if actions:
        parts.append(
            "Actions:\n"
            + "\n".join(f"- {action.name}({action.input})" for action in actions)
        )
    if observations:
        parts.append(
            "Observations:\n"
            + "\n".join(
                f"- {observation.action_name}: {observation.output}"
                for observation in observations
            )
        )
    parts.append("Answer:")
    return "\n\n".join(parts)
