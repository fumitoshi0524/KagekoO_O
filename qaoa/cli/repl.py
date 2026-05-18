"""REPL command dispatcher for Kageko Agent CLI — with tab completion and safety prompts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import CompleteEvent, Completer, Completion, WordCompleter
from prompt_toolkit.document import Document
from prompt_toolkit.history import FileHistory
from prompt_toolkit.shortcuts import prompt as pt_prompt
from prompt_toolkit.styles import Style
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .render import CATEGORY_COLORS, render_tool_detail, render_tool_table, render_hud_prompt

if TYPE_CHECKING:
    from ..runtime import KagekoRuntime


console = Console()

# ── prompt_toolkit styling ──────────────────────────────────────────────

REPL_STYLE = Style.from_dict({
    "prompt": "ansicyan bold",
    "separator": "ansicyan",
})


# ── Tab completion for /commands ────────────────────────────────────────

AVAILABLE_THEMES: list[str] = [
    "onedark",
    "monokai",
    "solarized-light",
    "dracula",
    "nord",
]

COMMAND_SPECS: dict[str, str] = {
    "/exit":           "Exit the REPL",
    "/quit":           "Exit the REPL",
    "/help":           "Show available commands",
    "/session":        "Show or switch session — /session <id>",
    "/skill":          "Skill management — /skill list|generate|use|clear|active|import",
    "/skills":         "List all available skills",
    "/tools":          "Tool inspection — /tools list|show <name>",
    "/tool":           "Call a tool directly — /tool <name> <payload>",
    "/search":         "Search tools by name or description — /search <query>",
    "/categories":     "List UniToolCall categories and domains",
    "/activate":       "Activate a skill — /activate <skill-name>",
    "/mode":           "Permission mode control — /mode [name] or /mode to list all",
    "/setup":          "Reconfigure provider and API key",
    "/theme":          "Display or switch themes — /theme [name|number]",
    "/commands":       "Searchable command list — /commands [filter]",
    "/model":          "Show current model — /model",
    "/display":        "Show display modes — /display",
    "/history":        "Show recent sessions — /history",
    "/init":           "Initialize .kageko/ directory — /init",
    "/clear":          "Clear the screen — /clear",
    "/plan":           "Enable plan mode (read-only) — /plan",
    "/status":         "Show system status — /status",
    "/doctor":         "Diagnose configuration — /doctor",
    "/logs":           "Show recent logs — /logs",
}

SUB_COMMANDS: dict[str, list[str]] = {
    "/skill":  ["list", "generate", "use", "clear", "active", "import"],
    "/tools":  ["list", "show"],
    "/session": [],
}

PERMISSION_MODES: dict[str, str] = {
    "default":     "Ask before each write/destructive tool — safest for exploration",
    "auto":        "Auto-approve everything — fastest, use when you trust the agent",
    "plan":        "Read-only — tools that write are skipped, ideal for architecture & review",
    "acceptEdits": "Auto-approve file edits but ask for bash/destructive — good for coding",
    "bypass":      "Skip all permission checks entirely — only for fully trusted scripts",
}


class KagekoCompleter(Completer):
    """Tab-completer that suggests /commands and sub-commands."""

    def get_completions(self, document: Document, complete_event: CompleteEvent):
        text_before = document.text_before_cursor
        # Check if we're after a recognized command with trailing space
        trailing_space = text_before.endswith(" ")
        words = text_before.split()

        # Completing the first word — suggest /commands
        if len(words) <= 1 and not trailing_space:
            prefix = words[0] if words else ""
            for cmd, desc in COMMAND_SPECS.items():
                if cmd.startswith(prefix):
                    yield Completion(
                        cmd,
                        start_position=-len(prefix),
                        display_meta=desc,
                        selected_style="bg:ansicyan fg:ansiblack",
                    )
            return

        # Completing sub-commands after /skill or /tools
        cmd = words[0]
        if cmd in SUB_COMMANDS and trailing_space:
            # We're after "cmd " — show sub-commands
            prefix = words[1] if len(words) > 1 else ""
            for sub in SUB_COMMANDS[cmd]:
                if sub.startswith(prefix):
                    yield Completion(
                        sub,
                        start_position=-len(prefix),
                        selected_style="bg:ansicyan fg:ansiblack",
                    )
            return

        # Still typing the first word — show matching commands
        if not trailing_space:
            prefix = words[0]
            for cmd, desc in COMMAND_SPECS.items():
                if cmd.startswith(prefix):
                    yield Completion(
                        cmd,
                        start_position=-len(prefix),
                        display_meta=desc,
                        selected_style="bg:ansicyan fg:ansiblack",
                    )


# ── Tool risk display ───────────────────────────────────────────────────

RISK_ICONS = {"read": "📖", "write": "✏️", "destructive": "⚠️"}
RISK_STYLES = {"read": "green", "write": "yellow", "destructive": "bold red"}


def _format_risk_badge(risk_level: str) -> str:
    icon = RISK_ICONS.get(risk_level, "•")
    color = RISK_STYLES.get(risk_level, "white")
    return f"[{color}]{icon} {risk_level}[/{color}]"


# ── ReplDispatcher ──────────────────────────────────────────────────────

@dataclass(slots=True, kw_only=True)
class ReplDispatcher:
    """Dispatches REPL commands with tab completion and safety prompts."""

    runtime: KagekoRuntime
    session_id: str
    auto_approve: bool = False
    workspace: str = ""
    _commands: dict = field(default_factory=dict)
    _running: bool = field(default=True)
    _approved_tools: set = field(default_factory=set)
    _permission_mode: str = "default"

    def __post_init__(self) -> None:
        self._commands = {
            "/exit": self._cmd_exit,
            "/quit": self._cmd_exit,
            "/help": self._cmd_help,
            "/session": self._cmd_session,
            "/skill": self._cmd_skill_dispatch,
            "/skills": self._cmd_skills_menu,
            "/tools": self._cmd_tools_menu,
            "/tool": self._cmd_tool_call,
            "/search": self._cmd_search,
            "/categories": self._cmd_categories,
            "/activate": self._cmd_activate_skill,
            "/mode": self._cmd_mode,
            "/theme": self._cmd_theme,
            "/commands": self._cmd_commands,
            "/model": self._cmd_model,
            "/display": self._cmd_display,
            "/history": self._cmd_history,
            "/init": self._cmd_init_project,
            "/clear": self._cmd_clear_screen,
            "/plan": self._cmd_plan,
            "/status": self._cmd_status,
            "/doctor": self._cmd_doctor,
            "/logs": self._cmd_logs,
        }
        self._running = True
        self._approved_tools = set()

    def dispatch(self, line: str) -> bool:
        if not line:
            return True
        try:
            if line.startswith("/"):
                parts = line.split()
                cmd = parts[0]
                handler = self._commands.get(cmd)
                if handler is not None:
                    return handler(line)
                # Fuzzy suggestion — match by prefix length
                matches = [c for c in self._commands if c.startswith(cmd[:max(3, len(cmd))])]
                if matches:
                    console.print(f"[yellow]Unknown command:[/yellow] [bold]{cmd}[/bold] — did you mean [green]{', '.join(matches[:3])}[/green]?")
                else:
                    console.print(f"[yellow]Unknown command:[/yellow] [bold]{cmd}[/bold]")
                    console.print("[dim]Type /help to see available commands.[/dim]")
                return True
            return self._handle_agent_query(line)
        except Exception as exc:
            from .errors import format_error
            console.print(Panel(format_error(exc), border_style="red", title="Error"))
            return True

    def switch_runtime(self, runtime: object) -> None:
        """Swap the runtime instance without recreating the prompt session."""
        self.runtime = runtime

    @property
    def running(self) -> bool:
        return self._running

    @property
    def prompt_message(self) -> list[tuple[str, str]]:
        """Build the HUD-style REPL prompt."""
        provider = getattr(self.runtime, 'provider', '?')
        model = getattr(self.runtime, 'model', '?') or '?'
        mode = self._permission_mode
        session = self.session_id
        msg_count = len(self.runtime.memory.get_messages(self.session_id)) if hasattr(self.runtime, 'memory') else 0
        hud = render_hud_prompt(provider=provider, model=model, mode=mode, session=session, msg_count=msg_count)
        # Return as prompt_toolkit style tuples — first line is HUD, second is the input marker
        lines = hud.strip().split("\n")
        if len(lines) >= 2:
            return [("class:prompt", lines[0] + "\n"), ("class:separator", lines[1] + " ")]
        return [("class:prompt", hud.strip() + " ")]

    # ── Interactive selector ────────────────────────────────────────────

    def _pick_option(self, title: str, options: dict[str, str]) -> str | None:
        """Interactive option picker with arrow-key navigation via tab completion.

        Shows a titled list of options, then prompts the user to pick one.
        Tab triggers the completion menu; arrows navigate; Enter selects.
        """
        option_names = list(options.keys())
        console.print(f"\n[bold]{title}[/bold]")
        for i, (name, desc) in enumerate(options.items(), 1):
            marker = " [bold green]◀ current[/bold green]" if name == self._permission_mode else ""
            console.print(f"  {i}. [cyan]{name:<14}[/cyan] {desc}{marker}")

        completer = WordCompleter(option_names, ignore_case=True, sentence=True)
        try:
            choice = pt_prompt(
                "\n  Pick an option (Tab to see list, arrows to choose): ",
                completer=completer,
                complete_while_typing=False,
                style=REPL_STYLE,
            ).strip()
        except (EOFError, KeyboardInterrupt):
            return None

        if choice in options:
            return choice
        # Try numeric fallback
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(option_names):
                return option_names[idx]
        return None

    # ── Tab completion helper ──────────────────────────────────────────

    def create_prompt_session(self) -> PromptSession:
        return PromptSession(
            completer=KagekoCompleter(),
            style=REPL_STYLE,
            complete_while_typing=True,
            reserve_space_for_menu=4,
        )

    # ── Commands ───────────────────────────────────────────────────────

    def _cmd_exit(self, _line: str) -> bool:
        self._running = False
        console.print("[dim]Goodbye.[/dim]")
        return False

    def _cmd_help(self, _line: str) -> bool:
        cmd_list = "\n".join(
            f"  [bold cyan]{cmd.ljust(16)}[/bold cyan] [dim]{desc}[/dim]"
            for cmd, desc in sorted(COMMAND_SPECS.items())
        )
        console.print(Panel(
            f"{cmd_list}\n\n"
            "[dim]Tab-completion is available — press[/dim] [bold]Tab[/bold] [dim]while typing a /command[/dim]",
            title="Commands",
            border_style="cyan",
            box=box.ROUNDED,
        ))
        return True

    def _cmd_session(self, line: str) -> bool:
        rest = line[len("/session"):].strip()
        sessions = self.runtime.list_sessions()

        # /session new — create a fresh session
        if rest == "new":
            import uuid
            self.session_id = uuid.uuid4().hex[:6]
            console.print(f"[bold green]✓[/bold green] New session → [cyan]{self.session_id}[/cyan]")
            return True

        # /session (with no args) — list available sessions
        if not rest:
            if not sessions:
                console.print(f"[dim]Current session:[/dim] [cyan]{self.session_id}[/cyan] (no other sessions)")
                console.print("[dim]Use /session new to create one, or just start chatting.[/dim]")
                return True

            table = Table(title="Sessions", box=box.ROUNDED)
            table.add_column("#", style="dim", width=4)
            table.add_column("ID", style="cyan")
            table.add_column("Status")
            for i, sid in enumerate(sessions, 1):
                is_current = "← [green]active[/green]" if sid == self.session_id else ""
                msg_count = len(self.runtime.memory.get_messages(sid))
                table.add_row(str(i), sid, f"{msg_count} msgs {is_current}")
            console.print(table)
            console.print("[dim]Switch with /session <#> or /session <id> | /session new[/dim]")
            return True

        # /session <number> — switch by list number
        if rest.isdigit():
            idx = int(rest) - 1
            if 0 <= idx < len(sessions):
                self.session_id = sessions[idx]
                console.print(f"[bold green]✓[/bold green] Session → [cyan]{self.session_id}[/cyan]")
            else:
                console.print(f"[yellow]Invalid session number: {rest}[/yellow]")
            return True

        # /session <id> — switch by ID
        self.session_id = rest
        console.print(f"[bold green]✓[/bold green] Session → [cyan]{self.session_id}[/cyan]")
        return True

    def _cmd_skill_dispatch(self, line: str) -> bool:
        rest = line[len("/skill"):].strip()
        if rest == "list":
            skills = self.runtime.list_skills()
            if not skills:
                console.print("[dim]No skills found. Use /skill generate <name> <goal> to create one.[/dim]")
            else:
                table = Table(title="Skills", box=box.ROUNDED)
                table.add_column("Name", style="bold green")
                table.add_column("Description", max_width=60)
                table.add_column("Tools")
                for s in skills:
                    table.add_row(s.name, s.description[:80], ", ".join(s.allowed_tools) if s.allowed_tools else "—")
                console.print(table)
            return True
        if rest == "clear":
            self.runtime.clear_active_skill(session_id=self.session_id)
            console.print("[dim]Active skill → <none>[/dim]")
            return True
        if rest == "active":
            skill = self.runtime.get_active_skill(session_id=self.session_id)
            if skill:
                console.print(f"[bold green]Active:[/bold green] {skill.name} — {skill.description}")
            else:
                console.print("[dim]No active skill.[/dim]")
            return True
        if rest.startswith("use "):
            self.runtime.activate_skill(session_id=self.session_id, name=rest[4:].strip())
            console.print(f"[bold green]✓[/bold green] Active skill → [bold]{rest[4:].strip()}[/bold]")
            return True
        if rest.startswith("generate "):
            args = rest[len("generate "):].strip().split(" ", 1)
            if len(args) < 2:
                console.print("[yellow]Usage: /skill generate <name> <goal>[/yellow]")
                return True
            with console.status("[dim]Generating skill...[/dim]", spinner="dots"):
                skill = self.runtime.generate_skill(name=args[0], objective=args[1])
            console.print(Panel(
                f"[bold]Name:[/bold] {skill.name}\n"
                f"[bold]Description:[/bold] {skill.description}\n"
                f"[bold]Tools:[/bold] {', '.join(skill.allowed_tools) if skill.allowed_tools else '—'}\n"
                f"[bold]Instructions:[/bold]\n{skill.instructions[:500]}",
                title=f"[bold green]Skill: {skill.name}[/bold green]",
                border_style="green", box=box.ROUNDED,
            ))
            return True
        console.print("[bold]Skill commands:[/bold]\n  /skill list | /skill generate <name> <goal>\n  /skill use <name> | /skill clear | /skill active\n  /skill import <path> --format <fmt>")
        return True

    def _cmd_skills_menu(self, _line: str) -> bool:
        return self._cmd_skill_dispatch("/skill list")

    def _cmd_tools_menu(self, line: str) -> bool:
        rest = line[len("/tools"):].strip()
        if rest == "list":
            specs = self.runtime.tools.list_specs()
            console.print(render_tool_table(specs))
            return True
        if rest.startswith("show "):
            spec = self.runtime.tools.describe(rest[5:].strip())
            console.print(render_tool_detail(spec))
            return True
        if rest == "show":
            console.print("[yellow]Usage: /tools show <name>[/yellow]")
            return True
        console.print("[bold]Tool commands:[/bold]\n  /tools list | /tools show <name>\n  /tool <name> <payload> | /search <query>")
        return True

    def _cmd_tool_call(self, line: str) -> bool:
        rest = line[len("/tool"):].strip()
        parts = rest.split(" ", 1)
        if len(parts) < 1 or not parts[0]:
            console.print("[yellow]Usage: /tool <name> <payload>[/yellow]")
            return True
        tname, tpayload = parts[0], parts[1] if len(parts) > 1 else ""

        # Safety check for direct tool calls
        try:
            spec = self.runtime.tools.describe(tname)
            risk = getattr(spec, 'risk_level', 'read')
            if risk != "read" and not self.auto_approve:
                if not self._prompt_tool_approval(tname, tpayload, risk):
                    console.print("[dim]Cancelled.[/dim]")
                    return True
        except ValueError:
            pass

        try:
            output = self.runtime.tools.call(tname, tpayload)
        except Exception as e:
            console.print(Panel(f"[red]{e}[/red]", border_style="red"))
            return True
        console.print(Panel(output, title=f"[bold]Tool: {tname}[/bold]", border_style="cyan", box=box.ROUNDED))
        return True

    def _cmd_search(self, line: str) -> bool:
        query = line[len("/search"):].strip().lower()
        specs = self.runtime.tools.list_specs()
        matches = [s for s in specs if query in s.name.lower() or query in s.description.lower()
                    or query in s.category.lower() or query in s.domain.lower()]
        if not matches:
            console.print(f"[dim]No tools matching '[bold]{query}[/bold]'[/dim]")
        else:
            console.print(render_tool_table(matches, highlight=query))
        return True

    def _cmd_theme(self, line: str) -> bool:
        choice = line[len("/theme"):].strip().lower()
        # Support numeric selection e.g. /theme 3
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(AVAILABLE_THEMES):
                choice = AVAILABLE_THEMES[idx]
            else:
                console.print(f"[yellow]Invalid theme number: {choice} (1-{len(AVAILABLE_THEMES)})[/yellow]")
                return True
        if choice in AVAILABLE_THEMES:
            console.print(f"[bold green]✓[/bold green] Theme → [bold]{choice}[/bold]")
            return True
        # Interactive picker
        theme_options = {t: t for t in AVAILABLE_THEMES}
        picked = self._pick_option("Available Themes", theme_options)
        if picked:
            console.print(f"[bold green]✓[/bold green] Theme → [bold]{picked}[/bold]")
        return True

    def _cmd_commands(self, line: str) -> bool:
        filter_text = line[len("/commands"):].strip().lower()
        console.print("[bold]Available Commands[/bold]")
        found = False
        for cmd, desc in COMMAND_SPECS.items():
            if not filter_text or filter_text in cmd.lower() or filter_text in desc.lower():
                console.print(f"  [cyan]{cmd:<14}[/cyan] {desc}")
                found = True
        if filter_text:
            if found:
                console.print(f"\n[dim]Filtered by: {filter_text}[/dim]")
            else:
                console.print(f"\n[dim]No commands matching '{filter_text}'[/dim]")
        return True

    def _cmd_categories(self, _line: str) -> bool:
        from ..types import APPLICATION_DOMAINS, FUNCTIONAL_CATEGORIES
        console.print("[bold]Categories:[/bold] " + " ".join(
            f"[{CATEGORY_COLORS.get(c,'white')}]{c}[/{CATEGORY_COLORS.get(c,'white')}]"
            for c in FUNCTIONAL_CATEGORIES
        ))
        console.print("[bold]Domains:[/bold] " + ", ".join(APPLICATION_DOMAINS))
        return True

    def _cmd_activate_skill(self, line: str) -> bool:
        name = line[len("/activate"):].strip()
        if not name:
            console.print("[yellow]Usage: /activate <skill-name>[/yellow]")
            return True
        self.runtime.activate_skill(session_id=self.session_id, name=name)
        console.print(f"[bold green]✓[/bold green] Active skill → [bold]{name}[/bold]")
        return True

    def _cmd_mode(self, line: str) -> bool:
        mode_name = line[len("/mode"):].strip().lower()

        if mode_name == "acceptedits":
            mode_name = "acceptEdits"

        # Direct switch: /mode plan
        if mode_name and mode_name != "help":
            if mode_name not in PERMISSION_MODES:
                console.print(f"[yellow]Unknown mode '{mode_name}'.[/yellow]")
                return True
            self._switch_mode(mode_name)
            return True

        # Interactive picker with arrow-key navigation
        choice = self._pick_option("Permission Mode", PERMISSION_MODES)
        if choice:
            self._switch_mode(choice)
        return True

    def _switch_mode(self, mode_name: str) -> None:
        """Switch permission mode and update auto_approve."""
        if mode_name not in PERMISSION_MODES:
            return
        old_mode = self._permission_mode
        self._permission_mode = mode_name
        self.auto_approve = mode_name in ("auto", "bypass")
        desc = PERMISSION_MODES.get(mode_name, "")
        console.print(
            f"[bold green]✓[/bold green] Mode [bold]{old_mode}[/bold] → [bold]{self._permission_mode}[/bold]\n"
            f"[dim]{desc}[/dim]"
        )

    # ── Safety: tool approval prompts ──────────────────────────────────

    def _prompt_tool_approval(self, tool_name: str, tool_input: str, risk: str) -> bool:
        risk_badge = _format_risk_badge(risk)
        risk_style = RISK_STYLES.get(risk, "white")

        # Build a richer context description
        context_lines: list[str] = []
        context_lines.append(f"[bold]Tool:[/bold] {tool_name}")
        context_lines.append(f"[bold]Risk:[/bold] {risk_badge}")

        if tool_name == "file.read":
            path = tool_input.split("\n")[0].strip() if tool_input else ""
            context_lines.append(f"[bold]File:[/bold] [dim]{path}[/dim]")
        elif tool_name == "file.write":
            parts = tool_input.split("\n", 1)
            path = parts[0].strip() if parts else ""
            content = parts[1] if len(parts) > 1 else ""
            context_lines.append(f"[bold]File:[/bold] [dim]{path}[/dim]")
            context_lines.append(f"[bold]Content:[/bold] [dim]{content[:100]}{'...' if len(content) > 100 else ''}[/dim]")
        elif tool_name == "bash.run":
            cmd = tool_input.split("\n")[0].strip() if tool_input else tool_input
            context_lines.append(f"[bold]Command:[/bold] [dim]{cmd[:120]}[/dim]")
        else:
            context_lines.append(f"[bold]Input:[/bold] [dim]{tool_input[:200]}[/dim]")

        border = risk_style if risk != "read" else "yellow"
        console.print(Panel(
            "\n".join(context_lines),
            title="⚠️  Approval Required",
            border_style=border,
        ))
        choices = ["y", "n", "a"]
        labels = "y=yes / n=no / a=always for session"
        try:
            from rich.prompt import Prompt
            answer = Prompt.ask(f"Execute? [{labels}]", default="n",
                                choices=choices, show_choices=False).strip().lower()
        except (EOFError, KeyboardInterrupt):
            return False
        if answer == "a":
            self._approved_tools.add(tool_name)
            return True
        return answer == "y"

    def _check_tool_permission(self, tool_name: str, tool_input: str) -> bool:
        """Returns True if the tool call is permitted."""
        if self.auto_approve:
            return True
        if tool_name in self._approved_tools:
            return True
        try:
            spec = self.runtime.tools.describe(tool_name)
            risk = getattr(spec, 'risk_level', 'read')
        except ValueError:
            risk = "read"
        if risk == "read":
            return True
        return self._prompt_tool_approval(tool_name, tool_input, risk)

    # ── REPL commands ──────────────────────────────────────────────────

    def _cmd_model(self, line: str) -> bool:
        """Interactive model selection."""
        provider = getattr(self.runtime, 'provider', 'unknown')
        model = getattr(self.runtime, 'model', 'unknown')
        console.print(f"[bold]Current:[/bold] {provider} / {model}")
        console.print("To change, run [bold]kageko config init[/bold] or set [cyan]KAGEKO_PROVIDER[/cyan] / [cyan]KAGEKO_MODEL[/cyan]")
        return True

    def _cmd_display(self, line: str) -> bool:
        modes = {"full": "All panels visible", "compact": "Chat + HUD",
                 "zen": "Chat only", "review": "Chat + HUD", "minimal": "Bare chat"}
        console.print("[bold]Display Modes:[/bold]")
        for name, desc in modes.items():
            console.print(f"  [cyan]{name:<10}[/cyan] {desc}")
        return True

    def _cmd_history(self, line: str) -> bool:
        sessions = self.runtime.memory.list_sessions() if hasattr(self.runtime, 'memory') else []
        if not sessions:
            console.print("[dim]No session history.[/dim]")
            return True
        console.print("[bold]Recent Sessions:[/bold]")
        for sid in sessions[-10:]:
            console.print(f"  [cyan]{sid}[/cyan]")
        return True

    def _cmd_init_project(self, _line: str) -> bool:
        from pathlib import Path
        kg_dir = Path.cwd() / ".kageko"
        if kg_dir.exists():
            console.print("[dim].kageko/ already exists.[/dim]")
        else:
            kg_dir.mkdir()
            console.print("[bold green]✓[/bold green] Created .kageko/")
        return True

    def _cmd_clear_screen(self, _line: str) -> bool:
        import os
        os.system('cls' if os.name == 'nt' else 'clear')
        return True

    def _cmd_plan(self, _line: str) -> bool:
        console.print("[bold]Plan Mode[/bold] — read-only, tools that write are skipped.")
        console.print("Use [cyan]/mode plan[/cyan] to enable.")
        return True

    def _cmd_status(self, _line: str) -> bool:
        import importlib.metadata
        try:
            ver = importlib.metadata.version("KagekoO_O")
        except Exception:
            ver = "0.1.0"
        provider = getattr(self.runtime, 'provider', 'N/A')
        model = getattr(self.runtime, 'model', 'N/A')
        tools_count = len(self.runtime.tools.list_specs()) if self.runtime else 0
        skills_count = len(self.runtime.list_skills()) if self.runtime else 0
        console.print(f"[bold]Kageko v{ver}[/bold]")
        console.print(f"Provider: {provider}  |  Model: {model}")
        console.print(f"Tools: {tools_count}  |  Skills installed: {skills_count}")
        console.print(f"Session: [cyan]{self.session_id}[/cyan]  |  Mode: [cyan]{self._permission_mode}[/cyan]")
        return True

    def _cmd_doctor(self, _line: str) -> bool:
        provider = getattr(self.runtime, 'provider', 'N/A')
        has_key = bool(getattr(self.runtime, '_api_key', ''))
        console.print(f"[bold]Provider:[/bold] {provider}")
        console.print(f"[bold]API Key:[/bold] {'[green]Configured[/green]' if has_key else '[red]Missing[/red]'}")
        console.print(f"[bold]Model:[/bold] {getattr(self.runtime, 'model', 'N/A')}")
        console.print(f"[bold]Workspace:[/bold] {self.workspace}")
        return True

    def _cmd_logs(self, _line: str) -> bool:
        from pathlib import Path
        log_path = Path.home() / ".kageko" / "kageko.log"
        if log_path.exists():
            lines = log_path.read_text(encoding="utf-8").splitlines()[-20:]
            console.print("\n".join(f"[dim]{l}[/dim]" for l in lines))
        else:
            console.print("[dim]No logs found.[/dim]")
        return True

    # ── Agent interaction ──────────────────────────────────────────────

    def _handle_agent_query(self, line: str) -> bool:
        from ..streaming import ConsoleStreamRenderer
        from ..types import AgentMode

        # Auto-activate best matching skill (keyword-based, fast)
        matches = self.runtime.find_matching_skills(line)
        if matches:
            current = self.runtime.get_active_skill(session_id=self.session_id)
            if current is None or matches[0].name != current.name:
                self.runtime.activate_skill(session_id=self.session_id, name=matches[0].name)
                console.print(f"[dim]Activated skill:[/dim] [green]{matches[0].name}[/green] — {matches[0].description[:80]}")

        # Permission callback using multi-layer pipeline
        from ..permissions import PermissionHandler, PermissionMode, _check_dangerous
        perm = PermissionHandler(mode=PermissionMode(self._permission_mode)
            if self._permission_mode in PermissionMode.__members__
            else PermissionMode.DEFAULT)

        def _on_tool(tool_name: str, tool_input: str, risk: str) -> bool:
            err = perm.validate_input(tool_name, tool_input)
            if err:
                return False
            if risk == "read" or self._permission_mode == "bypass":
                return True
            danger = _check_dangerous(tool_name, tool_input)
            if danger and "Warning:" not in danger:
                console.print(f"[red]Blocked: {danger}[/red]")
                return False
            if self._permission_mode == "plan":
                console.print("[dim]Plan mode: read-only, skipping write[/dim]")
                return False
            if self._permission_mode == "auto":
                return True
            if tool_name in self._approved_tools:
                return True
            allowed = self._prompt_tool_approval(tool_name, tool_input, risk)
            if allowed:
                self._approved_tools.add(tool_name)
            return allowed

        # Stream response with live rendering
        active_skill = self.runtime.get_active_skill(session_id=self.session_id)
        if active_skill:
            console.print(f"[dim]using skill:[/dim] [green]{active_skill.name}[/green]")

        renderer = ConsoleStreamRenderer()
        try:
            for event in self.runtime.run_stream(
                AgentMode.QAOA, line, session_id=self.session_id,
                permission_callback=_on_tool,
            ):
                renderer.on_event(event)
            renderer.on_done()
        except Exception as e:
            renderer.on_done()
            console.print(Panel(f"[red]{e}[/red]", border_style="red"))
            return True
        return True


# ── REPL input helper ───────────────────────────────────────────────────

def repl_input(prompt_session: PromptSession | None = None,
               message: list[tuple[str, str]] | None = None) -> str | None:
    """Read a line from the user with tab completion support.

    Returns None on EOF/Ctrl+C, otherwise the trimmed string.
    """
    if prompt_session is None:
        history_path = Path.home() / ".kageko" / "history.txt"
        history_path.parent.mkdir(parents=True, exist_ok=True)
        history = FileHistory(str(history_path))
        prompt_session = PromptSession(completer=KagekoCompleter(), style=REPL_STYLE,
                                        complete_while_typing=True, reserve_space_for_menu=4,
                                        history=history)
    if message is None:
        message = [("class:prompt", "kageko"), ("class:separator", "> ")]
    try:
        text = prompt_session.prompt(message)
        return text.strip()
    except (EOFError, KeyboardInterrupt):
        return None
