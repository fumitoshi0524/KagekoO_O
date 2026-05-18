"""Slash commands: /plugin (Claude Code style) and /skill-name."""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass
from pathlib import Path

from ..config.settings import Settings
from ..storage_paths import iter_read_candidates
from .manager import PluginManager
from .paths import resolve_plugin_paths
from .ops import (
    FetchError,
    install_plugin_from_marketplace,
    marketplace_add,
    marketplace_list,
    marketplace_remove,
    marketplace_update,
    uninstall_plugin,
)
from .types import PluginSkill


def plugin_skill_autocomplete_entries(pm: PluginManager | None) -> list[tuple[str, str]]:
    """Return (name, description) rows for `/` UI autocomplete from loaded plugin skills.

    Mirrors skills shown in the system prompt; skips ``disable_model_invocation`` skills.
    """
    if pm is None:
        return []
    rows: list[tuple[str, str]] = []
    try:
        skills = pm.get_all_skills()
    except Exception:
        return []
    for sk in skills:
        if sk.disable_model_invocation:
            continue
        desc = (sk.description or "").strip().replace("\n", " ")
        if len(desc) > 100:
            desc = desc[:97] + "..."
        plug = (sk.plugin_name or "").strip() or "plugin"
        label = f"Skill ({plug})" + (f": {desc}" if desc else "")
        rows.append((sk.name, label))
    return rows


@dataclass
class SlashDispatch:
    """Result of inspecting a user message for slash handling."""

    # If True, skip the LLM and only show plugin_reply in the UI.
    consume_without_llm: bool
    # Text sent to the agent (original or skill-wrapped). Ignored if consume_without_llm.
    llm_user_text: str
    # Assistant-style message when consume_without_llm.
    plugin_reply: str | None = None


_PLUGIN_HEAD = re.compile(r"^/([a-zA-Z][a-zA-Z0-9_.-]*)\s*(.*)$", re.DOTALL)


def plugin_slash_help() -> str:
    return (
        "Kageko /plugin (Claude Code compatible)\n"
        "  /plugin marketplace add <path|git|url>\n"
        "  /plugin marketplace update [name]\n"
        "  /plugin marketplace list\n"
        "  /plugin marketplace remove <name>\n"
        "  /plugin install <plugin>@<marketplace>\n"
        "  /plugin list\n"
        "  /plugin enable <name>\n"
        "  /plugin disable <name>\n"
        "  /plugin uninstall <name>\n"
    )


def empty_plugin_list_hint(settings: Settings) -> str:
    """Human-readable hint when /plugin list finds nothing (not an error)."""
    if not settings.plugins.enabled:
        return (
            "Plugin system is disabled (set plugins.enabled to true in config)."
        )
    paths = resolve_plugin_paths(settings)
    wd = Path(settings.working_directory or ".")
    project_paths = [str(p.resolve()) for p in iter_read_candidates(wd, Path("plugins"))]
    proj_hint = "\n".join([f"  - {p}" for p in project_paths])
    return (
        "No plugins loaded yet.\n\n"
        "Kageko scans (in order):\n"
        f"  - plugin_dirs in config\n"
        f"{proj_hint}\n"
        f"  - {paths.user_plugins_dir} (subfolders except 'cache')\n"
        f"  - {paths.cache_dir} (after /plugin install)\n\n"
        "Install from a marketplace:\n"
        "  /plugin marketplace add <local-path|git-url>\n"
        "  /plugin install <plugin-name>@<marketplace-name>\n\n"
        "If you already use Claude Code plugins under ~/.claude, set:\n"
        '  "plugins": { "data_root_mode": "claude" }'
    )


def _ensure_pm(settings: Settings, pm: PluginManager | None) -> PluginManager:
    if pm is not None:
        return pm
    out = PluginManager(settings)
    out.discover_and_load()
    return out


def _run_plugin_argv(argv: list[str], settings: Settings, pm: PluginManager | None) -> str:
    pm_eff = _ensure_pm(settings, pm)
    if not argv:
        return plugin_slash_help()
    head, *rest = argv
    if head == "marketplace" and rest:
        sub = rest[0]
        args = rest[1:]
        if sub == "add" and args:
            try:
                name, _root = marketplace_add(settings, " ".join(args))
                pm_eff.discover_and_load()
                return f"Marketplace added: {name}"
            except FetchError as e:
                return f"Error: {e}"
        if sub == "update":
            mname = args[0] if args else None
            try:
                upd = marketplace_update(settings, mname)
                pm_eff.discover_and_load()
                return "Updated: " + (", ".join(upd) if upd else "(nothing to do)")
            except Exception as e:
                return f"Error: {e}"
        if sub == "list":
            rows = marketplace_list(settings)
            if not rows:
                return "No marketplaces registered."
            lines = [f"  {r.name}  ({r.local_path})" for r in rows]
            return "Marketplaces:\n" + "\n".join(lines)
        if sub == "remove" and args:
            ok = marketplace_remove(settings, args[0])
            pm_eff.discover_and_load()
            return f"Removed marketplace {args[0]}" if ok else f"Unknown marketplace: {args[0]}"
        return plugin_slash_help()
    if head == "install" and rest:
        spec = " ".join(rest).strip()
        if "@" not in spec:
            return "Usage: /plugin install <plugin>@<marketplace>"
        pname, mname = spec.rsplit("@", 1)
        pname, mname = pname.strip(), mname.strip()
        try:
            dest = install_plugin_from_marketplace(settings, pname, mname)
            pm_eff.discover_and_load()
            return f"Installed {pname} into {dest}"
        except FetchError as e:
            return f"Error: {e}"
    if head == "list":
        rows = pm_eff.list_plugins()
        if not rows:
            return empty_plugin_list_hint(settings)
        lines = [
            f"  {p['name']} v{p['version']}  [{'on' if p['enabled'] else 'off'}]  {p['root']}"
            for p in rows
        ]
        return "Plugins:\n" + "\n".join(lines)
    if head == "enable" and rest:
        n = rest[0]
        ok = pm_eff.enable_plugin(n)
        pm_eff.discover_and_load()
        return f"Enabled {n}" if ok else f"Plugin not found: {n}"
    if head == "disable" and rest:
        n = rest[0]
        ok = pm_eff.disable_plugin(n)
        pm_eff.discover_and_load()
        return f"Disabled {n}" if ok else f"Plugin not found: {n}"
    if head == "uninstall" and rest:
        n = rest[0]
        ok = uninstall_plugin(settings, n)
        pm_eff.discover_and_load()
        return f"Uninstalled {n}" if ok else f"Plugin not in registry: {n}"
    return plugin_slash_help()


def dispatch_slash(user_text: str, settings: Settings, pm: PluginManager | None) -> SlashDispatch | None:
    """Return None if the message should be handled as a normal chat line."""
    raw = user_text.strip()
    if not raw.startswith("/"):
        return None
    m = _PLUGIN_HEAD.match(raw)
    if not m:
        return None
    head, tail = m.group(1), m.group(2).strip()
    if head == "plugin":
        try:
            parts = shlex.split(tail) if tail else []
        except ValueError as e:
            return SlashDispatch(
                consume_without_llm=True,
                llm_user_text="",
                plugin_reply=f"Invalid /plugin arguments: {e}",
            )
        msg = _run_plugin_argv(parts, settings, pm)
        return SlashDispatch(consume_without_llm=True, llm_user_text="", plugin_reply=msg)

    if pm is None:
        return None
    skills = [s for s in pm.get_all_skills() if s.name == head]
    if not skills:
        return None
    if len(skills) > 1:
        opts = ", ".join(f"{s.plugin_name}:{s.name}" for s in skills)
        return SlashDispatch(
            consume_without_llm=True,
            llm_user_text="",
            plugin_reply=f"Ambiguous skill {head!r}. Use one of: {opts}",
        )
    return _wrap_skill(skills[0], tail, user_text)


def _wrap_skill(skill: PluginSkill, tail: str, original: str) -> SlashDispatch:
    body = skill.content.strip()
    hint = (
        f"[Skill /{skill.name} from plugin {skill.plugin_name}]\n{body}\n\n"
        f"---\nUser request:\n{tail if tail else '(no additional text)'}\n"
    )
    if skill.allowed_tools:
        hint += f"\n(preferred tools: {', '.join(skill.allowed_tools)})\n"
    return SlashDispatch(consume_without_llm=False, llm_user_text=hint, plugin_reply=None)
