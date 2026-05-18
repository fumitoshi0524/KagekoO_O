"""Conformance engine — validates skills against the UniToolCall standard."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..types import ConformanceResult, SkillSpec, FUNCTIONAL_CATEGORIES, APPLICATION_DOMAINS


@dataclass(slots=True, kw_only=True)
class ConformanceEngine:
    min_instruction_length: int = 20
    min_score_threshold: float = 0.5

    def validate(self, skill: SkillSpec) -> ConformanceResult:
        issues: list[str] = []
        checks: dict[str, bool] = {}

        checks["has_category"] = self._check_category(skill, issues)
        checks["has_domain"] = self._check_domain(skill, issues)
        checks["has_instructions"] = self._check_instructions(skill, issues)
        checks["has_tools"] = self._check_tools(skill, issues)
        checks["has_permissions"] = self._check_permissions(skill, issues)
        checks["has_qaoa_structure"] = self._check_qaoa_structure(skill, issues)

        passed_count = sum(1 for v in checks.values() if v)
        total = len(checks)
        score = passed_count / total if total > 0 else 0.0

        if score < self.min_score_threshold:
            return ConformanceResult(
                passed=False,
                reason=f"Score {score:.2f} below threshold {self.min_score_threshold}",
                issues=issues,
                score=score,
            )

        if issues:
            return ConformanceResult(
                passed=False,
                reason=f"{len(issues)} conformance issue(s)",
                issues=issues,
                score=score,
            )

        return ConformanceResult(passed=True, reason="All checks passed", issues=[], score=1.0)

    def _check_category(self, skill: SkillSpec, issues: list[str]) -> bool:
        cat = skill.metadata.get("category", "")
        if not cat:
            issues.append("Missing required metadata: category")
            return False
        if cat not in FUNCTIONAL_CATEGORIES:
            issues.append(f"Invalid category '{cat}'. Must be one of: {FUNCTIONAL_CATEGORIES}")
            return False
        return True

    def _check_domain(self, skill: SkillSpec, issues: list[str]) -> bool:
        dom = skill.metadata.get("domain", "")
        if not dom:
            issues.append("Missing required metadata: domain")
            return False
        if dom not in APPLICATION_DOMAINS:
            issues.append(f"Invalid domain '{dom}'. Must be one of: {APPLICATION_DOMAINS}")
            return False
        return True

    def _check_instructions(self, skill: SkillSpec, issues: list[str]) -> bool:
        if len(skill.instructions.strip()) < self.min_instruction_length:
            issues.append(f"Instructions too short: {len(skill.instructions)} chars (min {self.min_instruction_length})")
            return False
        return True

    def _check_tools(self, skill: SkillSpec, issues: list[str]) -> bool:
        if not skill.allowed_tools:
            issues.append("No allowed_tools specified")
            return False
        return True

    def _check_permissions(self, skill: SkillSpec, issues: list[str]) -> bool:
        valid = {"read", "write", "destructive"}
        for perm in skill.permissions:
            if perm not in valid:
                issues.append(f"Invalid permission '{perm}'. Must be one of: {sorted(valid)}")
                return False
        return True

    def _check_qaoa_structure(self, skill: SkillSpec, issues: list[str]) -> bool:
        instructions = skill.instructions.lower()
        has_step = any(
            marker in instructions
            for marker in ("step", "1.", "2.", "first", "then", "next", "finally")
        )
        if not has_step:
            issues.append("Instructions lack QAOA step structure (no numbered steps or sequence markers)")
            return False
        return True
