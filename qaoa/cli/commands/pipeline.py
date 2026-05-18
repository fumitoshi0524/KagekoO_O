"""Unified generation pipeline commands for tools, skills, and QAOA data."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich import box
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from .._shared import (
    _require_runtime, _spinner_context, console,
    ProviderOpt, ApiKeyOpt, ModelOpt, WorkspaceOpt, SkillsDirOpt,
)
from ..errors import format_error
from ..render import CATEGORY_COLORS

pipeline_app = typer.Typer(help="Unified generation pipeline for tools and skills")


@pipeline_app.command("generate-tool")
def pipeline_generate_tool(
    ctx: typer.Context,
    spec: Annotated[str, typer.Argument(help="Natural language spec")],
    name: Annotated[str | None, typer.Option(help="Tool name")] = None,
    category: Annotated[str, typer.Option(help="Functional category")] = "operations",
    domain: Annotated[str, typer.Option(help="Application domain")] = "technology",
    output_dir: Annotated[str, typer.Option(help="Output directory")] = "./tools",
    provider: ProviderOpt = None, api_key: ApiKeyOpt = None,
    model: ModelOpt = None,
) -> None:
    """Generate a tool from natural language spec."""
    runtime = _require_runtime(
        ctx, provider, api_key, model, base_url=None, workspace=None,
        skills_dir=None, enable_rag=False, rag_persist_dir=None,
        enable_mcp=False, mcp_server_url=None,
    )
    with _spinner_context():
        try:
            result = runtime.generate_tool_via_pipeline(
                spec=spec, name=name or spec.replace(" ", "_")[:30],
                category=category, domain=domain, output_dir=output_dir,
            )
        except Exception as e:
            console.print(Panel(format_error(e), border_style="red"))
            raise typer.Exit(1)
    if result.success:
        console.print(f"[bold green]✓[/bold green] Tool generated: [cyan]{result.output_path}[/cyan]")
    else:
        console.print(Panel("\n".join(f"• {e}" for e in result.errors), title="Tool generation failed", border_style="red"))


@pipeline_app.command("generate-skill")
def pipeline_generate_skill(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Skill name")],
    goal: Annotated[str, typer.Argument(help="Skill goal")],
    output_dir: Annotated[str, typer.Option(help="Output directory")] = "./skills",
    provider: ProviderOpt = None, api_key: ApiKeyOpt = None,
    model: ModelOpt = None,
) -> None:
    """Generate a skill from name and goal."""
    runtime = _require_runtime(
        ctx, provider, api_key, model, base_url=None, workspace=None,
        skills_dir=None, enable_rag=False, rag_persist_dir=None,
        enable_mcp=False, mcp_server_url=None,
    )
    with _spinner_context():
        try:
            result = runtime.generate_skill_via_pipeline(name=name, goal=goal, output_dir=output_dir)
        except Exception as e:
            console.print(Panel(format_error(e), border_style="red"))
            raise typer.Exit(1)
    if result.success:
        console.print(f"[bold green]✓[/bold green] Skill generated: [cyan]{result.output_path}[/cyan]")
    else:
        console.print(Panel("\n".join(f"• {e}" for e in result.errors), title="Skill generation failed", border_style="red"))


@pipeline_app.command("generate-tools-batch")
def pipeline_generate_tools_batch(
    ctx: typer.Context,
    spec_file: Annotated[str, typer.Argument(help="JSON file with array of {name, spec, category, domain} objects")],
    output_dir: Annotated[str, typer.Option(help="Output directory")] = "./tools",
    provider: ProviderOpt = None, api_key: ApiKeyOpt = None,
    model: ModelOpt = None,
) -> None:
    """Generate multiple tools from a JSON spec file."""
    spec_path = Path(spec_file)
    if not spec_path.exists():
        console.print(f"[red]Spec file not found:[/red] {spec_file}")
        raise typer.Exit(1)
    try:
        specs = json.loads(spec_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON:[/red] {e}")
        raise typer.Exit(1)
    if not isinstance(specs, list):
        console.print("[red]Spec file must contain a JSON array.[/red]")
        raise typer.Exit(1)

    runtime = _require_runtime(
        ctx, provider, api_key, model, base_url=None, workspace=None,
        skills_dir=None, enable_rag=False, rag_persist_dir=None,
        enable_mcp=False, mcp_server_url=None,
    )
    with Progress(
        SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
        BarColumn(), TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        task = progress.add_task("Generating tools...", total=len(specs))
        results = runtime.generate_tools_batch_via_pipeline(specs=specs, output_dir=output_dir)
        progress.update(task, completed=len(results))
    ok = sum(1 for r in results if r.success)
    fail = len(results) - ok
    console.print(f"[bold green]✓[/bold green] {ok} generated, [red]{fail} failed[/red]")
    for r in results:
        if not r.success:
            console.print(f"  [red]✗[/red] {r.errors}")


@pipeline_app.command("generate-data")
def pipeline_generate_data(
    ctx: typer.Context,
    data_type: Annotated[str, typer.Option(help="Data type: single-hop, multi-hop, or multi-turn")] = "single-hop",
    count: Annotated[int, typer.Option(help="Number of trajectories")] = 10,
    output: Annotated[str, typer.Option(help="Output JSONL path")] = "./data/qaoa_data.jsonl",
    provider: ProviderOpt = None, api_key: ApiKeyOpt = None,
    model: ModelOpt = None, workspace: WorkspaceOpt = None,
    skills_dir: SkillsDirOpt = None,
) -> None:
    """Generate QAOA training data (single-hop, multi-hop, or multi-turn)."""
    runtime = _require_runtime(
        ctx, provider, api_key, model, base_url=None, workspace=workspace,
        skills_dir=skills_dir, enable_rag=False, rag_persist_dir=None,
        enable_mcp=False, mcp_server_url=None,
    )
    tool_specs = [
        {"name": s.name, "description": s.description, "schema": {"type": "object", "properties": {}}, "category": s.category, "domain": s.domain}
        for s in runtime.tools.list_specs()
        if not s.name.startswith("skill.")
    ]
    if not tool_specs:
        console.print("[red]No tools available. Generate tools first.[/red]")
        raise typer.Exit(1)

    with _spinner_context():
        try:
            if data_type == "single-hop":
                result = runtime.generate_qaoa_single_hop_via_pipeline(tool_specs=tool_specs, count=count)
            elif data_type == "multi-hop":
                result = runtime.generate_qaoa_multi_hop_via_pipeline(tool_specs=tool_specs, count=count)
            elif data_type == "multi-turn":
                result = runtime.generate_qaoa_multi_turn_via_pipeline(tool_specs=tool_specs, count=count)
            else:
                console.print(f"[red]Unknown type:[/red] {data_type}. Use single-hop, multi-hop, or multi-turn.")
                raise typer.Exit(1)
        except Exception as e:
            console.print(Panel(format_error(e), border_style="red"))
            raise typer.Exit(1)

    if result.success:
        output_path = Path(output)
        from ...learning import export_conversations_jsonl
        export_conversations_jsonl(turns=result.turns, output_path=output_path)
        console.print(f"[bold green]✓[/bold green] Generated {len(result.turns)} trajectories → [cyan]{output_path}[/cyan]")
    else:
        console.print(Panel(str(result.errors), title="Data generation failed", border_style="red"))


@pipeline_app.command("list-categories")
def pipeline_list_categories() -> None:
    """List UniToolCall functional categories and application domains."""
    from ...types import APPLICATION_DOMAINS, FUNCTIONAL_CATEGORIES

    cat_table = Table(title="Functional Categories", box=box.ROUNDED)
    cat_table.add_column("Category", style="bold")
    cat_table.add_column("Description")
    cat_defs = {
        "analysis": "Data analysis and insights",
        "operations": "Business process operations",
        "system": "System administration and maintenance",
        "visualization": "Data visualization and presentation",
        "search": "Information retrieval and search",
        "generate": "Content and data generation",
    }
    for c in FUNCTIONAL_CATEGORIES:
        color = CATEGORY_COLORS.get(c, "white")
        cat_table.add_row(f"[{color}]{c}[/{color}]", cat_defs.get(c, ""))
    console.print(cat_table)

    dom_table = Table(title="Application Domains", box=box.ROUNDED)
    dom_table.add_column("Domain", style="bold")
    for i, d in enumerate(APPLICATION_DOMAINS):
        if i % 2 == 0:
            dom_table.add_column("", style="dim")
    rows_needed = (len(APPLICATION_DOMAINS) + 1) // 2
    for i in range(rows_needed):
        row = [APPLICATION_DOMAINS[i]]
        if i + rows_needed < len(APPLICATION_DOMAINS):
            row.append(APPLICATION_DOMAINS[i + rows_needed])
        else:
            row.append("")
        dom_table.add_row(*row)
    console.print(dom_table)
