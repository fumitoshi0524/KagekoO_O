from __future__ import annotations

import json
from dataclasses import asdict

from .experience_models import ExperienceCapsule, ExperienceStep, ToolCallHint


def to_ecap_json(capsule: ExperienceCapsule) -> str:
    return json.dumps(asdict(capsule), ensure_ascii=False, indent=2) + "\n"


def to_ecap_markdown(capsule: ExperienceCapsule) -> str:
    c = capsule
    lines = [
        f"# {c.title or c.ecap_id}\n\n",
        f"- **ECAP ID:** `{c.ecap_id}`\n",
        f"- **Schema:** `{c.schema_version}`\n",
        f"- **Problem type:** `{c.problem_type}`\n",
        f"- **Model:** `{c.model_profile.source_provider}/{c.model_profile.source_model}`\n\n",
        "## Context\n\n",
        f"- Repo fingerprint: `{c.context.repo_fingerprint}`\n",
        f"- Language stack: {', '.join(c.context.language_stack) or '(unknown)'}\n",
    ]
    if c.context.constraints:
        lines.append("- Constraints:\n")
        lines.extend([f"  - {x}\n" for x in c.context.constraints])
    lines.append("\n## Solution Trace\n\n")
    if c.solution_trace.steps:
        for i, step in enumerate(c.solution_trace.steps, 1):
            if isinstance(step, ExperienceStep):
                t = f" [{step.step_type}]"
                tool = f" tool={step.tool_name}" if step.tool_name else ""
                lines.append(f"{i}. {step.summary}{t}{tool}\n")
            else:
                lines.append(f"{i}. {step}\n")
        lines.append("\n")
    if c.solution_trace.tool_sequence:
        parts: list[str] = []
        for one in c.solution_trace.tool_sequence:
            if isinstance(one, ToolCallHint):
                parts.append(f"{one.tool_name} x{one.count}")
            else:
                parts.append(str(one))
        lines.append(f"- Tool sequence: {', '.join(parts)}\n")
    if c.solution_trace.decision_rationale_summary:
        lines.append(f"- Decision rationale (summary): {c.solution_trace.decision_rationale_summary}\n")
    lines.append("\n## Outcome\n\n")
    lines.append(f"- Result: `{c.outcome.result}`\n")
    if c.outcome.verification:
        lines.append("- Verification:\n")
        lines.extend([f"  - {x}\n" for x in c.outcome.verification])
    if c.outcome.risk_left:
        lines.append("- Remaining risks:\n")
        lines.extend([f"  - {x}\n" for x in c.outcome.risk_left])
    lines.append("\n## Transfer\n\n")
    if c.transfer.applicability_conditions:
        lines.append("- Applicability:\n")
        lines.extend([f"  - {x}\n" for x in c.transfer.applicability_conditions])
    if c.transfer.target_model_hints:
        lines.append("- Target model hints:\n")
        lines.extend([f"  - {x}\n" for x in c.transfer.target_model_hints])
    if c.transfer.model_migration_rules:
        lines.append("- Migration rules:\n")
        lines.extend([f"  - {x}\n" for x in c.transfer.model_migration_rules])
    if c.transfer.anti_patterns:
        lines.append("- Anti-patterns:\n")
        lines.extend([f"  - {x}\n" for x in c.transfer.anti_patterns])
    lines.append("\n## Knowledge Triple\n\n")
    if c.knowledge_triple.instinct_ref.instinct_ids:
        lines.append("- Instinct refs:\n")
        lines.extend([f"  - {x}\n" for x in c.knowledge_triple.instinct_ref.instinct_ids])
    ef = c.knowledge_triple.experience_fn
    lines.append(
        f"- Experience function: type=`{ef.fn_type}` gap=`{ef.gap:.3f}` score=`{ef.score:.3f}` confidence=`{ef.confidence:.3f}` "
        f"ci=`[{ef.ci_lower:.3f},{ef.ci_upper:.3f}]` level=`{ef.effectiveness_level}`\n"
    )
    sr = c.knowledge_triple.skill_ref
    lines.append(f"- Skill ref: `{sr.skill_name or '-'}` version=`{sr.skill_version or '-'}` path=`{sr.skill_path or '-'}`\n")
    return "".join(lines)
