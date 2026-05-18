"""Shared CLI utilities — option types, credential resolution, runtime factory."""

from __future__ import annotations

import importlib.metadata
import os
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel

from ..runtime import KagekoRuntime
from .config import load_global_config
from .setup import run_setup_wizard
from .state import CliState

try:
    __version__ = importlib.metadata.version("KagekoO_O")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.1.0"

console = Console()


def _is_interactive() -> bool:
    import sys
    return sys.stdin.isatty()


def _has_credentials(provider: str | None, api_key: str | None) -> bool:
    if provider and api_key:
        return True
    if os.getenv("KAGEKO_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("DEEPSEEK_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or os.getenv("GOOGLE_API_KEY"):
        return True
    config = load_global_config()
    if config.get("api_key"):
        return True
    return False


def _resolve_provider_and_key(provider: str | None, api_key: str | None) -> tuple[str, str]:
    if provider is None:
        provider = os.getenv("KAGEKO_PROVIDER", "").strip()
    if api_key is None:
        api_key = (
            os.getenv("KAGEKO_API_KEY", "").strip()
            or os.getenv("OPENAI_API_KEY", "").strip()
            or os.getenv("DEEPSEEK_API_KEY", "").strip()
            or os.getenv("ANTHROPIC_API_KEY", "").strip()
            or os.getenv("GOOGLE_API_KEY", "").strip()
        )
    config = load_global_config()
    if not provider:
        provider = str(config.get("provider", "")).strip()
    if not api_key:
        api_key = str(config.get("api_key", "")).strip()
    if not api_key and _is_interactive():
        provider, api_key = run_setup_wizard()
    if not api_key:
        console.print(Panel.fit(
            "[bold red]No API key configured.[/bold red]\n\n"
            "Run one of:\n"
            "  [bold]kageko config init[/bold]\n"
            "  [bold]kageko --provider <name> --api-key <key> ...[/bold]\n"
            "Or set [cyan]KAGEKO_API_KEY[/cyan] / [cyan]OPENAI_API_KEY[/cyan] environment variable.",
            title="Setup Required",
            border_style="red",
        ))
        raise typer.Exit(1)
    provider = provider or "openai"
    return provider, api_key


def _get_or_fallback(ctx: typer.Context, name: str, local_value, *, is_bool: bool = False):
    """Return local_value if explicitly provided, otherwise fall back to CLI state.

    For boolean params: False (the Typer default) means "not provided" — fall back to state.
    Only True means the user explicitly enabled it.
    """
    if is_bool:
        if local_value is True:
            return True
    elif local_value is not None:
        return local_value
    state: CliState = ctx.obj
    return getattr(state, name, None)


def _require_runtime(
    ctx: typer.Context,
    provider: str | None, api_key: str | None, model: str | None,
    base_url: str | None, workspace: str | None, skills_dir: str | None,
    enable_rag: bool, rag_persist_dir: str | None,
    enable_mcp: bool, mcp_server_url: str | None,
) -> KagekoRuntime:
    provider = _get_or_fallback(ctx, "provider", provider)
    api_key = _get_or_fallback(ctx, "api_key", api_key)
    model = _get_or_fallback(ctx, "model", model)
    base_url = _get_or_fallback(ctx, "base_url", base_url)
    workspace = _get_or_fallback(ctx, "workspace", workspace)
    skills_dir = _get_or_fallback(ctx, "skills_dir", skills_dir)
    enable_rag = _get_or_fallback(ctx, "enable_rag", enable_rag, is_bool=True)
    rag_persist_dir = _get_or_fallback(ctx, "rag_persist_dir", rag_persist_dir)
    enable_mcp = _get_or_fallback(ctx, "enable_mcp", enable_mcp, is_bool=True)
    mcp_server_url = _get_or_fallback(ctx, "mcp_server_url", mcp_server_url)

    if not _has_credentials(provider, api_key) and _is_interactive():
        provider, api_key = run_setup_wizard()
        state: CliState = ctx.obj
        state.provider = provider
        state.api_key = api_key
    else:
        provider, api_key = _resolve_provider_and_key(provider, api_key)

    state: CliState = ctx.obj
    return state.get_runtime(
        provider=provider, api_key=api_key, model=model, base_url=base_url,
        workspace=workspace, skills_dir=skills_dir, enable_rag=bool(enable_rag),
        rag_persist_dir=rag_persist_dir, enable_mcp=bool(enable_mcp),
        mcp_server_url=mcp_server_url,
    )


# ── Shared option type aliases ─────────────────────────────────────────────

ProviderOpt = Annotated[str | None, typer.Option("--provider", help="LLM provider")]
ApiKeyOpt = Annotated[str | None, typer.Option("--api-key", help="API key for the provider")]
ModelOpt = Annotated[str | None, typer.Option("--model", help="Model name")]
BaseUrlOpt = Annotated[str | None, typer.Option("--base-url", help="Custom provider base URL")]
WorkspaceOpt = Annotated[str | None, typer.Option("--workspace", help="Workspace root directory")]
SkillsDirOpt = Annotated[str | None, typer.Option("--skills-dir", help="Skills directory")]
EnableRagOpt = Annotated[bool, typer.Option("--enable-rag", help="Enable RAG retrieval tools")]
RagPersistDirOpt = Annotated[str | None, typer.Option("--rag-persist-dir", help="RAG persist directory")]
EnableMcpOpt = Annotated[bool, typer.Option("--enable-mcp", help="Enable MCP tools")]
McpServerUrlOpt = Annotated[str | None, typer.Option("--mcp-server-url", help="MCP server URL")]
SessionOpt = Annotated[str, typer.Option("--session", help="Session ID for stateful conversations")]
AutoApproveOpt = Annotated[bool, typer.Option("--auto-approve", help="Auto-approve all tool executions")]
VerboseOpt = Annotated[bool, typer.Option("--verbose", help="Enable verbose logging")]
JsonOpt = Annotated[bool, typer.Option("--json", help="Output in JSON format (for scripting)")]
VersionOpt = Annotated[bool, typer.Option("--version", help="Show version and exit.", is_flag=True, is_eager=True)]


def _spinner_context():
    """Return a context manager that shows a spinner via console.status."""
    return console.status("[dim]Thinking...[/dim]", spinner="dots")
