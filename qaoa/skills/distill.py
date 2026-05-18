"""Distill engine — extracts semantic structure from skill content."""

from __future__ import annotations

from dataclasses import dataclass, field
import re

from ..types import FUNCTIONAL_CATEGORIES, APPLICATION_DOMAINS


@dataclass(slots=True, frozen=True, kw_only=True)
class DistilledSkill:
    name: str
    description: str
    instructions: str
    category: str
    domain: str
    tool_bindings: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    intent: str = ""
    source_format: str = "unknown"


@dataclass(slots=True, kw_only=True)
class DistillEngine:
    def distill(self, raw_markdown: str) -> DistilledSkill:
        frontmatter, body = self._split_frontmatter(raw_markdown)

        name = frontmatter.get("name", self._infer_name(body))
        description = frontmatter.get("description", "")
        category = self._extract_category(frontmatter, body)
        domain = self._extract_domain(frontmatter, body)
        tool_bindings = self._extract_list(frontmatter, "tools")
        permissions = self._extract_list(frontmatter, "permissions")
        intent = self._infer_intent(name, description, body)

        return DistilledSkill(
            name=name,
            description=description,
            instructions=body,
            category=category,
            domain=domain,
            tool_bindings=tool_bindings,
            permissions=permissions,
            intent=intent,
            source_format=frontmatter.get("format", "unknown"),
        )

    def _split_frontmatter(self, raw: str) -> tuple[dict[str, str], str]:
        text = raw.strip()
        fm_match = re.match(
            r"\A---\s*\r?\n(.*?)\r?\n---\s*(.*)\Z",
            text, re.DOTALL,
        )
        if not fm_match:
            return {}, text
        header = fm_match.group(1) or ""
        body = fm_match.group(2).strip() if fm_match.group(2) else text
        meta: dict[str, str] = {}
        current_list_key: str | None = None
        for line in header.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("- "):
                if current_list_key:
                    meta[current_list_key] = meta.get(current_list_key, "") + "," + stripped[2:].strip()
                continue
            if ":" in stripped:
                key, _, value = stripped.partition(":")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if value == "":
                    current_list_key = key
                else:
                    meta[key] = value
                    current_list_key = key
        return meta, body

    def _extract_category(self, frontmatter: dict[str, str], body: str) -> str:
        cat = frontmatter.get("category", "").strip().lower()
        if cat in FUNCTIONAL_CATEGORIES:
            return cat
        body_lower = body.lower()
        for fc in FUNCTIONAL_CATEGORIES:
            if fc in body_lower:
                return fc
        return "operations"

    def _extract_domain(self, frontmatter: dict[str, str], body: str) -> str:
        dom = frontmatter.get("domain", "").strip().lower()
        if dom in APPLICATION_DOMAINS:
            return dom
        body_lower = body.lower()
        for ad in APPLICATION_DOMAINS:
            if ad in body_lower:
                return ad
        return "technology"

    def _extract_list(self, frontmatter: dict[str, str], key: str) -> list[str]:
        raw = frontmatter.get(key, "")
        if not raw:
            return []
        items = [item.strip() for item in raw.replace("\n", ",").split(",")]
        return [i for i in items if i]

    def _infer_name(self, body: str) -> str:
        h1 = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
        if h1:
            return h1.group(1).strip().lower().replace(" ", "-")[:40]
        return "unnamed-skill"

    def _infer_intent(self, name: str, description: str, body: str) -> str:
        lines = [line.strip() for line in body.splitlines() if line.strip() and not line.startswith("#")]
        objective_line = ""
        for i, line in enumerate(lines):
            if line.lower().startswith("objective"):
                if i + 1 < len(lines):
                    objective_line = lines[i + 1]
                break
        if not objective_line:
            for line in lines[:5]:
                if len(line) > 20:
                    objective_line = line
                    break
        return objective_line or description or name
