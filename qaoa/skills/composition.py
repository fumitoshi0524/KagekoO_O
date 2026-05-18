"""Skill composition — merge overlapping skills and compose skill pipelines."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..types import SkillSpec


@dataclass(slots=True, frozen=True, kw_only=True)
class ComposedSkill:
    """Result of composing multiple skills together."""
    name: str
    description: str
    instructions: str
    combined_tools: list[str]
    combined_permissions: list[str]
    sources: list[str]  # names of source skills


def merge_skills(skills: list[SkillSpec], *, name: str | None = None) -> SkillSpec | None:
    """Merge overlapping skills into one. Combines tools, permissions, and instructions.

    Returns None if the skills have incompatible domains (different domains).
    """
    if not skills:
        return None
    if len(skills) == 1:
        return skills[0]

    domains = {s.metadata.get("domain", "") for s in skills}
    if len(domains) > 1:
        # Can't merge skills from different domains
        return None

    merged_name = name or "+".join(s.name for s in skills)[:40]
    merged_desc = f"Merged skill: {', '.join(s.description for s in skills)}"[:200]
    merged_category = _most_common([s.metadata.get("category", "") for s in skills]) or "operations"

    all_tools: list[str] = []
    seen_tools: set[str] = set()
    for s in skills:
        for t in s.allowed_tools:
            if t not in seen_tools:
                all_tools.append(t)
                seen_tools.add(t)

    all_perms: list[str] = []
    seen_perms: set[str] = set()
    for s in skills:
        for p in s.permissions:
            if p not in seen_perms:
                all_perms.append(p)
                seen_perms.add(p)

    # Combine instructions
    instruction_parts: list[str] = []
    for i, s in enumerate(skills, 1):
        instruction_parts.append(f"## Phase {i}: {s.name}\n{s.instructions}")
    merged_instructions = "\n\n".join(instruction_parts)

    return SkillSpec(
        name=merged_name,
        description=merged_desc,
        instructions=merged_instructions,
        allowed_tools=all_tools,
        permissions=all_perms,
        metadata={
            "category": merged_category,
            "domain": skills[0].metadata.get("domain", "technology"),
            "sources": [s.name for s in skills],
            "composition_type": "merge",
        },
        format="qaoa-uni-tool-call",
    )


def compose_pipeline(skills: list[SkillSpec], *, name: str | None = None) -> SkillSpec | None:
    """Compose skills into a sequential pipeline. Each skill feeds into the next.

    The pipeline is valid when skills share compatible tool interfaces:
    earlier skills' output tools match later skills' input needs.
    """
    if not skills:
        return None
    if len(skills) == 1:
        return skills[0]

    pipeline_name = name or "→".join(s.name for s in skills)[:40]
    pipeline_desc = f"Pipeline: {' → '.join(s.name for s in skills)}"

    all_tools: list[str] = []
    seen: set[str] = set()
    for s in skills:
        for t in s.allowed_tools:
            if t not in seen:
                all_tools.append(t)
                seen.add(t)

    all_perms: list[str] = []
    seen_p: set[str] = set()
    for s in skills:
        for p in s.permissions:
            if p not in seen_p:
                all_perms.append(p)
                seen_p.add(p)

    # Pipeline instructions: sequential phases
    parts: list[str] = [f"# Pipeline: {pipeline_name}"]
    for i, s in enumerate(skills, 1):
        parts.append(f"## Step {i}: {s.name}")
        parts.append(s.instructions)
        parts.append(f"After completing {s.name}, proceed to the next step.\n")
    pipeline_instructions = "\n\n".join(parts)

    return SkillSpec(
        name=pipeline_name,
        description=pipeline_desc,
        instructions=pipeline_instructions,
        allowed_tools=all_tools,
        permissions=all_perms,
        metadata={
            "category": "operations",
            "domain": skills[0].metadata.get("domain", "technology"),
            "sources": [s.name for s in skills],
            "composition_type": "pipeline",
        },
        format="qaoa-uni-tool-call",
    )


def find_overlapping(skills: list[SkillSpec]) -> list[tuple[SkillSpec, SkillSpec]]:
    """Find pairs of skills that overlap in domain and tool usage."""
    pairs: list[tuple[SkillSpec, SkillSpec]] = []
    for i in range(len(skills)):
        for j in range(i + 1, len(skills)):
            a, b = skills[i], skills[j]
            if a.metadata.get("domain") != b.metadata.get("domain"):
                continue
            a_tools = set(a.allowed_tools)
            b_tools = set(b.allowed_tools)
            overlap = len(a_tools & b_tools)
            total = len(a_tools | b_tools)
            if total > 0 and overlap / total >= 0.3:  # 30% tool overlap
                pairs.append((a, b))
    return pairs


def _most_common(values: list[str]) -> str | None:
    if not values:
        return None
    from collections import Counter
    return Counter(values).most_common(1)[0][0]
