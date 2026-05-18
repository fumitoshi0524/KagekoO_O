"""Kageko Agent CLI — QAOA-powered tool-using assistant in the terminal."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import typer
from rich.panel import Panel
from rich.console import Console

from ._shared import (
    __version__, console,
    _is_interactive, _has_credentials, _resolve_provider_and_key, _require_runtime,
    ProviderOpt, ApiKeyOpt, ModelOpt, BaseUrlOpt, WorkspaceOpt, SkillsDirOpt,
    EnableRagOpt, RagPersistDirOpt, EnableMcpOpt, McpServerUrlOpt,
    SessionOpt, AutoApproveOpt, VerboseOpt, VersionOpt,
)
from .state import CliState
from .setup import run_setup_wizard

# ── Root Typer app ──────────────────────────────────────────────────────

app = typer.Typer(
    name="kageko",
    help="Kageko Agent CLI — QAOA-powered tool-using assistant",
    no_args_is_help=False,
    rich_markup_mode="rich",
)

# ── Register command groups ─────────────────────────────────────────────

from .commands.chat import chat_command
from .commands.config import config_app
from .commands.pipeline import pipeline_app
from .commands.session import session_app
from .commands.skill import skill_app
from .commands.tool import tool_app

app.command("chat")(chat_command)
app.add_typer(config_app, name="config")
app.add_typer(pipeline_app, name="pipeline")
app.add_typer(session_app, name="session")
app.add_typer(skill_app, name="skill")
app.add_typer(tool_app, name="tool")


# ── Helpers ─────────────────────────────────────────────────────────────

def _resolve_session(runtime, session: str) -> str:
    """Resolve the session ID for a REPL session."""
    if session != "default":
        return session
    sessions = runtime.list_sessions()
    if "default" in sessions and runtime.memory.get_messages("default"):
        return "default"
    return sessions[-1] if sessions else uuid.uuid4().hex[:6]


def _handle_repl_setup(state: CliState, dispatcher, model, base_url, workspace,
                        skills_dir, enable_rag, rag_persist_dir, enable_mcp,
                        mcp_server_url):
    """Handle /setup in the REPL: reconfigure credentials and swap runtime."""
    new_provider, new_key = run_setup_wizard()
    state.provider = new_provider
    state.api_key = new_key
    state.runtime = None
    state.runtime_key = None
    new_runtime = state.get_runtime(
        provider=new_provider, api_key=new_key, model=model, base_url=base_url,
        workspace=workspace, skills_dir=skills_dir, enable_rag=enable_rag,
        rag_persist_dir=rag_persist_dir, enable_mcp=enable_mcp,
        mcp_server_url=mcp_server_url,
    )
    dispatcher.switch_runtime(new_runtime)


# ── Default: REPL ───────────────────────────────────────────────────────

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

    # Credential resolution
    has_credentials = _has_credentials(provider, api_key)
    if not has_credentials and _is_interactive():
        provider, api_key = run_setup_wizard()
        state: CliState = ctx.obj
        state.provider = provider
        state.api_key = api_key
    else:
        provider, api_key = _resolve_provider_and_key(provider, api_key)

    # Runtime
    runtime = _require_runtime(
        ctx, provider, api_key, model, base_url, workspace, skills_dir,
        enable_rag, rag_persist_dir, enable_mcp, mcp_server_url,
    )
    session_id = _resolve_session(runtime, session)
    state = ctx.obj

    # Banner
    raw_key = runtime._api_key or ""
    placeholder_keys = {"test", "your-key", "your-api-key", "sk-test", "placeholder", ""}
    key_warning = ""
    if raw_key.lower() in placeholder_keys:
        key_warning = "\n[bold yellow]⚠ API key looks like a placeholder — type /setup to configure a real one[/bold yellow]"

    from .render import render_welcome
    resolved_workspace = str(Path(workspace or os.getenv("KAGEKO_WORKSPACE") or os.getcwd()).resolve())
    console.print(render_welcome(
        version=__version__,
        provider=runtime.provider,
        model=runtime.model or "default",
        tools=len(runtime.tools.list_specs()),
        skills=len(runtime.list_skills()),
        session=session_id,
        workspace=resolved_workspace,
    ))
    if key_warning:
        console.print(key_warning)

    # REPL
    from .repl import ReplDispatcher, repl_input

    dispatcher = ReplDispatcher(
        runtime=runtime,
        session_id=session_id,
        auto_approve=state.auto_approve,
        workspace=resolved_workspace,
    )
    prompt_session = dispatcher.create_prompt_session()

    while dispatcher.running:
        line = repl_input(prompt_session, message=dispatcher.prompt_message)
        if line is None:
            console.print("\n[dim]Goodbye.[/dim]")
            break
        if not line:
            continue
        if line == "/setup":
            _handle_repl_setup(
                state, dispatcher, model, base_url, workspace, skills_dir,
                enable_rag, rag_persist_dir, enable_mcp, mcp_server_url,
            )
            continue
        dispatcher.dispatch(line)


def _entrypoint() -> None:
    app(prog_name="kageko")


if __name__ == "__main__":
    _entrypoint()
