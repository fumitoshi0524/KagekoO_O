"""One-shot chat command."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.markdown import Markdown
from rich.panel import Panel

from .._shared import (
    _require_runtime, _spinner_context, console,
    ProviderOpt, ApiKeyOpt, ModelOpt, BaseUrlOpt,
    WorkspaceOpt, SkillsDirOpt, EnableRagOpt, RagPersistDirOpt,
    EnableMcpOpt, McpServerUrlOpt, SessionOpt,
)
from ..errors import format_error


def chat_command(
    ctx: typer.Context,
    message: Annotated[str, typer.Argument(help="Message to send")],
    stream: Annotated[bool, typer.Option("--stream", help="Stream response in real-time")] = False,
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
    from ...types import AgentMode

    runtime = _require_runtime(
        ctx, provider, api_key, model, base_url, workspace, skills_dir,
        enable_rag, rag_persist_dir, enable_mcp, mcp_server_url,
    )
    if stream:
        from ...streaming import ConsoleStreamRenderer
        renderer = ConsoleStreamRenderer()
        try:
            for event in runtime.run_stream(AgentMode.QAOA, message, session_id=session):
                renderer.on_event(event)
            renderer.on_done()
        except Exception as e:
            renderer.on_done()
            console.print(Panel(format_error(e), border_style="red"))
            raise typer.Exit(1)
    else:
        with _spinner_context():
            try:
                response = runtime.run(AgentMode.QAOA, message, session_id=session)
            except Exception as e:
                console.print(Panel(format_error(e), border_style="red"))
                raise typer.Exit(1)
        console.print(Markdown(response.answer))
