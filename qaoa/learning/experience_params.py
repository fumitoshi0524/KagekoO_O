from __future__ import annotations

import shlex
from dataclasses import dataclass
from typing import Literal

from .experience_models import ExperienceApplyMode

ExportFormat = Literal["json", "md", "both"]
FeedbackResult = Literal["success", "fail"]


@dataclass
class ExperienceCreateArgs:
    from_session: str = ""
    problem_type: str = ""
    dry_run: bool = False


@dataclass
class ExperienceStatusArgs:
    as_json: bool = False
    problem_type: str = ""
    model: str = ""


@dataclass
class ExperienceExportArgs:
    ecap_id: str = ""
    format: ExportFormat = "both"
    output: str = ""


@dataclass
class ExperienceImportArgs:
    source: str = ""
    dry_run: bool = False
    force: bool = False


@dataclass
class ExperienceApplyArgs:
    ecap_id: str = ""
    mode: ExperienceApplyMode = "concise"
    problem_type: str = ""
    model: str = ""
    repo_fingerprint: str = ""
    top_k: int = 1


@dataclass
class ExperienceFeedbackArgs:
    ecap_id: str = ""
    result: FeedbackResult = "success"
    score: float = 0.5
    note: str = ""


def _split(tail: str) -> list[str]:
    return shlex.split(tail or "")


def parse_experience_create_args(tail: str) -> tuple[ExperienceCreateArgs | None, str]:
    try:
        argv = _split(tail)
    except ValueError as e:
        return None, f"Invalid args: {e}"
    out = ExperienceCreateArgs(dry_run="--dry-run" in argv)
    if "--from-session" in argv:
        i = argv.index("--from-session")
        if i + 1 < len(argv):
            out.from_session = argv[i + 1]
    if "--problem-type" in argv:
        i = argv.index("--problem-type")
        if i + 1 < len(argv):
            out.problem_type = argv[i + 1]
    return out, ""


def parse_experience_status_args(tail: str) -> tuple[ExperienceStatusArgs | None, str]:
    try:
        argv = _split(tail)
    except ValueError as e:
        return None, f"Invalid args: {e}"
    out = ExperienceStatusArgs(as_json="--json" in argv)
    if "--problem-type" in argv:
        i = argv.index("--problem-type")
        if i + 1 < len(argv):
            out.problem_type = argv[i + 1]
    if "--model" in argv:
        i = argv.index("--model")
        if i + 1 < len(argv):
            out.model = argv[i + 1]
    return out, ""


def parse_experience_export_args(tail: str) -> tuple[ExperienceExportArgs | None, str]:
    try:
        argv = _split(tail)
    except ValueError as e:
        return None, f"Invalid args: {e}"
    if not argv:
        return None, "Usage: `/experience-export <ecap_id> [--format json|md|both] [--output <path>]`"
    out = ExperienceExportArgs(ecap_id=argv[0])
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
    return out, ""


def parse_experience_import_args(tail: str) -> tuple[ExperienceImportArgs | None, str]:
    try:
        argv = _split(tail)
    except ValueError as e:
        return None, f"Invalid args: {e}"
    if not argv:
        return None, "Usage: `/experience-import <file-or-url> [--dry-run] [--force]`"
    return ExperienceImportArgs(source=argv[0], dry_run="--dry-run" in argv, force="--force" in argv), ""


def parse_experience_apply_args(tail: str) -> tuple[ExperienceApplyArgs | None, str]:
    try:
        argv = _split(tail)
    except ValueError as e:
        return None, f"Invalid args: {e}"
    out = ExperienceApplyArgs(mode="concise", top_k=1)
    if argv and not argv[0].startswith("--"):
        out.ecap_id = argv[0]
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
    if "--model" in argv:
        i = argv.index("--model")
        if i + 1 < len(argv):
            out.model = argv[i + 1]
    if "--repo-fingerprint" in argv:
        i = argv.index("--repo-fingerprint")
        if i + 1 < len(argv):
            out.repo_fingerprint = argv[i + 1]
    if "--top-k" in argv:
        i = argv.index("--top-k")
        if i + 1 < len(argv):
            try:
                out.top_k = max(1, int(argv[i + 1]))
            except ValueError:
                return None, "`--top-k` must be an integer >= 1."
    if not out.ecap_id and not (out.problem_type or out.model or out.repo_fingerprint):
        return None, (
            "Usage: `/experience-apply <ecap_id> [--mode concise|full]` or "
            "`/experience-apply --problem-type <type> [--model <name>] [--top-k N]`"
        )
    return out, ""


def parse_experience_feedback_args(tail: str) -> tuple[ExperienceFeedbackArgs | None, str]:
    try:
        argv = _split(tail)
    except ValueError as e:
        return None, f"Invalid args: {e}"
    if not argv:
        return None, "Usage: `/experience-feedback <ecap_id> --result success|fail --score <0..1> [--note <text>]`"
    out = ExperienceFeedbackArgs(ecap_id=argv[0])
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
