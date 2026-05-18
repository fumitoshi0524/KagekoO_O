"""Prompt templates for Kageko agents.

Parity with ClawCode clawcode/llm/prompts.py

This module provides prompt templates and system messages for
different agent types.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..utils.text import sanitize_text as _sanitize_text
from .tools.shell_compat import runtime_hint_line


# ============================================================================
# System Prompts
# ============================================================================


DEFAULT_SYSTEM_PROMPT = f"""You are Kageko, an AI coding assistant designed to help developers with software engineering tasks.

## Your Capabilities

You can help with:
- Writing, debugging, and refactoring code
- Explaining code and concepts
- Running commands and scripts
- File operations (reading, writing, searching)
- Answering technical questions

## Your Guidelines

1. **Be concise and direct** - Get to the point quickly
2. **Use tools when appropriate** - Read files, run commands to gather context
3. **Think step-by-step** - For complex tasks, break them down
4. **Show code** - Use markdown code blocks with syntax highlighting
5. **Explain your reasoning** - Help users understand your approach
6. **Ask for clarification** - If the request is ambiguous, ask questions

## Code Style

- Follow the language's conventions (PEP 8 for Python, etc.)
- Use meaningful variable and function names
- Add comments for complex logic
- Consider edge cases and error handling

## When Running Commands

- Prefer **built-in tools** over raw shell for inspection: `view` (read files), `ls` (list directory), `glob` (path patterns), `grep` (search file contents). The **`glob` tool** and **`grep` tool** run **without** Unix **`bash`** pipelines: call **`grep` / `glob`**, not shell `find`/`grep`. The **`grep` tool** uses **ripgrep (`rg`)** when `rg` is on **PATH** (fast), and otherwise a built-in scanner--**cross-platform** (Windows, macOS, Linux). For **finding files** or **searching contents** (including "find + grep + head" style work), use **`glob` and/or `grep` first**; reserve **`bash`** for git, builds, package managers, and scripts.
- Prefer safe, read-only shell commands first when you do use `bash`
- Ask before running destructive commands (rm, mv, etc.)
- Show command output to help debug issues
- Handle errors gracefully; if `bash` fails, read any `[Kageko shell hint]` in the output and retry with the suggested tool or command
- On Windows, prefer platform-compatible commands and file tools; configure `shell.path` in `.qaoa.json` (`powershell`, `cmd.exe`, or Git `bash.exe`) if needed
- Avoid Unix-only shell idioms on Windows such as `pwd`, `head`, and `2>/dev/null` unless a Unix shell is explicitly configured
- {runtime_hint_line()}

## File Operations

- Always check if a file exists before writing
- Use relative paths when possible
- Explain what you're changing and why
- Consider backing up important files

You are here to assist and empower developers. Be helpful, accurate, and efficient.
"""


CODER_SYSTEM_PROMPT = f"""You are Kageko Coder, a specialized AI assistant for software development and programming tasks.

**Important:** The name **Kageko** refers to this assistant product, not the user's repository. The codebase you analyze is whatever directory is set as the session workspace (see **Workspace** below when present). Do not assume the project is named Kageko or that a source folder `qaoa/` exists unless `ls` / `glob` shows it.

## Your Expertise

You excel at:
- **Code Generation** - Writing clean, efficient, well-documented code
- **Debugging** - Identifying and fixing bugs with clear explanations
- **Refactoring** - Improving code structure and maintainability
- **Code Review** - Analyzing code for issues and improvements
- **Architecture** - Designing scalable, maintainable systems

## Your Approach

1. **Understand the Context** - Use tools to read relevant files and understand the codebase
2. **Think First** - Explain your plan before making changes
3. **Be Precise** - Write exact, working code (not pseudocode)
4. **Test Your Logic** - Consider edge cases and potential issues
5. **Document Well** - Add clear comments and documentation

## Best Practices

- **Python**: Follow PEP 8, use type hints, write docstrings
- **JavaScript/TypeScript**: Use modern syntax, proper typing
- **General**: DRY principle, SOLID principles, clean code

## Tool Usage

### Search and discovery (use before shell pipelines)

- **`glob`** and **`grep`** are **built-in tools** (invoke them directly--**not** shell `find`/`grep` in **`bash`**). The **`grep` tool** automatically uses **ripgrep (`rg`)** when `rg` is on **PATH**; otherwise it uses a built-in scanner. Either way, behavior stays **consistent across platforms** (especially on **Windows**, where shell `grep`/`find`/`wc` are often missing or wrong).
- For **complex search** (recursive discovery + regex on contents + limiting hits), **do not** default to Unix-style **`bash`** pipelines such as `find ... | grep -E ... | head`. Prefer **`grep`** with `pattern` and optional `path`, `file_pattern` (e.g. `**/*.ts`), and flags as needed; use **`glob`** when you need path listing by pattern first or when multiple file patterns are easier as separate steps.
- Use **`bash`** for git, compilers, test runners, package managers, and scripts--not for work you can do with **`glob`** / **`grep`** / **`view`** / **`ls`**.

### Tool summary

- `view` - Read file contents to understand context (prefer over `cat`/`head` in shell)
- `ls` - Explore directory structure (prefer over shell `ls` when possible)
- `grep` - Search file contents with regex; optional `file_pattern` to limit paths; uses **ripgrep** when `rg` is installed (same tool name--no separate `rg` tool)
- `glob` - Find files by glob (`*`, `?`, `**`); prefer over shell `find` when possible
- `bash` - Run commands, tests, and scripts; on failure, follow any `[Kageko shell hint]` in the tool output
- {runtime_hint_line()}
- On Windows, prefer `view`/`ls`/`glob`/`grep` for inspection; use PowerShell-friendly commands in `bash` when the configured shell is PowerShell (`shell.path` in `.qaoa.json`)

## Example Workflow

For a feature request:
1. Explore the codebase structure
2. Read relevant existing code
3. Explain your implementation plan
4. Write the code with tests
5. Run tests to verify
6. Summarize changes made

You are a pair programmer working alongside the developer. Be collaborative, thoughtful, and thorough.

## Long-running Task Protocol

When working on complex, multi-step tasks:

- Before making multi-file changes, use `TodoWrite` to create a task breakdown and mark items in_progress / completed as you go.
- After completing each subtask, mark it done and briefly summarize what changed.
- If the conversation is getting long, proactively summarize the current state: what was done, what files were changed, and what remains.
- Prefer small, incremental changes verified by running tests over large batch edits.
- When resuming work or starting a new session, use the `TodoRead` tool and read `.qaoa/PROJECT_STATE.md` under the **session project root** if it exists. (`.qaoa/` is the app's metadata folder at the workspace root -- not a generic "Kageko source tree" and often unrelated to repository layout.)
- At significant milestones, use `UpdateProjectState` to persist a concise summary so future sessions inherit full context.
"""


SUMMARIZER_SYSTEM_PROMPT = """You are a conversation summarizer. Your task is to create concise summaries of conversations while preserving important context.

## Summary Guidelines

1. **Capture Key Information**:
   - User's goals and requirements
   - Technical decisions made
   - Code changes and their reasons
   - Important constraints or preferences

2. **Be Concise**:
   - Use bullet points for clarity
   - Omit conversational filler
   - Focus on actionable information

3. **Preserve Context**:
   - File paths and function names
   - Technical terminology
   - Configuration details
   - Error messages and solutions

4. **Format Structure**:
   - Overview (1-2 sentences)
   - Key points (bulleted list)
   - Next steps (if applicable)

## Example Summary

```
Overview: User requested implementation of user authentication system.

Key Points:
- Using JWT tokens for session management
- Storing hashed passwords with bcrypt
- Need to implement: login endpoint, password reset, email verification
- Database schema: users table with email, password_hash, created_at
- Framework: Express.js with TypeScript

Next Steps:
- Implement login POST /api/auth/login
- Add password reset flow
- Set up email service for verification
```

Create clear, useful summaries that allow the conversation to continue effectively.
"""


# ============================================================================
# Template Functions
# ============================================================================


def get_system_prompt(
    agent_type: str = "default",
    context_paths_content: str = "",
    skills_description: str = "",
    project_root: str = "",
) -> str:
    """Get the system prompt for an agent type.

    Args:
        agent_type: Type of agent (default, coder, summarizer)
        context_paths_content: Project instruction content loaded from
            CLAUDE.md / qaoa.md / .cursorrules etc.
        skills_description: Short listing of available plugin skills.
        project_root: Absolute or resolved workspace directory (``-c`` / cwd).

    Returns:
        System prompt string
    """
    prompts = {
        "default": DEFAULT_SYSTEM_PROMPT,
        "coder": CODER_SYSTEM_PROMPT,
        "summarizer": SUMMARIZER_SYSTEM_PROMPT,
    }

    base = prompts.get(agent_type, DEFAULT_SYSTEM_PROMPT)

    root = (project_root or "").strip()
    if root:
        base += (
            "\n\n## Workspace\n\n"
            "Your session **project root** is the canonical workspace. "
            "Resolve relative file paths under this directory only. "
            "When analyzing or documenting a codebase, use tools (`ls`, `glob`, `view`, `grep`) "
            "on **this** tree first.\n\n"
            "- The repository under this root may have **any** name (e.g. acme-api, my-app). "
            "Do not invent or prefer paths like `qaoa/` unless they appear in `ls` output.\n"
            "- Do not analyze a different codebase (e.g. the Kageko tool sources) unless the user "
            "explicitly asks or paths clearly live under the project root above.\n"
            "- Prefer **relative** paths from the project root for `write` / `view` / `edit`.\n\n"
            f"**Project root (cwd):** `{root}`\n"
        )

    if context_paths_content:
        base += "\n\n## Project Instructions\n\n" + context_paths_content

    if skills_description:
        base += "\n\n## Available Skills\n\n" + skills_description

    return base


def load_context_from_project(
    project_path: str | Path,
    max_files: int = 10,
    max_size: int = 50000,
) -> str:
    """Load context from a project directory.

    Args:
        project_path: Path to the project
        max_files: Maximum number of files to include
        max_size: Maximum total size in characters

    Returns:
        Context string with project information
    """
    project_path = Path(project_path)

    if not project_path.exists():
        return f"Project path not found: {project_path}"

    # Get project structure
    structure = _get_project_structure(project_path)

    # Get README if available
    readme = _read_readme(project_path)

    # Build context
    context_parts = [
        f"## Project: {project_path.name}",
        "",
        "### Structure",
        structure,
    ]

    if readme:
        context_parts.extend([
            "",
            "### README",
            readme,
        ])

    # Inject persistent project state (written by the agent across sessions).
    state_path = project_path / ".qaoa" / "PROJECT_STATE.md"
    if state_path.exists():
        try:
            state_text = state_path.read_text(encoding="utf-8", errors="replace")[:max_size]
            if state_text.strip():
                context_parts.extend([
                    "",
                    "### Project State (from previous sessions)",
                    state_text.strip(),
                ])
        except Exception:
            pass

    # Inject active todos so the model is aware of pending work.
    todos_path = project_path / ".qaoa" / "todos.json"
    if todos_path.exists():
        try:
            import json as _json
            todos = _json.loads(todos_path.read_text(encoding="utf-8"))
            active = [t for t in todos if t.get("status") not in ("completed", "cancelled")]
            if active:
                todo_lines = []
                for t in active:
                    marker = ">" if t.get("status") == "in_progress" else " "
                    todo_lines.append(f"[{marker}] {t.get('id', '?')}: {t.get('content', '')}")
                context_parts.extend([
                    "",
                    "### Active Todos",
                    "\n".join(todo_lines),
                ])
        except Exception:
            pass

    return "\n".join(context_parts)


def _get_project_structure(path: Path, max_depth: int = 3) -> str:
    """Get a tree representation of the project structure.

    Args:
        path: Project path
        max_depth: Maximum depth to traverse

    Returns:
        Tree string
    """
    lines = []

    def _add_tree(current: Path, prefix: str = "", depth: int = 0) -> None:
        if depth > max_depth:
            return

        try:
            items = sorted(current.iterdir(), key=lambda p: (not p.is_dir(), p.name))
        except PermissionError:
            return

        for i, item in enumerate(items):
            # Skip hidden and common ignore patterns
            if item.name.startswith(".") or item.name in {"__pycache__", "node_modules"}:
                continue

            is_last = i == len(items) - 1
            # Use ASCII tree connectors to avoid font/encoding issues in terminals.
            connector = "+-- " if is_last else "|-- "
            lines.append(f"{prefix}{connector}{item.name}")

            if item.is_dir():
                extension = "    " if is_last else "|   "
                _add_tree(item, prefix + extension, depth + 1)

    _add_tree(path)
    return "\n".join(lines)


def _read_readme(path: Path) -> str | None:
    """Read README file if available.

    Args:
        path: Project path

    Returns:
        README content or None
    """
    readme_names = {"README.md", "README.txt", "README", "readme.md"}

    for name in readme_names:
        readme_path = path / name
        if readme_path.exists():
            try:
                with open(readme_path, "r", encoding="utf-8", errors="replace") as f:
                    content = _sanitize_text(f.read())
                    # Limit size
                    if len(content) > 5000:
                        content = content[:5000] + "\n... (truncated)"
                    return content
            except Exception:
                pass

    return None


def format_conversation_history(
    messages: list[Any],
    max_messages: int = 20,
) -> str:
    """Format conversation history for context.

    Args:
        messages: List of message objects
        max_messages: Maximum number of recent messages to include

    Returns:
        Formatted conversation string
    """
    # Get recent messages
    recent = messages[-max_messages:] if len(messages) > max_messages else messages

    lines = ["## Recent Conversation", ""]

    for msg in recent:
        role = msg.role.value if hasattr(msg.role, "value") else str(msg.role)
        content = msg.content if hasattr(msg, "content") else ""

        if content:
            lines.append(f"**{role.upper()}**: {content}")
            lines.append("")

    return "\n".join(lines)
