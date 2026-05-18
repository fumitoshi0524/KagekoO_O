"""Session management commands."""

from __future__ import annotations

from typing import Annotated

import typer
from rich import box
from rich.table import Table

from .._shared import (
    _require_runtime, console,
    ProviderOpt, ApiKeyOpt, ModelOpt, WorkspaceOpt, SkillsDirOpt,
)

session_app = typer.Typer(help="Manage sessions")


@session_app.command("list")
def session_list(
    ctx: typer.Context,
    provider: ProviderOpt = None, api_key: ApiKeyOpt = None,
    model: ModelOpt = None, workspace: WorkspaceOpt = None,
    skills_dir: SkillsDirOpt = None,
) -> None:
    """List all persistent sessions."""
    runtime = _require_runtime(
        ctx, provider, api_key, model, base_url=None, workspace=workspace,
        skills_dir=skills_dir, enable_rag=False, rag_persist_dir=None,
        enable_mcp=False, mcp_server_url=None,
    )
    sessions = runtime.list_sessions()
    if not sessions:
        console.print("[dim]No sessions.[/dim]")
        return
    table = Table(box=box.ROUNDED)
    table.add_column("Session ID", style="cyan")
    for sid in sessions:
        table.add_row(sid)
    console.print(table)


@session_app.command("clear")
def session_clear(
    ctx: typer.Context,
    session_id: Annotated[str, typer.Argument(help="Session ID")],
    provider: ProviderOpt = None, api_key: ApiKeyOpt = None,
    model: ModelOpt = None, workspace: WorkspaceOpt = None,
    skills_dir: SkillsDirOpt = None,
) -> None:
    """Clear a session and its history."""
    runtime = _require_runtime(
        ctx, provider, api_key, model, base_url=None, workspace=workspace,
        skills_dir=skills_dir, enable_rag=False, rag_persist_dir=None,
        enable_mcp=False, mcp_server_url=None,
    )
    runtime.clear_session(session_id=session_id)
    console.print(f"[bold green]✓[/bold green] Cleared session → [cyan]{session_id}[/cyan]")
