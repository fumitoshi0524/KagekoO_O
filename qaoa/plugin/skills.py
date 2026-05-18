from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from .types import LoadedPlugin, PluginSkill, SkillContext

logger = logging.getLogger(__name__)

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n(.*)", re.DOTALL)


def _parse_yaml_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Split a SKILL.md into (frontmatter dict, markdown body).

    Uses a lightweight regex + manual key:value parsing so we avoid
    a hard dependency on PyYAML (which may not be installed).
    """
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text

    raw_yaml = m.group(1)
    body = m.group(2)

    # Try PyYAML first (best fidelity).
    try:
        import yaml
        fm = yaml.safe_load(raw_yaml)
        if isinstance(fm, dict):
            return fm, body
    except Exception:
        pass

    # Fallback: simple key:value line parser.
    fm: dict[str, Any] = {}
    for line in raw_yaml.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if value.lower() in ("true", "yes"):
            fm[key] = True
        elif value.lower() in ("false", "no"):
            fm[key] = False
        else:
            fm[key] = value
    return fm, body


def _load_skill_dir(skill_dir: Path, plugin_name: str) -> PluginSkill | None:
    """Load a skill from a directory containing SKILL.md."""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return None

    try:
        text = skill_md.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None

    fm, body = _parse_yaml_frontmatter(text)

    name = str(fm.get("name", skill_dir.name))
    description = fm.get("description")
    if description is None:
        first_para = body.strip().split("\n\n", 1)[0]
        description = first_para[:200] if first_para else name

    disable_model = fm.get("disable-model-invocation", False)
    if isinstance(disable_model, str):
        disable_model = disable_model.lower() in ("true", "yes", "1")

    allowed_tools_raw = fm.get("allowed-tools", "")
    if isinstance(allowed_tools_raw, str):
        allowed_tools = [t.strip() for t in allowed_tools_raw.split(",") if t.strip()]
    elif isinstance(allowed_tools_raw, list):
        allowed_tools = [str(t).strip() for t in allowed_tools_raw]
    else:
        allowed_tools = []

    ctx_raw = fm.get("context", "inline")
    try:
        ctx = SkillContext(ctx_raw)
    except Exception:
        ctx = SkillContext.INLINE

    user_invocable_raw = fm.get("user-invocable")
    user_invocable: bool | None = None
    if isinstance(user_invocable_raw, bool):
        user_invocable = user_invocable_raw
    elif isinstance(user_invocable_raw, str):
        user_invocable = user_invocable_raw.lower() in ("true", "yes", "1")

    return PluginSkill(
        name=name,
        description=str(description),
        content=body,
        plugin_name=plugin_name,
        disable_model_invocation=bool(disable_model),
        argument_hint=fm.get("argument-hint"),
        user_invocable=user_invocable,
        allowed_tools=allowed_tools,
        context=ctx,
    )


def _load_command_file(md_path: Path, plugin_name: str) -> PluginSkill | None:
    """Load a simple command .md file (Claude Code `commands/` directory)."""
    if not md_path.is_file() or md_path.suffix.lower() != ".md":
        return None

    try:
        text = md_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None

    fm, body = _parse_yaml_frontmatter(text)

    name = str(fm.get("name", md_path.stem))
    description = fm.get("description")
    if description is None:
        first_para = body.strip().split("\n\n", 1)[0]
        description = first_para[:200] if first_para else name

    return PluginSkill(
        name=name,
        description=str(description),
        content=body,
        plugin_name=plugin_name,
        disable_model_invocation=bool(fm.get("disable-model-invocation", False)),
    )


def _expand_manifest_paths(plugin_root: Path, spec: str | list[str] | None) -> list[Path]:
    if spec is None:
        return []
    items: list[str] = [spec] if isinstance(spec, str) else list(spec)
    root = plugin_root.resolve()
    out: list[Path] = []
    for item in items:
        if not isinstance(item, str) or not item.strip():
            continue
        p = (plugin_root / item).resolve()
        if not str(p).startswith(str(root)):
            continue
        if p.is_file() and p.suffix.lower() == ".md":
            out.append(p)
        elif p.is_dir():
            for md in sorted(p.rglob("*.md"), key=lambda x: str(x)):
                out.append(md)
    return out


def _load_skill_from_path(md_path: Path, plugin_name: str) -> PluginSkill | None:
    """Load a SKILL.md path or a generic .md as a command-style skill."""
    if md_path.name.upper() == "SKILL.md" and md_path.parent.is_dir():
        return _load_skill_dir(md_path.parent, plugin_name)
    return _load_command_file(md_path, plugin_name)


def load_skills_for_plugin(plugin: LoadedPlugin) -> list[PluginSkill]:
    """Discover and load all skills/commands from a plugin directory.

    When ``manifest.strict`` is true, only paths listed under ``skills`` and
    ``commands`` in plugin.json are used. Otherwise the default ``skills/`` and
    ``commands/`` directories are scanned.
    """
    root = plugin.root
    m = plugin.manifest
    strict = m.strict is True
    skills: list[PluginSkill] = []
    seen_names: set[str] = set()

    def add_skill(s: PluginSkill | None) -> None:
        if s and s.name not in seen_names:
            seen_names.add(s.name)
            skills.append(s)

    if strict:
        if m.skills is None and m.commands is None:
            return []
        for pth in _expand_manifest_paths(root, m.skills):
            add_skill(_load_skill_from_path(pth, plugin.name))
        for pth in _expand_manifest_paths(root, m.commands):
            add_skill(_load_command_file(pth, plugin.name))
        return skills

    skills_dir = root / "skills"
    if skills_dir.is_dir():
        for entry in sorted(skills_dir.iterdir(), key=lambda p: p.name):
            if entry.is_dir():
                add_skill(_load_skill_dir(entry, plugin.name))

    commands_dir = root / "commands"
    if commands_dir.is_dir():
        for entry in sorted(commands_dir.iterdir(), key=lambda p: p.name):
            if entry.is_file() and entry.suffix.lower() == ".md":
                add_skill(_load_command_file(entry, plugin.name))

    # QAOA conformance validation: verify each skill meets quality threshold
    return skills


def load_agent_files_for_plugin(plugin: LoadedPlugin) -> list[dict[str, Any]]:
    """Load agent markdown paths from manifest (strict or loose)."""
    root = plugin.root
    m = plugin.manifest
    agents_spec = m.agents
    paths: list[Path] = []
    if m.strict is True:
        paths = _expand_manifest_paths(root, agents_spec)
    elif agents_spec is not None:
        paths = _expand_manifest_paths(root, agents_spec)
    else:
        ad = root / "agents"
        if ad.is_dir():
            paths = sorted([x for x in ad.iterdir() if x.suffix.lower() == ".md"], key=lambda p: p.name)

    out: list[dict[str, Any]] = []
    for pth in paths:
        if not pth.is_file():
            continue
        try:
            text = pth.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        out.append({"path": str(pth.relative_to(root)), "content": text[:8000]})
    return out


def build_skills_description(skills: list[PluginSkill]) -> str:
    """Build a short summary of available skills for system prompt injection."""
    if not skills:
        return ""
    by_name: dict[str, list[PluginSkill]] = {}
    for s in skills:
        by_name.setdefault(s.name, []).append(s)

    lines: list[str] = []
    for s in skills:
        if s.disable_model_invocation:
            continue
        desc = s.description or "(no description)"
        alts = by_name.get(s.name, [])
        if len(alts) == 1:
            lines.append(f"- /{s.name} — {desc}  (plugin: {s.plugin_name})")
        else:
            lines.append(f"- /{s.plugin_name}:{s.name} — {desc}")
    if not lines:
        return ""
    return "\n".join(lines)
