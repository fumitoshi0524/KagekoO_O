"""Skill registry — central store for all skills."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..types import SkillSpec, FUNCTIONAL_CATEGORIES, APPLICATION_DOMAINS
from .scripts import SkillScriptLoader

if TYPE_CHECKING:
    from ..adapters.tools import ToolRegistry


@dataclass(slots=True, kw_only=True)
class SkillRegistry:
    _skills: dict[str, SkillSpec] = field(default_factory=dict)
    _active_skill: str | None = None
    _tools: ToolRegistry | None = None
    _script_loader: SkillScriptLoader = field(default_factory=SkillScriptLoader)
    _workspace: str = ""
    _prompts: dict[str, str] = field(default_factory=dict)
    _references: dict[str, str] = field(default_factory=dict)
    _installed: set[str] = field(default_factory=set)

    # ── CRUD ─────────────────────────────────────────────────────────

    def register(self, skill: SkillSpec) -> None:
        self._skills[skill.name] = skill

    def unregister(self, name: str) -> None:
        if name in self._skills:
            self.deactivate_scripts(name)
            del self._skills[name]
        if self._active_skill == name:
            self._active_skill = None

    def get(self, name: str) -> SkillSpec | None:
        return self._skills.get(name)

    def list_all(self) -> list[SkillSpec]:
        return sorted(self._skills.values(), key=lambda s: s.name)

    def count(self) -> int:
        return len(self._skills)

    # ── Activation ───────────────────────────────────────────────────

    def activate(self, name: str) -> None:
        if name not in self._skills:
            raise ValueError(f"Skill '{name}' is not registered.")
        self._active_skill = name
        skill = self._skills[name]
        self._activate_scripts(skill)

    def deactivate(self) -> None:
        if self._active_skill:
            self.deactivate_scripts(self._active_skill)
        self._active_skill = None

    def bind_tools(self, tools: ToolRegistry) -> None:
        self._tools = tools
        self._script_loader.registry = tools

    # ── Script tools ─────────────────────────────────────────────────

    def _activate_scripts(self, skill: SkillSpec) -> None:
        if self._tools is None:
            return
        names = self._script_loader.register(skill, workspace=self._workspace)
        if names:
            import logging
            logging.getLogger(__name__).debug(f"Activated script tools: {names}")

    def deactivate_scripts(self, name: str) -> None:
        skill = self._skills.get(name)
        if skill:
            self._script_loader.unregister(skill)

    def get_active(self) -> SkillSpec | None:
        if self._active_skill is None:
            return None
        return self._skills.get(self._active_skill)

    # ── Search ───────────────────────────────────────────────────────

    def search(self, query: str) -> list[SkillSpec]:
        q = query.lower()
        results: list[SkillSpec] = []
        for skill in self._skills.values():
            if (
                q in skill.name.lower()
                or q in skill.description.lower()
                or q in skill.instructions.lower()
            ):
                results.append(skill)
        return sorted(results, key=lambda s: s.name)

    def find_matching(self, query: str) -> list[SkillSpec]:
        """Keyword-based matching. Returns best matches first."""
        q = query.lower()
        words = set(q.split())
        scored: list[tuple[int, SkillSpec]] = []
        for skill in self._skills.values():
            score = 0
            name_lower = skill.name.lower().replace("-", " ").replace("_", " ")
            desc_lower = skill.description.lower()
            # Full query match (highest weight)
            if q in name_lower:
                score += 15
            elif any(w in name_lower for w in words if len(w) > 2):
                score += 8
            if q in desc_lower:
                score += 8
            elif any(w in desc_lower for w in words if len(w) > 2):
                score += 4
            # Word overlap in instructions
            if q in skill.instructions.lower():
                score += 2
            elif any(w in skill.instructions.lower() for w in words if len(w) > 2):
                score += 1
            # Tag matching
            for tag in skill.metadata.get("tags", []):
                tag_str = str(tag).lower()
                if q in tag_str:
                    score += 5
                elif any(w in tag_str for w in words if len(w) > 2):
                    score += 2
            if score > 0:
                scored.append((score, skill))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [skill for _, skill in scored]

    def find_by_grid(
        self,
        *,
        category: str | None = None,
        domain: str | None = None,
        include_neighbors: bool = True,
    ) -> list[SkillSpec]:
        """Semantic grid search — find skills at specific UniToolCall grid coordinates.

        If include_neighbors is True, also returns skills in adjacent categories/domains.
        Results are ordered by distance from the target coordinate.
        """
        results: list[tuple[int, SkillSpec]] = []

        for skill in self._skills.values():
            skill_cat = skill.metadata.get("category", "")
            skill_dom = skill.metadata.get("domain", "")
            distance = self._grid_distance(
                target_cat=category,
                target_dom=domain,
                skill_cat=skill_cat,
                skill_dom=skill_dom,
            )
            if distance is not None and (distance == 0 or include_neighbors):
                results.append((distance, skill))

        results.sort(key=lambda item: item[0])
        return [skill for _, skill in results]

    @staticmethod
    def _grid_distance(
        *,
        target_cat: str | None,
        target_dom: str | None,
        skill_cat: str,
        skill_dom: str,
    ) -> int | None:
        """Compute Manhattan distance in the category×domain grid. Returns None if no target."""
        if target_cat is None and target_dom is None:
            return 0

        distance = 0
        if target_cat is not None:
            try:
                cat_idx = FUNCTIONAL_CATEGORIES.index(target_cat)
                skill_cat_idx = FUNCTIONAL_CATEGORIES.index(skill_cat) if skill_cat in FUNCTIONAL_CATEGORIES else -1
                if skill_cat_idx == -1:
                    return None
                distance += abs(cat_idx - skill_cat_idx)
            except ValueError:
                pass

        if target_dom is not None:
            try:
                dom_idx = APPLICATION_DOMAINS.index(target_dom)
                skill_dom_idx = APPLICATION_DOMAINS.index(skill_dom) if skill_dom in APPLICATION_DOMAINS else -1
                if skill_dom_idx == -1:
                    return None
                distance += abs(dom_idx - skill_dom_idx)
            except ValueError:
                pass

        return distance

    def classify_query_to_grid(self, query: str) -> tuple[str, str]:
        """Heuristic classification of a query into category and domain."""
        query_lower = query.lower()

        cat_scores: dict[str, int] = {}
        for cat in FUNCTIONAL_CATEGORIES:
            score = 0
            if cat in query_lower:
                score += 10
            keywords = {
                "analysis": ("analyze", "compute", "calculate", "evaluate", "assess"),
                "operations": ("create", "write", "update", "delete", "deploy", "build", "run"),
                "system": ("config", "system", "admin", "manage", "monitor"),
                "visualization": ("chart", "plot", "display", "show", "visualize", "graph"),
                "search": ("search", "find", "query", "lookup", "read", "fetch"),
                "generate": ("generate", "create", "build", "produce", "make"),
            }
            for kw in keywords.get(cat, ()):
                if kw in query_lower:
                    score += 3
            if score > 0:
                cat_scores[cat] = score

        domain_scores: dict[str, int] = {}
        for dom in APPLICATION_DOMAINS:
            if dom in query_lower:
                domain_scores[dom] = 10

        best_cat = max(cat_scores, key=cat_scores.get) if cat_scores else "operations"
        best_dom = max(domain_scores, key=domain_scores.get) if domain_scores else "technology"
        return best_cat, best_dom

    # ── Tool binding ─────────────────────────────────────────────────
    # (see bind_tools above — single definition)

    def get_tools_for_active(self) -> dict[str, object] | None:
        if self._tools is None:
            return None
        active = self.get_active()
        if active is None:
            return None
        return {
            name: self._tools.describe(name)
            for name in active.allowed_tools
            if name in self._tools._specs
        }

    def validate_skill_tools(self, skill: SkillSpec) -> list[str]:
        """Return list of tool names in skill.allowed_tools that don't exist."""
        if self._tools is None:
            return []
        missing: list[str] = []
        for name in skill.allowed_tools:
            if name not in self._tools._specs:
                missing.append(name)
        return missing

    # ── QAOA: install/uninstall skills (unitool + prompt + reference) ──

    def install_skill(self, name: str, tool_fn, prompt: str, reference: str = "",
                      category: str = "operations", domain: str = "technology") -> None:
        """Install a skill: register tool + store prompt + store reference. Permanent until uninstalled."""
        if self._tools is None:
            return
        self._tools.unfreeze()
        self._tools.register(name, tool_fn, description=prompt[:80],
                             category=category, domain=domain)
        self._tools.freeze()
        self._prompts[name] = prompt
        self._references[name] = reference
        self._installed.add(name)

    def uninstall_skill(self, name: str) -> None:
        """Uninstall a skill: unregister tool + remove prompt + remove reference."""
        if self._tools is not None:
            self._tools.unregister(name)
        self._prompts.pop(name, None)
        self._references.pop(name, None)
        self._installed.discard(name)

    def get_prompts_for_grid(self, category: str, domain: str, limit: int = 5) -> list[str]:
        """Return concise system prompts for installed skills matching grid coordinates."""
        skills = self.find_by_grid(category=category, domain=domain, include_neighbors=True)
        return [self._prompts[s.name] for s in skills[:limit] if s.name in self._prompts]

    def get_reference(self, name: str) -> str:
        """Return detailed reference doc for a skill (on-demand loading)."""
        return self._references.get(name, "")

    def get_installed_skills(self) -> list[str]:
        return sorted(self._installed)
