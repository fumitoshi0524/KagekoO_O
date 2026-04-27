"""Pure-Python CLI for Kageko agent runtime — Rich-powered terminal UI."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.prompt import Prompt
from rich import box

from .runtime import KagekoRuntime, create_runtime
from .types import AgentMode, APPLICATION_DOMAINS, FUNCTIONAL_CATEGORIES

import importlib.metadata

try:
    __version__ = importlib.metadata.version("KagekoO_O")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.1.0"

console = Console()
app = typer.Typer(
    name="kageko",
    help="Kageko Agent CLI — QAOA-powered tool-using assistant",
    no_args_is_help=False,
    rich_markup_mode="rich",
)

# ── Category color map ──────────────────────────────────────────────
CATEGORY_COLORS = {
    "analysis": "blue",
    "operations": "yellow",
    "system": "magenta",
    "visualization": "green",
    "search": "cyan",
    "generate": "red",
}
RISK_COLORS = {"read": "green", "write": "yellow", "destructive": "red"}


class CliState:
    def __init__(
        self,
        provider: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        workspace: str | None = None,
        skills_dir: str | None = None,
        enable_rag: bool = False,
        rag_persist_dir: str | None = None,
        enable_mcp: bool = False,
        mcp_server_url: str | None = None,
        auto_approve: bool = False,
        verbose: bool = False,
    ) -> None:
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.workspace = workspace
        self.skills_dir = skills_dir
        self.enable_rag = enable_rag
        self.rag_persist_dir = rag_persist_dir
        self.enable_mcp = enable_mcp
        self.mcp_server_url = mcp_server_url
        self.auto_approve = auto_approve
        self.verbose = verbose
        self.runtime: KagekoRuntime | None = None
        self.runtime_key: tuple[object, ...] | None = None

    def get_runtime(
        self,
        provider: str | None,
        api_key: str | None,
        model: str | None,
        base_url: str | None,
        workspace: str | None,
        skills_dir: str | None,
        enable_rag: bool,
        rag_persist_dir: str | None,
        enable_mcp: bool,
        mcp_server_url: str | None,
    ) -> KagekoRuntime:
        cache_key = (
            provider, api_key, model, base_url, workspace, skills_dir,
            enable_rag, rag_persist_dir, enable_mcp, mcp_server_url,
        )
        if self.runtime is not None and self.runtime_key == cache_key:
            return self.runtime
        self.runtime = create_runtime(
            provider=provider, api_key=api_key, model=model, base_url=base_url,
            workspace=workspace, skills_dir=skills_dir, enable_rag=enable_rag,
            rag_persist_dir=rag_persist_dir, enable_mcp=enable_mcp,
            mcp_server_url=mcp_server_url,
        )
        self.runtime_key = cache_key
        return self.runtime


# ── Config helpers ──────────────────────────────────────────────────

def _load_global_config() -> dict[str, object]:
    path = Path.home() / ".kageko" / "config.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_global_config(config: dict[str, object]) -> None:
    path = Path.home() / ".kageko" / "config.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _is_interactive() -> bool:
    import sys
    return sys.stdin.isatty()


def _has_credentials(provider: str | None, api_key: str | None) -> bool:
    if provider and api_key:
        return True
    if os.getenv("KAGEKO_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("DEEPSEEK_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or os.getenv("GOOGLE_API_KEY"):
        return True
    config = _load_global_config()
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
    config = _load_global_config()
    if not provider:
        provider = str(config.get("provider", "")).strip()
    if not api_key:
        api_key = str(config.get("api_key", "")).strip()
    if not api_key and _is_interactive():
        provider, api_key = _run_setup_wizard()
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


def _get_or_fallback(ctx: typer.Context, name: str, local_value):
    if local_value is not None and local_value != "":
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
    enable_rag = _get_or_fallback(ctx, "enable_rag", enable_rag)
    rag_persist_dir = _get_or_fallback(ctx, "rag_persist_dir", rag_persist_dir)
    enable_mcp = _get_or_fallback(ctx, "enable_mcp", enable_mcp)
    mcp_server_url = _get_or_fallback(ctx, "mcp_server_url", mcp_server_url)

    if not _has_credentials(provider, api_key) and _is_interactive():
        provider, api_key = _run_setup_wizard()
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


# ── Shared option definitions ───────────────────────────────────────

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


# ── Rich rendering helpers ──────────────────────────────────────────

def _render_tool_table(specs, *, highlight: str = "") -> Table:
    """Render a Rich table of tool specs."""
    table = Table(title="Available Tools", box=box.ROUNDED, highlight=True)
    table.add_column("Name", style="bold cyan", no_wrap=True)
    table.add_column("Category", style="italic")
    table.add_column("Domain")
    table.add_column("Risk", width=5)
    table.add_column("Description", max_width=50)
    for s in specs:
        cat_style = CATEGORY_COLORS.get(s.category, "white")
        risk_style = RISK_COLORS.get(s.risk_level, "white")
        name_style = "bold cyan" if highlight and highlight.lower() in s.name.lower() else "cyan"
        table.add_row(
            f"[{name_style}]{s.name}[/{name_style}]",
            f"[{cat_style}]{s.category}[/{cat_style}]",
            s.domain,
            f"[{risk_style}]⬤[/{risk_style}]",
            s.description[:80],
        )
    return table


def _render_skill_table(skills) -> Table:
    table = Table(title="Skills", box=box.ROUNDED)
    table.add_column("Name", style="bold green")
    table.add_column("Objective", max_width=60)
    table.add_column("Tools")
    for s in skills:
        table.add_row(s.name, s.objective, ", ".join(s.tools) if s.tools else "—")
    return table


def _render_tool_detail(spec) -> Panel:
    cat_color = CATEGORY_COLORS.get(spec.category, "white")
    risk_color = RISK_COLORS.get(spec.risk_level, "white")
    body = (
        f"[bold]Name:[/bold] {spec.name}\n"
        f"[bold]Category:[/bold] [{cat_color}]{spec.category}[/{cat_color}]\n"
        f"[bold]Domain:[/bold] {spec.domain}\n"
        f"[bold]Risk:[/bold] [{risk_color}]{spec.risk_level}[/{risk_color}]\n"
        f"[bold]Input:[/bold] {spec.input_contract}\n"
        f"[bold]Output:[/bold] {spec.output_contract}\n"
        f"[bold]Tags:[/bold] {', '.join(spec.tags) if spec.tags else '—'}\n\n"
        f"[bold]Description:[/bold]\n{spec.description}"
    )
    return Panel(body, title=f"[bold]Tool: {spec.name}[/bold]", border_style=cat_color, box=box.ROUNDED)


def _format_error(error_msg: str) -> str:
    """Return a colorized error message."""
    if "401" in error_msg or "403" in error_msg or "invalid_api_key" in error_msg or "Incorrect API key" in error_msg:
        return "[bold red]Authentication failed[/bold red] — your API key is invalid or expired.\nRun [bold]/setup[/bold] or [bold]kageko config init[/bold]"
    if "insufficient_quota" in error_msg or "429" in error_msg:
        return "[bold yellow]API quota exceeded.[/bold yellow] Check your billing/usage limits."
    if "connection" in error_msg.lower() or "timeout" in error_msg.lower():
        return f"[bold red]Connection error:[/bold red] {error_msg}"
    return f"[red]{error_msg}[/red]"


def _spinner_context():
    """Return a context manager that shows a spinner via console.status."""
    return console.status("[dim]Thinking...[/dim]", spinner="dots")


# ── Chat ────────────────────────────────────────────────────────────

@app.command("chat")
def chat_command(
    ctx: typer.Context,
    message: Annotated[str, typer.Argument(help="Message to send")],
    provider: ProviderOpt = None,
    api_key: ApiKeyOpt = None,
    model: ModelOpt = None,
    base_url: BaseUrlOpt = None,
    workspace: WorkspaceOpt = None,
    skills_dir: SkillsDirOpt = None,
    enable_rag: EnableRagOpt = False,
    rag_persist_dir: RagPersistDirOpt = None,
    enable_mcp: EnableMcpOpt = False,
    mcp_server_url: McpServerUrlOpt = None,
    session: SessionOpt = "default",
) -> None:
    """Send a one-shot message to the agent."""
    runtime = _require_runtime(
        ctx, provider, api_key, model, base_url, workspace, skills_dir,
        enable_rag, rag_persist_dir, enable_mcp, mcp_server_url,
    )
    with _spinner_context():
        try:
            response = runtime.run(AgentMode.QAOA, message, session_id=session)
        except Exception as e:
            console.print(Panel(_format_error(str(e)), border_style="red"))
            raise typer.Exit(1)
    console.print(Markdown(response.answer))


# ── Skill subcommands ───────────────────────────────────────────────

skill_app = typer.Typer(help="Manage skills")
app.add_typer(skill_app, name="skill")


@skill_app.command("list")
def skill_list(
    ctx: typer.Context,
    provider: ProviderOpt = None, api_key: ApiKeyOpt = None,
    model: ModelOpt = None, workspace: WorkspaceOpt = None,
    skills_dir: SkillsDirOpt = None,
) -> None:
    """List all skills."""
    runtime = _require_runtime(
        ctx, provider, api_key, model, base_url=None, workspace=workspace,
        skills_dir=skills_dir, enable_rag=False, rag_persist_dir=None,
        enable_mcp=False, mcp_server_url=None,
    )
    skills = runtime.list_skills()
    if not skills:
        console.print("[dim]No skills found.[/dim]")
        return
    console.print(_render_skill_table(skills))


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
            console.print(Panel(_format_error(str(e)), border_style="red"))
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


# ── Tool subcommands ────────────────────────────────────────────────

tool_app = typer.Typer(help="Inspect and call tools")
app.add_typer(tool_app, name="tool")


@tool_app.command("list")
def tool_list(
    ctx: typer.Context,
    provider: ProviderOpt = None, api_key: ApiKeyOpt = None,
    model: ModelOpt = None, workspace: WorkspaceOpt = None,
    skills_dir: SkillsDirOpt = None,
    enable_rag: EnableRagOpt = False, rag_persist_dir: RagPersistDirOpt = None,
    enable_mcp: EnableMcpOpt = False, mcp_server_url: McpServerUrlOpt = None,
) -> None:
    """List all available tools."""
    runtime = _require_runtime(
        ctx, provider, api_key, model, base_url=None, workspace=workspace,
        skills_dir=skills_dir, enable_rag=enable_rag, rag_persist_dir=rag_persist_dir,
        enable_mcp=enable_mcp, mcp_server_url=mcp_server_url,
    )
    specs = runtime.tools.list_specs()
    console.print(_render_tool_table(specs))


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
    console.print(_render_tool_detail(spec))


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
        console.print(Panel(_format_error(str(e)), border_style="red"))
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
    console.print(_render_tool_table(matches, highlight=query))


# ── Config subcommands ──────────────────────────────────────────────

config_app = typer.Typer(help="Manage configuration")
app.add_typer(config_app, name="config")


@config_app.command("init")
def config_init() -> None:
    """Initialize Kageko configuration interactively."""
    _run_setup_wizard()


@config_app.command("get")
def config_get(key: Annotated[str, typer.Argument(help="Config key")]) -> None:
    config = _load_global_config()
    value = config.get(key)
    console.print(f"[dim]{key}[/dim] = {'[dim]<not set>[/dim]' if value is None else str(value)}")


@config_app.command("set")
def config_set(
    key: Annotated[str, typer.Argument(help="Config key")],
    value: Annotated[str, typer.Argument(help="Config value")],
) -> None:
    config = _load_global_config()
    parsed: object = value
    if value == "true":
        parsed = True
    elif value == "false":
        parsed = False
    elif value.isdigit():
        parsed = int(value)
    config[key] = parsed
    _save_global_config(config)
    console.print(f"[bold green]✓[/bold green] {key} = {parsed}")


@config_app.command("list")
def config_list() -> None:
    config = _load_global_config()
    if not config:
        console.print("[dim]No configuration set.[/dim]")
        return
    for k, v in sorted(config.items()):
        console.print(f"  [dim]{k}[/dim] = {json.dumps(v, ensure_ascii=False)}")


# ── Session subcommands ─────────────────────────────────────────────

session_app = typer.Typer(help="Manage sessions")
app.add_typer(session_app, name="session")


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


# ── Pipeline subcommands ────────────────────────────────────────────

pipeline_app = typer.Typer(help="Unified generation pipeline for tools and skills")
app.add_typer(pipeline_app, name="pipeline")


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
            console.print(Panel(_format_error(str(e)), border_style="red"))
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
            console.print(Panel(_format_error(str(e)), border_style="red"))
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
    results = runtime.generate_tools_batch_via_pipeline(specs=specs, output_dir=output_dir)
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
            console.print(Panel(_format_error(str(e)), border_style="red"))
            raise typer.Exit(1)

    if result.success:
        output_path = Path(output)
        from qaoa.learning import export_conversations_jsonl
        export_conversations_jsonl(turns=result.turns, output_path=output_path)
        console.print(f"[bold green]✓[/bold green] Generated {len(result.turns)} trajectories → [cyan]{output_path}[/cyan]")
    else:
        console.print(Panel(str(result.errors), title="Data generation failed", border_style="red"))


@pipeline_app.command("list-categories")
def pipeline_list_categories() -> None:
    """List UniToolCall functional categories and application domains."""
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


# ── Setup wizard ────────────────────────────────────────────────────

def _run_setup_wizard() -> tuple[str, str]:
    """Interactive setup wizard with Rich styling."""
    console.print()
    console.print(Panel(
        "[bold cyan]Welcome to Kageko Agent CLI[/bold cyan]\n"
        "[dim]QAOA-powered tool-using assistant[/dim]\n\n"
        "Let's set up your LLM provider. You only need to do this once.\n"
        "Credentials are saved to [dim]~/.kageko/config.json[/dim]",
        border_style="cyan",
        box=box.ROUNDED,
    ))
    console.print("[bold]Supported providers:[/bold] openai, deepseek, claude, gemini")
    provider = Prompt.ask("Provider", default="openai").strip().lower() or "openai"
    while True:
        api_key = Prompt.ask(f"API key for [bold]{provider}[/bold]").strip()
        if api_key:
            break
        console.print("[yellow]API key is required.[/yellow] Press Ctrl+C to exit.")
    model = Prompt.ask("Model", default="").strip() or None
    config = _load_global_config()
    config["provider"] = provider
    config["api_key"] = api_key
    if model:
        config["model"] = model
    _save_global_config(config)
    console.print(f"\n[bold green]✓ Configuration saved[/bold green] to [dim]{Path.home() / '.kageko' / 'config.json'}[/dim]")
    console.print(f"   Provider: [bold]{provider}[/bold]")
    console.print(f"   You can now run [bold]kageko[/bold] without any arguments.\n")
    return provider, api_key


# ── Default: REPL ───────────────────────────────────────────────────

VersionOpt = Annotated[bool, typer.Option("--version", help="Show version and exit.", is_flag=True, is_eager=True)]


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: VersionOpt = False,
    provider: ProviderOpt = None, api_key: ApiKeyOpt = None,
    model: ModelOpt = None, base_url: BaseUrlOpt = None,
    workspace: WorkspaceOpt = None, skills_dir: SkillsDirOpt = None,
    enable_rag: EnableRagOpt = False, rag_persist_dir: RagPersistDirOpt = None,
    enable_mcp: EnableMcpOpt = False, mcp_server_url: McpServerUrlOpt = None,
    session: SessionOpt = "default",
    auto_approve: AutoApproveOpt = False, verbose: VerboseOpt = False,
) -> None:
    """Interactive REPL (default when no subcommand is given)."""
    if version:
        console.print(f"kageko {__version__}")
        raise typer.Exit()
    ctx.obj = CliState(
        provider=provider, api_key=api_key, model=model, base_url=base_url,
        workspace=workspace, skills_dir=skills_dir, enable_rag=enable_rag,
        rag_persist_dir=rag_persist_dir, enable_mcp=enable_mcp,
        mcp_server_url=mcp_server_url, auto_approve=auto_approve, verbose=verbose,
    )
    if ctx.invoked_subcommand is not None:
        return

    has_credentials = _has_credentials(provider, api_key)
    if not has_credentials and _is_interactive():
        provider, api_key = _run_setup_wizard()
        state: CliState = ctx.obj
        state.provider = provider
        state.api_key = api_key
    else:
        provider, api_key = _resolve_provider_and_key(provider, api_key)

    runtime = _require_runtime(
        ctx, provider, api_key, model, base_url, workspace, skills_dir,
        enable_rag, rag_persist_dir, enable_mcp, mcp_server_url,
    )
    session_id = session
    state = ctx.obj

    # Startup banner
    raw_key = runtime._api_key or ""
    placeholder_keys = {"test", "your-key", "your-api-key", "sk-test", "placeholder", ""}
    key_warning = ""
    if raw_key.lower() in placeholder_keys:
        key_warning = "\n[bold yellow]⚠ API key looks like a placeholder — type /setup to configure a real one[/bold yellow]"

    console.print(Panel(
        f"[bold cyan]Kageko Agent[/bold cyan] [dim]v{__version__}[/dim]\n"
        f"Provider: [bold]{runtime.provider}[/bold]  |  Model: [bold]{runtime.model}[/bold]  |  Tools: [bold]{len(runtime.tools.list_specs())}[/bold]"
        f"{key_warning}\n\n"
        "Type [bold]/help[/bold] for commands, [bold]/exit[/bold] to quit.",
        border_style="cyan",
        box=box.ROUNDED,
    ))

    # REPL loop
    while True:
        try:
            line = Prompt.ask("\n[bold cyan]kageko[/bold cyan]").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye.[/dim]")
            break
        if not line:
            continue

        # ── REPL meta-commands ──────────────────────────────────────
        if line in ("/exit", "/quit"):
            console.print("[dim]Goodbye.[/dim]")
            break
        if line == "/help":
            console.print(Panel(
                "[bold]Session:[/bold]\n  /session <id> — switch session\n\n"
                "[bold]Skills:[/bold]\n  /skill list | /skill generate <name> <goal>\n"
                "  /skill use <name> | /skill clear | /skill active\n\n"
                "[bold]Tools:[/bold]\n  /tools list | /tools show <name>\n"
                "  /tool <name> <payload> | /search <query>\n\n"
                "[bold]Info:[/bold]\n  /categories | /setup\n\n"
                "[bold]Other:[/bold]\n  /help | /exit | /quit",
                title="Commands",
                border_style="cyan",
                box=box.ROUNDED,
            ))
            continue
        if line.startswith("/session "):
            session_id = line[len("/session "):].strip() or "default"
            console.print(f"[dim]Session →[/dim] [cyan]{session_id}[/cyan]")
            continue
        if line == "/session":
            console.print(f"[dim]Current session:[/dim] [cyan]{session_id}[/cyan]")
            console.print("[dim]Usage: /session <id>[/dim]")
            continue
        if line == "/skill" or line == "/skills":
            console.print(
                "[bold]Skill commands:[/bold]\n"
                "  /skill list — list all skills\n"
                "  /skill generate [bold]<name> <goal>[/bold] — generate a new skill\n"
                "  /skill use [bold]<name>[/bold] — activate a skill for this session\n"
                "  /skill clear — deactivate the active skill\n"
                "  /skill active — show the active skill"
            )
            continue
        if line == "/skill list":
            skills = runtime.list_skills()
            if not skills:
                console.print("[dim]No skills found.[/dim]")
            else:
                console.print(_render_skill_table(skills))
            continue
        if line.startswith("/skill generate "):
            rest = line[len("/skill generate "):].strip()
            parts = rest.split(" ", 1)
            if len(parts) < 2:
                console.print("[yellow]Usage: /skill generate <name> <goal>[/yellow]")
                continue
            with _spinner_context():
                try:
                    skill = runtime.generate_skill(name=parts[0], objective=parts[1])
                except Exception as e:
                    console.print(Panel(_format_error(str(e)), border_style="red"))
                    continue
            console.print(Panel(
                f"[bold]Name:[/bold] {skill.name}\n[bold]Objective:[/bold] {skill.objective}\n"
                f"[bold]Tools:[/bold] {', '.join(skill.tools) if skill.tools else '—'}\n"
                f"[bold]Steps:[/bold]\n" + "\n".join(f"  {i}. {s}" for i, s in enumerate(skill.steps, 1)),
                title=f"[bold green]Skill: {skill.name}[/bold green]",
                border_style="green",
                box=box.ROUNDED,
            ))
            continue
        if line.startswith("/skill use "):
            name = line[len("/skill use "):].strip()
            runtime.activate_skill(session_id=session_id, name=name)
            console.print(f"[bold green]✓[/bold green] Active skill → [bold]{name}[/bold]")
            continue
        if line == "/skill clear":
            runtime.clear_active_skill(session_id=session_id)
            console.print("[dim]Active skill → <none>[/dim]")
            continue
        if line == "/skill active":
            skill = runtime.get_active_skill(session_id=session_id)
            if skill:
                console.print(f"[bold green]Active:[/bold green] {skill.name} — {skill.objective}")
            else:
                console.print("[dim]No active skill.[/dim]")
            continue
        if line == "/tools" or line == "/tool":
            console.print(
                "[bold]Tool commands:[/bold]\n"
                "  /tools list — list all available tools\n"
                "  /tools show [bold]<name>[/bold] — show tool details\n"
                "  /tool [bold]<name> <payload>[/bold] — call a tool directly\n"
                "  /search [bold]<query>[/bold] — search tools by name/description/category"
            )
            continue
        if line == "/tools list":
            specs = runtime.tools.list_specs()
            console.print(_render_tool_table(specs))
            continue
        if line == "/tools show":
            console.print("[yellow]Usage: /tools show <name>[/yellow]")
            continue
        if line.startswith("/tools show "):
            name = line[len("/tools show "):].strip()
            spec = runtime.tools.describe(name)
            console.print(_render_tool_detail(spec))
            continue
        if line.startswith("/tool "):
            rest = line[len("/tool "):].strip()
            parts = rest.split(" ", 1)
            if len(parts) < 1:
                console.print("[yellow]Usage: /tool <name> <payload>[/yellow]")
                continue
            tname = parts[0]
            tpayload = parts[1] if len(parts) > 1 else ""
            try:
                output = runtime.tools.call(tname, tpayload)
            except Exception as e:
                console.print(Panel(_format_error(str(e)), border_style="red"))
                continue
            console.print(Panel(output, title=f"[bold]Tool: {tname}[/bold]", border_style="cyan", box=box.ROUNDED))
            continue
        if line.startswith("/search "):
            query = line[len("/search "):].strip().lower()
            specs = runtime.tools.list_specs()
            matches = [
                s for s in specs
                if query in s.name.lower() or query in s.description.lower()
                or query in s.category.lower() or query in s.domain.lower()
            ]
            if not matches:
                console.print(f"[dim]No tools matching '[bold]{query}[/bold]'[/dim]")
            else:
                console.print(_render_tool_table(matches, highlight=query))
            continue
        if line == "/categories":
            console.print("[bold]Categories:[/bold] " + " ".join(
                f"[{CATEGORY_COLORS.get(c,'white')}]{c}[/{CATEGORY_COLORS.get(c,'white')}]"
                for c in FUNCTIONAL_CATEGORIES
            ))
            console.print("[bold]Domains:[/bold] " + ", ".join(APPLICATION_DOMAINS))
            continue
        if line == "/setup":
            new_provider, new_key = _run_setup_wizard()
            state.provider = new_provider
            state.api_key = new_key
            state.runtime = None
            state.runtime_key = None
            runtime = state.get_runtime(
                provider=new_provider, api_key=new_key, model=model, base_url=base_url,
                workspace=workspace, skills_dir=skills_dir, enable_rag=enable_rag,
                rag_persist_dir=rag_persist_dir, enable_mcp=enable_mcp,
                mcp_server_url=mcp_server_url,
            )
            continue

        # Catch unrecognized /commands before hitting the LLM
        if line.startswith("/"):
            console.print(f"[yellow]Unknown command:[/yellow] [bold]{line.split()[0]}[/bold]")
            console.print("[dim]Type /help to see available commands.[/dim]")
            continue

        # ── Agent interaction ───────────────────────────────────────
        if not state.auto_approve:
            planned_actions = runtime.engine.plan_actions(
                query=line, skill=runtime.get_active_skill(session_id=session_id)
            )
            risky = []
            for action in planned_actions:
                try:
                    spec = runtime.tools.describe(action.name)
                    if spec.risk_level != "read":
                        risky.append(action.name)
                except ValueError:
                    pass
            if risky:
                risk_list = ", ".join(f"[yellow]{r}[/yellow]" for r in risky)
                console.print(f"Planned: {', '.join(a.name for a in planned_actions)}")
                console.print(f"Risky: {risk_list}")
                confirm = Prompt.ask("Approve?", default="n").strip().lower()
                if confirm not in ("y", "yes"):
                    console.print("[dim]Cancelled.[/dim]")
                    continue

        with _spinner_context():
            try:
                response = runtime.run(AgentMode.QAOA, line, session_id=session_id)
            except Exception as e:
                console.print(Panel(_format_error(str(e)), border_style="red"))
                continue
        console.print(Markdown(response.answer))


def _entrypoint() -> None:
    app()


if __name__ == "__main__":
    _entrypoint()
