"""Lightweight CLI for Kageko runtime."""

from __future__ import annotations

import argparse
import shlex
import sys
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from core.models import AgentMode
from runtime import KagekoRuntime, create_runtime

_STYLE_PROMPTS: dict[str, str] = {
    "brief": "Answer in short, dense sentences.",
    "balanced": "Answer clearly with practical structure.",
    "creative": "Answer with imaginative but useful detail.",
}

_PROFILE_PROMPTS: dict[str, str] = {
    "work": "Prioritize professional, precise, and execution-oriented responses.",
    "fun": "Keep responses playful and vivid while staying helpful and actionable.",
}

_RESERVED_SLASH_COMMANDS = {
    "/help",
    "/exit",
    "/quit",
    "/config",
    "/status",
    "/new",
    "/clear",
    "/mode",
    "/model",
    "/provider",
    "/session",
    "/profile",
    "/persona",
    "/system",
    "/style",
    "/skills",
    "/tool",
    "/runtime",
}


@dataclass(slots=True)
class RuntimeSettings:
    provider: str | None = None
    api_key: str | None = None
    model: str | None = None
    base_url: str | None = None
    workspace: str | None = None
    skills_dir: str | None = None
    enable_rag: bool = False
    rag_persist_dir: str | None = None
    enable_mcp: bool = False
    mcp_server_url: str | None = None


@dataclass(slots=True)
class ChatSettings:
    mode: AgentMode = AgentMode.CHAT
    session_id: str = "default"
    profile: str | None = "work"
    persona: str | None = None
    system_prompt: str | None = None
    style: str = "balanced"
    agent_prompt: str | None = None


def _build_runtime(settings: RuntimeSettings) -> KagekoRuntime:
    return create_runtime(
        provider=settings.provider,
        api_key=settings.api_key,
        model=settings.model,
        base_url=settings.base_url,
        workspace=settings.workspace,
        skills_dir=settings.skills_dir,
        enable_rag=settings.enable_rag,
        rag_persist_dir=settings.rag_persist_dir,
        enable_mcp=settings.enable_mcp,
        mcp_server_url=settings.mcp_server_url,
    )


def _default_model_for(provider: str | None) -> str:
    defaults = {
        "openai": "gpt-4.1-mini",
        "deepseek": "deepseek-chat",
        "claude": "claude-3-7-sonnet-latest",
        "gemini": "gemini-2.5-flash",
    }
    normalized = (provider or "openai").strip().lower()
    return defaults.get(normalized, "gpt-4.1-mini")


def _try_rebuild_runtime(settings: RuntimeSettings) -> tuple[KagekoRuntime | None, str | None]:
    try:
        return _build_runtime(settings), None
    except (ValueError, RuntimeError, ModuleNotFoundError) as error:
        return None, str(error)


def _open_config_panel(settings: RuntimeSettings) -> tuple[KagekoRuntime | None, str | None]:
    provider = input(
        "provider [openai/deepseek/claude/gemini] "
        f"({settings.provider or 'openai'}): "
    ).strip().lower()
    if provider:
        settings.provider = provider
    elif settings.provider is None:
        settings.provider = "openai"

    default_model = _default_model_for(settings.provider)
    model = input(f"model ({settings.model or default_model}): ").strip()
    if model:
        settings.model = model
    elif settings.model is None:
        settings.model = default_model

    api_key = input("api key (leave empty to keep env/current): ").strip()
    if api_key:
        settings.api_key = api_key

    base_url = input("base url (optional): ").strip()
    if base_url:
        settings.base_url = base_url

    return _try_rebuild_runtime(settings)


def _workspace_path(raw: str | None) -> Path:
    if raw and raw.strip():
        return Path(raw).resolve()
    return Path.cwd().resolve()


def _load_agent_prompt(workspace: Path) -> str | None:
    agent_file = workspace / "AGENT.md"
    if not agent_file.exists() or not agent_file.is_file():
        return None
    text = agent_file.read_text(encoding="utf-8").strip()
    return text if text else None


def _compose_message(
    message: str,
    *,
    profile: str | None,
    persona: str | None,
    system_prompt: str | None,
    style: str,
    agent_prompt: str | None,
) -> str:
    blocks: list[str] = []
    if agent_prompt:
        blocks.append(f"Workspace AGENT.md:\n{agent_prompt}")
    if system_prompt:
        blocks.append(f"System instruction: {system_prompt}")
    style_prompt = _STYLE_PROMPTS.get(style)
    if style_prompt:
        blocks.append(style_prompt)
    if profile and profile in _PROFILE_PROMPTS:
        blocks.append(_PROFILE_PROMPTS[profile])
    if persona:
        blocks.append(f"Persona: {persona}")
    if not blocks:
        return message
    blocks.append(f"User message:\n{message}")
    return "\n\n".join(blocks)


def _send(runtime: KagekoRuntime, settings: ChatSettings, message: str) -> str:
    final_prompt = _compose_message(
        message,
        profile=settings.profile,
        persona=settings.persona,
        system_prompt=settings.system_prompt,
        style=settings.style,
        agent_prompt=settings.agent_prompt,
    )
    response = runtime.run(
        settings.mode,
        final_prompt,
        session_id=settings.session_id,
    )
    return response.text


def _invoke_skill(runtime: KagekoRuntime, settings: ChatSettings, name: str, user_input: str) -> str:
    tools = runtime.orchestrator.factory.services.tools
    skill_text = tools.call("skill.load", name)
    skill_prompt = (
        "Apply the following skill spec to fulfill the request.\n"
        f"Skill: {name}\n\n"
        f"{skill_text}\n\n"
        f"Request:\n{user_input}"
    )
    return _send(runtime, settings, skill_prompt)


def _as_mode(raw: str) -> AgentMode:
    normalized = raw.strip().lower()
    mode_map = {mode.value: mode for mode in AgentMode}
    if normalized not in mode_map:
        raise ValueError(
            f"Unsupported mode '{raw}'. Available: {', '.join(sorted(mode_map))}."
        )
    return mode_map[normalized]


def _print_repl_help() -> None:
    print("Slash commands:")
    print("  /help                            Show this help")
    print("  /exit or /quit                   Leave REPL")
    print("  /config                          Open config panel (provider/model/key)")
    print("  /status                          Show current runtime/session status")
    print("  /new or /clear                   Start a new session thread")
    print("  /mode [name]                     Get/set mode")
    print("  /model [name]                    Get/set model")
    print("  /provider [name]                 Get/set provider")
    print("  /session <id>                    Set session id")
    print("  /profile <work|fun|off>          Set high-level profile")
    print("  /persona <text|off>              Set persona")
    print("  /system <text|off>               Set extra system prompt")
    print("  /style <brief|balanced|creative> Set response style")
    print("  /skills list [query]             List discoverable skills")
    print("  /skills show <name>              Show one skill metadata")
    print("  /tool <name> <payload>           Run a registered tool directly")
    print("  /runtime                         Show runtime summary")
    print("  /<skill-name> [input]            Invoke skill command dynamically")


def _execute_repl_command(
    line: str,
    *,
    runtime: KagekoRuntime | None,
    runtime_settings: RuntimeSettings,
    chat_settings: ChatSettings,
) -> tuple[KagekoRuntime | None, bool]:
    parts = shlex.split(line)
    if not parts:
        return runtime, True

    command = parts[0].lower()
    if command in {"/exit", "/quit"}:
        return runtime, False
    if command == "/help":
        _print_repl_help()
        return runtime, True
    if command == "/config":
        runtime, error = _open_config_panel(runtime_settings)
        if error is not None:
            print(f"Runtime not ready: {error}")
        else:
            print(
                f"Runtime ready -> provider={runtime.provider if runtime else runtime_settings.provider} "
                f"model={runtime.model if runtime else runtime_settings.model}"
            )
        return runtime, True
    if command in {"/status", "/runtime"}:
        runtime_state = "ready" if runtime is not None else "not-configured"
        print(
            f"state={runtime_state} provider={runtime_settings.provider or '<auto>'} "
            f"model={runtime_settings.model or '<auto>'} mode={chat_settings.mode.value} "
            f"session={chat_settings.session_id} style={chat_settings.style} "
            f"profile={chat_settings.profile or '<off>'}"
        )
        return runtime, True
    if command in {"/new", "/clear"}:
        chat_settings.session_id = f"session-{uuid4().hex[:8]}"
        print(f"New session -> {chat_settings.session_id}")
        return runtime, True

    if command == "/mode":
        if len(parts) < 2:
            print(f"Mode -> {chat_settings.mode.value}")
            return runtime, True
        chat_settings.mode = _as_mode(parts[1])
        print(f"Mode -> {chat_settings.mode.value}")
        return runtime, True

    if command == "/model":
        if len(parts) < 2:
            print(f"Model -> {runtime_settings.model or '<auto>'}")
            return runtime, True
        runtime_settings.model = parts[1]
        runtime, error = _try_rebuild_runtime(runtime_settings)
        if error is not None:
            print(f"Model saved, runtime not ready: {error}")
        else:
            print(f"Model -> {runtime_settings.model}")
        return runtime, True

    if command == "/provider":
        if len(parts) < 2:
            print(f"Provider -> {runtime_settings.provider or '<auto>'}")
            return runtime, True
        provider = parts[1].strip().lower()
        if provider not in {"openai", "deepseek", "claude", "gemini"}:
            raise ValueError("Usage: /provider [openai|deepseek|claude|gemini]")
        runtime_settings.provider = provider
        if runtime_settings.model is None:
            runtime_settings.model = _default_model_for(provider)
        runtime, error = _try_rebuild_runtime(runtime_settings)
        if error is not None:
            print(f"Provider saved, runtime not ready: {error}")
        else:
            print(f"Provider -> {runtime.provider}")
        return runtime, True

    if command == "/session":
        if len(parts) < 2:
            raise ValueError("Usage: /session <id>")
        chat_settings.session_id = parts[1]
        print(f"Session -> {chat_settings.session_id}")
        return runtime, True

    if command == "/profile":
        if len(parts) < 2:
            raise ValueError("Usage: /profile <work|fun|off>")
        raw_profile = parts[1].strip().lower()
        if raw_profile == "off":
            chat_settings.profile = None
        elif raw_profile in _PROFILE_PROMPTS:
            chat_settings.profile = raw_profile
        else:
            raise ValueError("Usage: /profile <work|fun|off>")
        print(f"Profile -> {chat_settings.profile or '<off>'}")
        return runtime, True

    if command == "/persona":
        payload = line.split(" ", 1)[1].strip() if " " in line else ""
        chat_settings.persona = None if payload.lower() == "off" else payload
        print(f"Persona -> {chat_settings.persona or '<off>'}")
        return runtime, True

    if command == "/system":
        payload = line.split(" ", 1)[1].strip() if " " in line else ""
        chat_settings.system_prompt = None if payload.lower() == "off" else payload
        print(f"System prompt -> {chat_settings.system_prompt or '<off>'}")
        return runtime, True

    if command == "/style":
        if len(parts) < 2:
            raise ValueError("Usage: /style <brief|balanced|creative>")
        style = parts[1].strip().lower()
        if style not in _STYLE_PROMPTS:
            raise ValueError(
                f"Unsupported style '{style}'. Available: {', '.join(sorted(_STYLE_PROMPTS))}."
            )
        chat_settings.style = style
        print(f"Style -> {chat_settings.style}")
        return runtime, True

    if command == "/skills":
        if runtime is None:
            print("Runtime not configured. Use /config.")
            return runtime, True
        if len(parts) < 2:
            print("Usage: /skills <list|show> ...")
            return runtime, True
        action = parts[1].lower()
        tools = runtime.orchestrator.factory.services.tools
        if action == "list":
            query = " ".join(parts[2:]).strip()
            print(tools.call("skill.list", query))
            return runtime, True
        if action == "show":
            if len(parts) < 3:
                raise ValueError("Usage: /skills show <name>")
            print(tools.call("skill.describe", parts[2]))
            return runtime, True
        raise ValueError("Usage: /skills <list|show> ...")

    if command == "/tool":
        if runtime is None:
            print("Runtime not configured. Use /config.")
            return runtime, True
        if len(parts) < 3:
            raise ValueError("Usage: /tool <name> <payload>")
        tool_name = parts[1]
        payload = " ".join(parts[2:])
        tools = runtime.orchestrator.factory.services.tools
        print(tools.call(tool_name, payload))
        return runtime, True

    if command.startswith("/") and command not in _RESERVED_SLASH_COMMANDS:
        if runtime is None:
            print("Runtime not configured. Use /config.")
            return runtime, True
        skill_name = command[1:]
        payload = " ".join(parts[1:]).strip()
        print(_invoke_skill(runtime, chat_settings, skill_name, payload))
        return runtime, True

    raise ValueError("Unknown slash command. Use /help.")


def _create_runtime_and_chat_settings(
    args: argparse.Namespace,
) -> tuple[KagekoRuntime, ChatSettings, RuntimeSettings]:
    runtime_settings = RuntimeSettings(
        provider=args.provider,
        api_key=args.api_key,
        model=args.model,
        base_url=args.base_url,
        workspace=args.workspace,
        skills_dir=args.skills_dir,
        enable_rag=args.enable_rag,
        rag_persist_dir=args.rag_persist_dir,
        enable_mcp=args.enable_mcp,
        mcp_server_url=args.mcp_server_url,
    )
    workspace = _workspace_path(args.workspace)
    profile = None if args.profile == "off" else args.profile
    chat_settings = ChatSettings(
        mode=_as_mode(args.mode),
        session_id=args.session_id or f"session-{uuid4().hex[:8]}",
        profile=profile,
        persona=args.persona,
        system_prompt=args.system,
        style=args.style,
        agent_prompt=_load_agent_prompt(workspace),
    )
    runtime = _build_runtime(runtime_settings)
    return runtime, chat_settings, runtime_settings


def _run_chat(args: argparse.Namespace) -> int:
    runtime, chat_settings, _ = _create_runtime_and_chat_settings(args)
    message = " ".join(args.message).strip()
    print(_send(runtime, chat_settings, message))
    return 0


def _run_repl(args: argparse.Namespace) -> int:
    runtime_settings = RuntimeSettings(
        provider=args.provider,
        api_key=args.api_key,
        model=args.model,
        base_url=args.base_url,
        workspace=args.workspace,
        skills_dir=args.skills_dir,
        enable_rag=args.enable_rag,
        rag_persist_dir=args.rag_persist_dir,
        enable_mcp=args.enable_mcp,
        mcp_server_url=args.mcp_server_url,
    )
    workspace = _workspace_path(args.workspace)
    profile = None if args.profile == "off" else args.profile
    chat_settings = ChatSettings(
        mode=_as_mode(args.mode),
        session_id=args.session_id or f"session-{uuid4().hex[:8]}",
        profile=profile,
        persona=args.persona,
        system_prompt=args.system,
        style=args.style,
        agent_prompt=_load_agent_prompt(workspace),
    )
    runtime, error = _try_rebuild_runtime(runtime_settings)
    print("Kageko REPL - lightweight customizable agent shell")
    print("Type /help for commands, /exit to quit.")
    if runtime is None:
        print(f"Runtime not configured: {error}")
        open_now = input("Open config panel now? [Y/n]: ").strip().lower()
        if open_now in {"", "y", "yes"}:
            runtime, panel_error = _open_config_panel(runtime_settings)
            if panel_error is not None:
                print(f"Runtime still not ready: {panel_error}")
    while True:
        try:
            line = input("kageko> ").strip()
        except EOFError:
            print()
            return 0
        if line == "":
            continue
        if line.startswith("/"):
            try:
                runtime, keep_running = _execute_repl_command(
                    line,
                    runtime=runtime,
                    runtime_settings=runtime_settings,
                    chat_settings=chat_settings,
                )
            except (ValueError, RuntimeError, ModuleNotFoundError) as error:
                print(f"error: {error}")
                continue
            if not keep_running:
                return 0
            continue
        if runtime is None:
            print("Runtime not configured. Use /config.")
            continue
        print(_send(runtime, chat_settings, line))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kageko",
        description="Kageko: customizable and lightweight multi-provider agent CLI",
    )
    parser.add_argument(
        "--provider",
        choices=["openai", "deepseek", "claude", "gemini"],
        help="LLM provider",
    )
    parser.add_argument("--api-key", help="Override API key")
    parser.add_argument("--model", help="Model name")
    parser.add_argument("--base-url", help="Custom provider base URL")
    parser.add_argument("--workspace", help="Workspace root")
    parser.add_argument("--skills-dir", help="Skills directory path")
    parser.add_argument(
        "--mode",
        default="chat",
        choices=[mode.value for mode in AgentMode],
        help="Agent mode",
    )
    parser.add_argument("--session-id", help="Conversation session id")
    parser.add_argument(
        "--profile",
        default="work",
        choices=["work", "fun", "off"],
        help="High-level interaction profile",
    )
    parser.add_argument(
        "--style",
        default="balanced",
        choices=sorted(_STYLE_PROMPTS),
        help="Response style",
    )
    parser.add_argument("--persona", help="Persona text")
    parser.add_argument("--system", help="Extra system instruction")
    parser.add_argument(
        "--enable-rag",
        action="store_true",
        help="Enable retriever for rag mode",
    )
    parser.add_argument("--rag-persist-dir", help="RAG storage path")
    parser.add_argument(
        "--enable-mcp",
        action="store_true",
        help="Enable MCP tool registration",
    )
    parser.add_argument("--mcp-server-url", help="MCP server URL")
    parser.add_argument(
        "--repl",
        action="store_true",
        help="Force interactive shell mode",
    )
    parser.add_argument(
        "message",
        nargs="*",
        help="Optional one-shot message; if omitted, starts REPL",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    if raw_argv and raw_argv[0] in {"chat", "repl"}:
        legacy_mode = raw_argv.pop(0)
        if legacy_mode == "repl":
            raw_argv.append("--repl")

    parser = _build_parser()
    args = parser.parse_args(raw_argv)
    try:
        if args.repl or len(args.message) == 0:
            return _run_repl(args)
        return _run_chat(args)
    except (FileNotFoundError, ValueError, RuntimeError, ModuleNotFoundError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
