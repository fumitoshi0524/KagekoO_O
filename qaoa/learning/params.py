from __future__ import annotations

import shlex
from dataclasses import dataclass
from typing import Literal

from .models import EvolveType

MergeStrategy = Literal["higher", "local", "import"]
OutputFormat = Literal["yaml", "json", "md"]


@dataclass
class StatusArgs:
    domain: str = ""
    source: str = ""
    low_confidence: bool = False
    high_confidence: bool = False
    as_json: bool = False


@dataclass
class ImportArgs:
    source: str = ""
    dry_run: bool = False
    force: bool = False
    min_confidence: float = 0.0
    merge_strategy: MergeStrategy = "higher"
    from_skill_creator: str = ""


@dataclass
class ExportArgs:
    output: str = ""
    domain: str = ""
    min_confidence: float = 0.0
    format: OutputFormat = "md"
    include_evidence: bool = False


@dataclass
class EvolveArgs:
    threshold: int = 3
    evolve_type: EvolveType | None = None
    domain: str = ""
    dry_run: bool = False
    execute: bool = False


def _tokenize(tail: str) -> list[str]:
    return shlex.split(tail or "")


def parse_status_args(tail: str) -> tuple[StatusArgs | None, str]:
    try:
        argv = _tokenize(tail)
    except ValueError as e:
        return None, f"Invalid args: {e}"
    out = StatusArgs()
    if "--domain" in argv:
        i = argv.index("--domain")
        if i + 1 < len(argv):
            out.domain = argv[i + 1]
    if "--source" in argv:
        i = argv.index("--source")
        if i + 1 < len(argv):
            out.source = argv[i + 1]
    out.low_confidence = "--low-confidence" in argv
    out.high_confidence = "--high-confidence" in argv
    out.as_json = "--json" in argv
    return out, ""


def parse_import_args(tail: str) -> tuple[ImportArgs | None, str]:
    try:
        argv = _tokenize(tail)
    except ValueError as e:
        return None, f"Invalid args: {e}"
    if not argv:
        return None, (
            "Usage: `/instinct-import <file-or-url> [--dry-run] [--force] "
            "[--min-confidence <n>] [--merge-strategy <higher|local|import>] "
            "[--from-skill-creator <owner/repo>]`"
        )
    out = ImportArgs(source=argv[0], dry_run="--dry-run" in argv, force="--force" in argv)
    if "--min-confidence" in argv:
        i = argv.index("--min-confidence")
        if i + 1 < len(argv):
            try:
                out.min_confidence = float(argv[i + 1])
            except ValueError:
                return None, "`--min-confidence` must be a float between 0 and 1."
    if "--merge-strategy" in argv:
        i = argv.index("--merge-strategy")
        if i + 1 < len(argv):
            ms = argv[i + 1].strip().lower()
            if ms not in {"higher", "local", "import"}:
                return None, "`--merge-strategy` must be one of: higher, local, import."
            out.merge_strategy = ms  # type: ignore[assignment]
    if "--from-skill-creator" in argv:
        i = argv.index("--from-skill-creator")
        if i + 1 < len(argv):
            out.from_skill_creator = argv[i + 1].strip()
    return out, ""


def parse_export_args(tail: str) -> tuple[ExportArgs | None, str]:
    try:
        argv = _tokenize(tail)
    except ValueError as e:
        return None, f"Invalid args: {e}"
    out = ExportArgs()
    if "--output" in argv:
        i = argv.index("--output")
        if i + 1 < len(argv):
            out.output = argv[i + 1]
    if "--domain" in argv:
        i = argv.index("--domain")
        if i + 1 < len(argv):
            out.domain = argv[i + 1]
    if "--min-confidence" in argv:
        i = argv.index("--min-confidence")
        if i + 1 < len(argv):
            try:
                out.min_confidence = float(argv[i + 1])
            except ValueError:
                return None, "`--min-confidence` must be a float between 0 and 1."
    if "--format" in argv:
        i = argv.index("--format")
        if i + 1 < len(argv):
            fmt = argv[i + 1].strip().lower()
            if fmt not in {"yaml", "json", "md"}:
                return None, "`--format` must be one of: yaml, json, md."
            out.format = fmt  # type: ignore[assignment]
    out.include_evidence = "--include-evidence" in argv
    return out, ""


def parse_evolve_args(tail: str) -> tuple[EvolveArgs | None, str]:
    try:
        argv = _tokenize(tail)
    except ValueError as e:
        return None, f"Invalid args: {e}"
    out = EvolveArgs(execute=("--execute" in argv or "--generate" in argv), dry_run="--dry-run" in argv)
    if "--threshold" in argv:
        i = argv.index("--threshold")
        if i + 1 < len(argv):
            try:
                out.threshold = max(2, int(argv[i + 1]))
            except ValueError:
                return None, "`--threshold` must be an integer >= 2."
    if "--type" in argv:
        i = argv.index("--type")
        if i + 1 < len(argv):
            t = argv[i + 1].strip().lower()
            if t not in {"command", "skill", "agent"}:
                return None, "`--type` must be one of: command, skill, agent."
            out.evolve_type = t  # type: ignore[assignment]
    if "--domain" in argv:
        i = argv.index("--domain")
        if i + 1 < len(argv):
            out.domain = argv[i + 1]
    return out, ""
