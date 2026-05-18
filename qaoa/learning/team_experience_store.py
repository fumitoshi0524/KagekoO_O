from __future__ import annotations

import json
import re
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from ..config.settings import Settings
from .paths import ensure_learning_dirs
from .store import write_snapshot
from .team_experience_migration import upgrade_tecap_v1_to_v2
from .team_experience_models import (
    TeamExperienceCapsule,
)


def _team_experience_dirs(settings: Settings) -> tuple[Path, Path]:
    p = ensure_learning_dirs(settings)
    root = p.root / "team-experience"
    caps = root / "capsules"
    exports = root / "exports"
    caps.mkdir(parents=True, exist_ok=True)
    exports.mkdir(parents=True, exist_ok=True)
    return caps, exports


def save_team_capsule(settings: Settings, capsule: TeamExperienceCapsule) -> Path:
    caps_dir, _ = _team_experience_dirs(settings)
    if not capsule.tecap_id:
        capsule.tecap_id = datetime.now().strftime("tecap-%Y%m%d-%H%M%S")
    now = datetime.now(timezone.utc).isoformat()
    if not capsule.governance.created_at:
        capsule.governance.created_at = now
    capsule.governance.updated_at = now
    out = caps_dir / f"{capsule.tecap_id}.json"
    out.write_text(json.dumps(asdict(capsule), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    snapshot_team_capsule_change(settings, "save", capsule)
    return out


def load_team_capsule(settings: Settings, tecap_id: str) -> TeamExperienceCapsule | None:
    caps_dir, _ = _team_experience_dirs(settings)
    path = caps_dir / f"{tecap_id}.json"
    if not path.exists():
        return None
    try:
        return team_capsule_from_dict(json.loads(path.read_text(encoding="utf-8")))
    except Exception:
        return None


def list_team_capsules(settings: Settings) -> list[TeamExperienceCapsule]:
    caps_dir, _ = _team_experience_dirs(settings)
    out: list[TeamExperienceCapsule] = []
    for f in sorted(caps_dir.glob("*.json")):
        try:
            out.append(team_capsule_from_dict(json.loads(f.read_text(encoding="utf-8"))))
        except Exception:
            continue
    return out


def _sanitize_text(s: str) -> str:
    s = re.sub(r"(/|[A-Za-z]:\\\\)[^\\s`'\"]+", "[PATH]", s)
    s = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+", "[EMAIL]", s)
    s = re.sub(r"([?&](token|key|secret)=)[^&\\s]+", r"\1[REDACTED]", s, flags=re.I)
    return s


def sanitize_tecap(c: TeamExperienceCapsule, *, level: str = "balanced") -> TeamExperienceCapsule:
    if level == "full":
        return c
    c.team_context.repo_fingerprint = _sanitize_text(c.team_context.repo_fingerprint)
    c.team_context.constraints = [_sanitize_text(x) for x in c.team_context.constraints]
    for p in c.participants:
        p.agent_id = _sanitize_text(p.agent_id)
        p.responsibility = _sanitize_text(p.responsibility)
    for st in c.collaboration_trace.steps:
        st.input_summary = _sanitize_text(st.input_summary)
        st.output_summary = _sanitize_text(st.output_summary)
        st.dependencies = [_sanitize_text(x) for x in st.dependencies]
    if level == "strict":
        c.team_context.repo_fingerprint = ""
        for p in c.participants:
            p.agent_id = ""
    c.governance.redaction_applied = True
    c.governance.privacy_level = level  # type: ignore[assignment]
    return c


def to_tecap_markdown(c: TeamExperienceCapsule) -> str:
    lines = [
        f"# {c.title or c.tecap_id}\n\n",
        f"- **TECAP ID:** `{c.tecap_id}`\n",
        f"- **Schema:** `{c.schema_version}`\n",
        f"- **Problem type:** `{c.problem_type}`\n",
        f"- **Objective:** {c.team_context.objective or '(none)'}\n\n",
        "## Team\n\n",
    ]
    for p in c.participants:
        lines.append(f"- `{p.agent_role or '?'}:{p.agent_id or '?'}` · {p.responsibility or '(no responsibility)'}\n")
    if c.team_context.constraints:
        lines.append("\n## Constraints\n\n")
        lines.extend([f"- {x}\n" for x in c.team_context.constraints])
    lines.append("\n## Collaboration Trace\n\n")
    for i, st in enumerate(c.collaboration_trace.steps, 1):
        lines.append(
            f"{i}. [{st.step_type}] owner=`{st.owner_agent}` handoff=`{st.handoff_to or '-'}`\n"
            f"   - input: {st.input_summary}\n"
            f"   - output: {st.output_summary}\n"
        )
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
        lines.append("- Applicability conditions:\n")
        lines.extend([f"  - {x}\n" for x in c.transfer.applicability_conditions])
    if c.transfer.team_migration_hints:
        lines.append("- Team migration hints:\n")
        lines.extend([f"  - {x}\n" for x in c.transfer.team_migration_hints])
    if c.coordination_patterns:
        lines.append("- Coordination patterns:\n")
        lines.extend([f"  - {x}\n" for x in c.coordination_patterns])
    if c.anti_patterns:
        lines.append("- Anti-patterns:\n")
        lines.extend([f"  - {x}\n" for x in c.anti_patterns])
    lines.append("\n## Team Review\n\n")
    lines.append(
        f"- Handoff success rate: `{c.coordination_metrics.handoff_success_rate:.2f}`\n"
        f"- Rework ratio: `{c.coordination_metrics.rework_ratio:.2f}`\n"
        f"- Escalation count: `{c.coordination_metrics.escalation_count}`\n"
        f"- Cycle time: `{c.coordination_metrics.cycle_time:.2f}`\n"
    )
    if c.match_explain:
        lines.append("- Match explain:\n")
        lines.extend([f"  - {x}\n" for x in c.match_explain])
    if c.quality_gates:
        lines.append("- Quality gates:\n")
        lines.extend([f"  - {x}\n" for x in c.quality_gates])
    if c.iteration_records:
        lines.append("- Iteration records:\n")
        for rec in c.iteration_records[-5:]:
            lines.append(
                "  - "
                f"iter={rec.iteration} goal={rec.iteration_goal or '-'} "
                f"gap_before={rec.gap_before:.3f} gap_after={rec.gap_after:.3f} gap_delta={rec.gap_delta:.3f} "
                f"deviation={rec.deviation_reason or '-'}\n"
            )
    lines.append("\n## Role Knowledge\n\n")
    if c.role_ecap_map:
        lines.append("- Role ECAP map:\n")
        lines.extend([f"  - {k}: {v or '-'}\n" for k, v in c.role_ecap_map.items()])
    lines.append(
        "- Team experience function: "
        f"type=`{c.team_experience_fn.fn_type}` "
        f"gap=`{c.team_experience_fn.gap:.3f}` "
        f"score=`{c.team_experience_fn.score:.3f}` "
        f"confidence=`{c.team_experience_fn.confidence:.3f}` "
        f"ci=`[{c.team_experience_fn.ci_lower:.3f},{c.team_experience_fn.ci_upper:.3f}]` "
        f"level=`{c.team_experience_fn.effectiveness_level}`\n"
    )
    lines.append(
        "- Role transfer policy: "
        f"source=`{c.role_transfer_policy.inheritance_source}` "
        f"threshold=`{c.role_transfer_policy.confidence_threshold:.2f}` "
        f"conflict=`{c.role_transfer_policy.conflict_rule}`\n"
    )
    return "".join(lines)


def export_team_capsule(
    settings: Settings,
    capsule: TeamExperienceCapsule,
    *,
    fmt: str,
    output_path: str = "",
    privacy_level: str = "balanced",
    v1_compatible: bool = False,
) -> Path:
    _, exports = _team_experience_dirs(settings)
    fmt = fmt.lower().strip()
    if fmt not in {"json", "md"}:
        raise ValueError("fmt must be json or md")
    ext = "json" if fmt == "json" else "md"
    out = Path(output_path).expanduser() if output_path else exports / f"{capsule.tecap_id}.{ext}"
    safe = sanitize_tecap(team_capsule_from_dict(asdict(capsule)), level=privacy_level)
    if fmt == "json":
        if v1_compatible:
            payload = _to_tecap_v1_payload(safe)
        else:
            payload = {
                **asdict(safe),
                "schema_meta": {
                    "schema_version": safe.schema_version,
                    "compatible_read": ["tecap-v1", "tecap-v2", "tecap-v3"],
                },
                "migration_hints": list(safe.transfer.team_migration_hints),
                "quality_score": _quality_score(safe),
                "match_explain": list(safe.match_explain),
            }
        text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    else:
        text = to_tecap_markdown(safe)
    out.write_text(text, encoding="utf-8")
    snapshot_team_capsule_change(settings, f"export-{fmt}", capsule)
    return out


def import_team_capsule_from_text(settings: Settings, text: str, *, force: bool = False) -> tuple[bool, str]:
    try:
        obj = json.loads(text)
    except Exception as e:
        return False, f"Invalid TECAP JSON: {e}"
    cap = team_capsule_from_dict(obj)
    if not cap.tecap_id:
        return False, "Missing tecap_id in capsule"
    if (not force) and load_team_capsule(settings, cap.tecap_id) is not None:
        return False, f"Capsule `{cap.tecap_id}` already exists. Use --force to overwrite."
    save_team_capsule(settings, cap)
    return True, f"Imported `{cap.tecap_id}`."


def snapshot_team_capsule_change(settings: Settings, action: str, capsule: TeamExperienceCapsule) -> Path:
    return write_snapshot(
        settings,
        reason=f"team-experience-{action}",
        payload={
            "schema_version": capsule.schema_version,
            "tecap_id": capsule.tecap_id,
            "action": action,
            "privacy_level": capsule.governance.privacy_level,
            "payload": asdict(capsule),
        },
    )


def team_capsule_from_dict(obj: dict) -> TeamExperienceCapsule:
    schema = str(obj.get("schema_version", "tecap-v1"))
    if schema in {"tecap-v1", "tecap-v2", "tecap-v3"}:
        return upgrade_tecap_v1_to_v2(obj)
    return upgrade_tecap_v1_to_v2(obj)


def _to_tecap_v1_payload(c: TeamExperienceCapsule) -> dict:
    return {
        "schema_version": "tecap-v1",
        "tecap_id": c.tecap_id,
        "title": c.title,
        "problem_type": c.problem_type,
        "team_context": asdict(c.team_context),
        "participants": [asdict(x) for x in c.participants],
        "collaboration_trace": {"steps": [asdict(x) for x in c.collaboration_trace.steps]},
        "coordination_patterns": list(c.coordination_patterns),
        "anti_patterns": list(c.anti_patterns),
        "outcome": asdict(c.outcome),
        "transfer": asdict(c.transfer),
        "related_ecap_ids": list(c.related_ecap_ids),
        "related_instinct_ids": list(c.related_instinct_ids),
        "governance": asdict(c.governance),
    }


def _quality_score(c: TeamExperienceCapsule) -> float:
    m = c.coordination_metrics
    handoff = max(0.0, min(1.0, float(m.handoff_success_rate or 0.0)))
    rework = max(0.0, min(1.0, float(m.rework_ratio or 0.0)))
    escalation_penalty = min(1.0, float(m.escalation_count or 0) / 10.0)
    review_bonus = 1.0 if any(s.step_type == "review" for s in c.collaboration_trace.steps) else 0.0
    gates_bonus = min(1.0, len(c.quality_gates) / 5.0)
    score = 0.45 * handoff + 0.20 * (1.0 - rework) + 0.15 * (1.0 - escalation_penalty) + 0.10 * review_bonus + 0.10 * gates_bonus
    return round(max(0.0, min(1.0, score)), 6)
