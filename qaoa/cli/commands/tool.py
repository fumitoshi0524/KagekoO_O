"""Tool inspection and invocation commands."""

from __future__ import annotations

from typing import Annotated

import typer
from rich import box
from rich.panel import Panel

from .._shared import (
    _require_runtime, console,
    ProviderOpt, ApiKeyOpt, ModelOpt, WorkspaceOpt, SkillsDirOpt,
    EnableRagOpt, RagPersistDirOpt, EnableMcpOpt, McpServerUrlOpt, JsonOpt,
)
from ..errors import format_error
from ..render import render_tool_table, render_tool_detail

tool_app = typer.Typer(help="Inspect and call tools")


@tool_app.command("list")
def tool_list(
    ctx: typer.Context,
    provider: ProviderOpt = None, api_key: ApiKeyOpt = None,
    model: ModelOpt = None, workspace: WorkspaceOpt = None,
    skills_dir: SkillsDirOpt = None,
    enable_rag: EnableRagOpt = False, rag_persist_dir: RagPersistDirOpt = None,
    enable_mcp: EnableMcpOpt = False, mcp_server_url: McpServerUrlOpt = None,
    json: JsonOpt = False,
) -> None:
    """List all available tools."""
    runtime = _require_runtime(
        ctx, provider, api_key, model, base_url=None, workspace=workspace,
        skills_dir=skills_dir, enable_rag=enable_rag, rag_persist_dir=rag_persist_dir,
        enable_mcp=enable_mcp, mcp_server_url=mcp_server_url,
    )
    specs = runtime.tools.list_specs()
    if json:
        console.print_json(data=[{"name": s.name, "description": s.description,
                                   "category": s.category, "domain": s.domain,
                                   "risk_level": s.risk_level} for s in specs])
    else:
        console.print(render_tool_table(specs))


@tool_app.command("show")
def tool_show(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Tool name")],
    provider: ProviderOpt = None, api_key: ApiKeyOpt = None,
    model: ModelOpt = None, workspace: WorkspaceOpt = None,
    skills_dir: SkillsDirOpt = None,
) -> None:
    """Show tool metadata."""
    runtime = _require_runtime(
        ctx, provider, api_key, model, base_url=None, workspace=workspace,
        skills_dir=skills_dir, enable_rag=False, rag_persist_dir=None,
        enable_mcp=False, mcp_server_url=None,
    )
    spec = runtime.tools.describe(name)
    console.print(render_tool_detail(spec))


@tool_app.command("call")
def tool_call(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Tool name")],
    payload: Annotated[str, typer.Argument(help="Tool payload")],
    provider: ProviderOpt = None, api_key: ApiKeyOpt = None,
    model: ModelOpt = None, workspace: WorkspaceOpt = None,
    skills_dir: SkillsDirOpt = None,
) -> None:
    """Call a tool directly."""
    runtime = _require_runtime(
        ctx, provider, api_key, model, base_url=None, workspace=workspace,
        skills_dir=skills_dir, enable_rag=False, rag_persist_dir=None,
        enable_mcp=False, mcp_server_url=None,
    )
    try:
        output = runtime.tools.call(name, payload)
    except Exception as e:
        console.print(Panel(format_error(e), border_style="red"))
        raise typer.Exit(1)
    console.print(Panel(output, title=f"[bold]Tool: {name}[/bold]", border_style="cyan", box=box.ROUNDED))


@tool_app.command("search")
def tool_search(
    ctx: typer.Context,
    query: Annotated[str, typer.Argument(help="Search query")],
    provider: ProviderOpt = None, api_key: ApiKeyOpt = None,
    model: ModelOpt = None, workspace: WorkspaceOpt = None,
    skills_dir: SkillsDirOpt = None,
) -> None:
    """Search tools by name, description, category, or domain."""
    runtime = _require_runtime(
        ctx, provider, api_key, model, base_url=None, workspace=workspace,
        skills_dir=skills_dir, enable_rag=False, rag_persist_dir=None,
        enable_mcp=False, mcp_server_url=None,
    )
    q = query.lower()
    specs = runtime.tools.list_specs()
    matches = [
        s for s in specs
        if q in s.name.lower() or q in s.description.lower()
        or q in s.category.lower() or q in s.domain.lower()
        or any(q in tag.lower() for tag in s.tags)
    ]
    if not matches:
        console.print(f"[dim]No tools matching '[bold]{query}[/bold]'[/dim]")
        return
    console.print(render_tool_table(matches, highlight=query))
