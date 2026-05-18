from __future__ import annotations

import json

from .models import Instinct


def to_markdown(instincts: list[Instinct], *, include_evidence: bool = False) -> str:
    lines: list[str] = []
    for inst in instincts:
        lines.append("---")
        lines.append(f"id: {inst.id}")
        lines.append(f'trigger: "{inst.trigger}"')
        lines.append(f"confidence: {inst.confidence:.2f}")
        lines.append(f"domain: {inst.domain}")
        lines.append(f"source: {inst.source}")
        if inst.imported_at:
            lines.append(f'imported_at: "{inst.imported_at}"')
        if inst.original_source:
            lines.append(f'original_source: "{inst.original_source}"')
        lines.append("---")
        lines.append("")
        body = (inst.content or "").strip()
        if not include_evidence and "## Evidence" in body:
            body = body.split("## Evidence", 1)[0].rstrip()
        lines.append(body)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def to_json(instincts: list[Instinct], *, include_evidence: bool = False) -> str:
    rows: list[dict[str, object]] = []
    for inst in instincts:
        content = inst.content or ""
        if not include_evidence and "## Evidence" in content:
            content = content.split("## Evidence", 1)[0].rstrip()
        rows.append(
            {
                "id": inst.id,
                "trigger": inst.trigger,
                "confidence": inst.confidence,
                "domain": inst.domain,
                "source": inst.source,
                "content": content,
                "imported_at": inst.imported_at,
                "original_source": inst.original_source,
            }
        )
    return json.dumps({"version": "2.0", "instincts": rows}, ensure_ascii=False, indent=2) + "\n"


def to_yaml(instincts: list[Instinct], *, include_evidence: bool = False) -> str:
    # Keep yaml generation simple and dependency-free.
    base = ["version: \"2.0\"", "instincts:"]
    for inst in instincts:
        content = inst.content or ""
        if not include_evidence and "## Evidence" in content:
            content = content.split("## Evidence", 1)[0].rstrip()
        base.extend(
            [
                f"  - id: {inst.id}",
                f"    trigger: \"{inst.trigger}\"",
                f"    confidence: {inst.confidence:.2f}",
                f"    domain: {inst.domain}",
                f"    source: {inst.source}",
                "    content: |-",
            ]
        )
        if content:
            for ln in content.splitlines():
                base.append(f"      {ln}")
        else:
            base.append("      ")
    return "\n".join(base).rstrip() + "\n"
