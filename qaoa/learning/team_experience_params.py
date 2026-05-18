from __future__ import annotations

import shlex
from dataclasses import dataclass
from typing import Literal

TeamExportFormat = Literal["json", "md", "both"]
TeamFeedbackResult = Literal["success", "fail"]
TeamApplyMode = Literal["concise", "full"]
TeamApplyStrategy = Literal["conservative", "balanced", "aggressive"]


@dataclass
class TeamExperienceCreateArgs:
    objective: str = ""
    problem_type: str = ""
    team: str = ""
    participants: str = ""
    workflow: str = ""
    constraints: str = ""
    role_ecap_mode: str = "reference"
    dry_run: bool = False


@dataclass
class TeamExperienceStatusArgs:
    as_json: bool = False
    problem_type: str = ""
    team: str = ""
    participant: str = ""


@dataclass
class TeamExperienceExportArgs:
    tecap_id: str = ""
    format: TeamExportFormat = "both"
    output: str = ""
    privacy_level: str = ""
    v1_compatible: bool = False


@dataclass
class TeamExperienceImportArgs:
    source: str = ""
    dry_run: bool = False
    force: bool = False


@dataclass
class TeamExperienceApplyArgs:
    tecap_id: str = ""
    mode: TeamApplyMode = "concise"
    problem_type: str = ""
    team: str = ""
    workflow: str = ""
    top_k: int = 1
    handoff_depth: int = 6
    strategy: TeamApplyStrategy = "balanced"
    explain: bool = False


@dataclass
class TeamExperienceFeedbackArgs:
    tecap_id: str = ""
    result: TeamFeedbackResult = "success"
    score: float = 0.5
    note: str = ""


def _split(tail: str) -> list[str]:
    return shlex.split(tail or "")


def parse_team_experience_create_args(tail: str) -> tuple[TeamExperienceCreateArgs | None, str]:
    try:
        argv = _split(tail)
    except ValueError as e:
        return None, f"Invalid args: {e}"
    out = TeamExperienceCreateArgs(dry_run="--dry-run" in argv)
    free: list[str] = []
    i = 0
    while i < len(argv):
        tok = argv[i]
        if tok == "--problem-type" and i + 1 < len(argv):
            out.problem_type = argv[i + 1]
            i += 2
            continue
        if tok == "--team" and i + 1 < len(argv):
            out.team = argv[i + 1]
            i += 2
            continue
        if tok == "--participants" and i + 1 < len(argv):
            out.participants = argv[i + 1]
            i += 2
            continue
        if tok == "--workflow" and i + 1 < len(argv):
            out.workflow = argv[i + 1]
            i += 2
            continue
        if tok == "--constraints" and i + 1 < len(argv):
            out.constraints = argv[i + 1]
            i += 2
            continue
        if tok == "--role-ecap-mode" and i + 1 < len(argv):
            mode = argv[i + 1].strip().lower()
            if mode not in {"reference", "inline"}:
                return None, "`--role-ecap-mode` must be `reference` or `inline`."
            out.role_ecap_mode = mode
            i += 2
            continue
        if tok == "--dry-run":
            i += 1
            continue
        if tok.startswith("--"):
            return None, (
                "Usage: `/team-experience-create <objective> [--problem-type <type>] [--team <name>] "
                "[--participants <a,b,c>] [--workflow <name>] [--constraints <text>] "
                "[--role-ecap-mode reference|inline] [--dry-run]`"
            )
        free.append(tok)
        i += 1
    out.objective = " ".join(free).strip()
    if not out.objective:
        return None, (
            "Usage: `/team-experience-create <objective> [--problem-type <type>] [--team <name>] "
            "[--participants <a,b,c>] [--workflow <name>] [--constraints <text>] "
            "[--role-ecap-mode reference|inline] [--dry-run]`"
        )
    return out, ""


def parse_team_experience_status_args(tail: str) -> tuple[TeamExperienceStatusArgs | None, str]:
    try:
        argv = _split(tail)
    except ValueError as e:
        return None, f"Invalid args: {e}"
    out = TeamExperienceStatusArgs(as_json="--json" in argv)
    if "--problem-type" in argv:
        i = argv.index("--problem-type")
        if i + 1 < len(argv):
            out.problem_type = argv[i + 1]
    if "--team" in argv:
        i = argv.index("--team")
        if i + 1 < len(argv):
            out.team = argv[i + 1]
    if "--participant" in argv:
        i = argv.index("--participant")
        if i + 1 < len(argv):
            out.participant = argv[i + 1]
    return out, ""


def parse_team_experience_export_args(tail: str) -> tuple[TeamExperienceExportArgs | None, str]:
    try:
        argv = _split(tail)
    except ValueError as e:
        return None, f"Invalid args: {e}"
    if not argv:
        return None, "Usage: `/team-experience-export <tecap_id> [--format json|md|both] [--output <path>]`"
    out = TeamExperienceExportArgs(tecap_id=argv[0])
    if "--format" in argv:
        i = argv.index("--format")
        if i + 1 < len(argv):
            fmt = argv[i + 1].strip().lower()
            if fmt not in {"json", "md", "both"}:
                return None, "`--format` must be one of: json, md, both."
            out.format = fmt  # type: ignore[assignment]
    if "--output" in argv:
        i = argv.index("--output")
        if i + 1 < len(argv):
            out.output = argv[i + 1]
    if "--privacy" in argv:
        i = argv.index("--privacy")
        if i + 1 < len(argv):
            out.privacy_level = argv[i + 1]
    out.v1_compatible = "--v1-compatible" in argv
    return out, ""


def parse_team_experience_import_args(tail: str) -> tuple[TeamExperienceImportArgs | None, str]:
    try:
        argv = _split(tail)
    except ValueError as e:
        return None, f"Invalid args: {e}"
    if not argv:
        return None, "Usage: `/team-experience-import <file-or-url> [--dry-run] [--force]`"
    return TeamExperienceImportArgs(source=argv[0], dry_run="--dry-run" in argv, force="--force" in argv), ""


def parse_team_experience_apply_args(tail: str) -> tuple[TeamExperienceApplyArgs | None, str]:
    try:
        argv = _split(tail)
    except ValueError as e:
        return None, f"Invalid args: {e}"
    out = TeamExperienceApplyArgs()
    if argv and not argv[0].startswith("--"):
        out.tecap_id = argv[0]
    if "--mode" in argv:
        i = argv.index("--mode")
        if i + 1 < len(argv):
            m = argv[i + 1].strip().lower()
            if m not in {"concise", "full"}:
                return None, "`--mode` must be `concise` or `full`."
            out.mode = m  # type: ignore[assignment]
    if "--problem-type" in argv:
        i = argv.index("--problem-type")
        if i + 1 < len(argv):
            out.problem_type = argv[i + 1]
    if "--team" in argv:
        i = argv.index("--team")
        if i + 1 < len(argv):
            out.team = argv[i + 1]
    if "--workflow" in argv:
        i = argv.index("--workflow")
        if i + 1 < len(argv):
            out.workflow = argv[i + 1]
    if "--top-k" in argv:
        i = argv.index("--top-k")
        if i + 1 < len(argv):
            try:
                out.top_k = max(1, int(argv[i + 1]))
            except ValueError:
                return None, "`--top-k` must be an integer >= 1."
    if "--handoff-depth" in argv:
        i = argv.index("--handoff-depth")
        if i + 1 < len(argv):
            try:
                out.handoff_depth = max(1, int(argv[i + 1]))
            except ValueError:
                return None, "`--handoff-depth` must be an integer >= 1."
    if "--strategy" in argv:
        i = argv.index("--strategy")
        if i + 1 < len(argv):
            s = argv[i + 1].strip().lower()
            if s not in {"conservative", "balanced", "aggressive"}:
                return None, "`--strategy` must be one of: conservative, balanced, aggressive."
            out.strategy = s  # type: ignore[assignment]
    out.explain = "--explain" in argv
    if not out.tecap_id and not (out.problem_type or out.team or out.workflow):
        return None, (
            "Usage: `/team-experience-apply <tecap_id> [--mode concise|full]` or "
            "`/team-experience-apply --problem-type <type> [--team <name>] [--top-k N]`"
        )
    return out, ""


def parse_team_experience_feedback_args(tail: str) -> tuple[TeamExperienceFeedbackArgs | None, str]:
    try:
        argv = _split(tail)
    except ValueError as e:
        return None, f"Invalid args: {e}"
    if not argv:
        return None, "Usage: `/team-experience-feedback <tecap_id> --result success|fail --score <0..1> [--note <text>]`"
    out = TeamExperienceFeedbackArgs(tecap_id=argv[0])
    if "--result" in argv:
        i = argv.index("--result")
        if i + 1 < len(argv):
            r = argv[i + 1].strip().lower()
            if r not in {"success", "fail"}:
                return None, "`--result` must be `success` or `fail`."
            out.result = r  # type: ignore[assignment]
    else:
        return None, "`--result` is required."
    if "--score" in argv:
        i = argv.index("--score")
        if i + 1 < len(argv):
            try:
                out.score = float(argv[i + 1])
            except ValueError:
                return None, "`--score` must be a float in [0,1]."
    else:
        return None, "`--score` is required."
    out.score = max(0.0, min(1.0, out.score))
    if "--note" in argv:
        i = argv.index("--note")
        if i + 1 < len(argv):
            out.note = argv[i + 1]
    return out, ""
