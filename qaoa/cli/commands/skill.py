"""Skill management commands."""

from __future__ import annotations

from typing import Annotated

import typer
from rich import box
from rich.panel import Panel

from .._shared import (
    _require_runtime, _spinner_context, console,
    ProviderOpt, ApiKeyOpt, ModelOpt, WorkspaceOpt, SkillsDirOpt, SessionOpt, JsonOpt,
)
from ..errors import format_error
from ..render import render_skill_table

skill_app = typer.Typer(help="Manage skills")


@skill_app.command("list")
def skill_list(
    ctx: typer.Context,
    provider: ProviderOpt = None, api_key: ApiKeyOpt = None,
    model: ModelOpt = None, workspace: WorkspaceOpt = None,
    skills_dir: SkillsDirOpt = None,
    json: JsonOpt = False,
) -> None:
    """List all skills."""
    runtime = _require_runtime(
        ctx, provider, api_key, model, base_url=None, workspace=workspace,
        skills_dir=skills_dir, enable_rag=False, rag_persist_dir=None,
        enable_mcp=False, mcp_server_url=None,
    )
    skills = runtime.list_skills()
    if not skills:
        if json:
            console.print_json("[]")
        else:
            console.print("[dim]No skills found.[/dim]")
        return
    if json:
        console.print_json(data=[{"name": s.name, "description": s.description,
                                   "allowed_tools": s.allowed_tools, "format": s.format}
                                  for s in skills])
    else:
        console.print(render_skill_table(skills))


@skill_app.command("generate")
def skill_generate(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Skill name")],
    objective: Annotated[str, typer.Argument(help="Skill objective")],
    provider: ProviderOpt = None, api_key: ApiKeyOpt = None,
    model: ModelOpt = None, workspace: WorkspaceOpt = None,
    skills_dir: SkillsDirOpt = None,
) -> None:
    """Generate a new skill."""
    runtime = _require_runtime(
        ctx, provider, api_key, model, base_url=None, workspace=workspace,
        skills_dir=skills_dir, enable_rag=False, rag_persist_dir=None,
        enable_mcp=False, mcp_server_url=None,
    )
    with _spinner_context():
        try:
            skill = runtime.generate_skill(name=name, objective=objective)
        except Exception as e:
            console.print(Panel(format_error(e), border_style="red"))
            raise typer.Exit(1)
    console.print(Panel(
        f"[bold]Name:[/bold] {skill.name}\n"
        f"[bold]Objective:[/bold] {skill.objective}\n"
        f"[bold]Tools:[/bold] {', '.join(skill.tools) if skill.tools else '—'}\n"
        f"[bold]Steps:[/bold]\n" + "\n".join(f"  {i}. {s}" for i, s in enumerate(skill.steps, 1)),
        title=f"[bold green]Skill: {skill.name}[/bold green]",
        border_style="green",
        box=box.ROUNDED,
    ))


@skill_app.command("use")
def skill_use(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Skill name")],
    session: SessionOpt = "default",
    provider: ProviderOpt = None, api_key: ApiKeyOpt = None,
    model: ModelOpt = None, workspace: WorkspaceOpt = None,
    skills_dir: SkillsDirOpt = None,
) -> None:
    """Activate a skill for the current session."""
    runtime = _require_runtime(
        ctx, provider, api_key, model, base_url=None, workspace=workspace,
        skills_dir=skills_dir, enable_rag=False, rag_persist_dir=None,
        enable_mcp=False, mcp_server_url=None,
    )
    runtime.activate_skill(session_id=session, name=name)
    console.print(f"[bold green]✓[/bold green] Active skill → [bold]{name}[/bold]")


@skill_app.command("clear")
def skill_clear(
    ctx: typer.Context,
    session: SessionOpt = "default",
    provider: ProviderOpt = None, api_key: ApiKeyOpt = None,
    model: ModelOpt = None, workspace: WorkspaceOpt = None,
    skills_dir: SkillsDirOpt = None,
) -> None:
    """Clear the active skill for the current session."""
    runtime = _require_runtime(
        ctx, provider, api_key, model, base_url=None, workspace=workspace,
        skills_dir=skills_dir, enable_rag=False, rag_persist_dir=None,
        enable_mcp=False, mcp_server_url=None,
    )
    runtime.clear_active_skill(session_id=session)
    console.print("[dim]Active skill → <none>[/dim]")


@skill_app.command("active")
def skill_active(
    ctx: typer.Context,
    session: SessionOpt = "default",
    provider: ProviderOpt = None, api_key: ApiKeyOpt = None,
    model: ModelOpt = None, workspace: WorkspaceOpt = None,
    skills_dir: SkillsDirOpt = None,
) -> None:
    """Show the active skill for the current session."""
    runtime = _require_runtime(
        ctx, provider, api_key, model, base_url=None, workspace=workspace,
        skills_dir=skills_dir, enable_rag=False, rag_persist_dir=None,
        enable_mcp=False, mcp_server_url=None,
    )
    skill = runtime.get_active_skill(session_id=session)
    if skill:
        console.print(Panel(
            f"[bold]Objective:[/bold] {skill.objective}\n"
            f"[bold]Tools:[/bold] {', '.join(skill.tools) if skill.tools else '—'}",
            title=f"[bold green]Active: {skill.name}[/bold green]",
            border_style="green",
        ))
    else:
        console.print("[dim]No active skill.[/dim]")


@skill_app.command("import")
def skill_import(
    ctx: typer.Context,
    source: Annotated[str, typer.Argument(help="Path to skill file or directory")],
    fmt: Annotated[str, typer.Option("--format", help="Source format")] = "auto",
    output_dir: Annotated[str, typer.Option("--output-dir", help="Output directory")] = "./skills",
    provider: ProviderOpt = None, api_key: ApiKeyOpt = None,
    model: ModelOpt = None, workspace: WorkspaceOpt = None,
) -> None:
    """Import skills from Claude Code, Superpowers, or other agent ecosystems."""
    from pathlib import Path

    from qaoa.skills.convert import create_default_converter

    source_path = Path(source).resolve()
    converter = create_default_converter()

    if not source_path.exists():
        console.print(f"[red]Source not found:[/red] {source}")
        raise typer.Exit(1)

    files: list[Path] = []
    if source_path.is_file():
        files.append(source_path)
    elif source_path.is_dir():
        for ext in (".md", ".markdown", ".skill", ".toml", ".json", ".yaml", ".yml"):
            files.extend(source_path.glob(f"*{ext}"))
        files.extend(source_path.glob("*/SKILL.md"))
        files.extend(source_path.glob("*/skill.md"))
    else:
        console.print(f"[red]Invalid source:[/red] {source}")
        raise typer.Exit(1)

    if not files:
        console.print("[yellow]No skill files found.[/yellow]")
        raise typer.Exit(1)

    out = Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)

    imported = 0
    failed = 0
    for file_path in files:
        try:
            if fmt == "auto":
                detected = "claude-code"
                if "superpowers" in str(file_path).lower():
                    detected = "superpowers"
                skill = converter.convert(file_path, detected)
            else:
                skill = converter.convert(file_path, fmt)

            output_path = out / f"{skill.name}.md"
            frontmatter = f"---\nname: {skill.name}\ndescription: {skill.description}\nformat: kageko-native\nsource_format: {skill.format}\n"
            if skill.allowed_tools:
                frontmatter += "tools:\n"
                for t in skill.allowed_tools:
                    frontmatter += f"  - {t}\n"
            if skill.permissions:
                frontmatter += "permissions:\n"
                for p in skill.permissions:
                    frontmatter += f"  - {p}\n"
            frontmatter += "---\n\n"
            output_path.write_text(frontmatter + skill.instructions, encoding="utf-8")
            console.print(f"[green]✓[/green] {skill.name} [dim]({skill.format})[/dim] → {output_path}")
            imported += 1
        except Exception as exc:
            console.print(f"[red]✗[/red] {file_path.name}: {exc}")
            failed += 1

    console.print(f"\n[bold]Imported: {imported}[/bold], [red]Failed: {failed}[/red]")
