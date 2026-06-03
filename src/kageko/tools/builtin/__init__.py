from kageko.tools.builtin.file_tools import file_read, file_write, file_list
from kageko.tools.builtin.shell_tools import bash_run
from kageko.tools.builtin.shell_tools import NATIVE_SHELL_TOOL, native_shell_handler
from kageko.tools.builtin.system_tools import echo, todo_add, todo_list
from kageko.tools.builtin.hashline_tool import hashline_edit, HASHLINE_TOOL
from kageko.tools.builtin.memory_tools import MEMORY_TOOLS, wire_memory_store
from kageko.tools.builtin.skill_tools import SKILL_TOOLS, wire_skill_store, wire_curator as _wire_curator
from kageko.tools.grep_tool import GREP_TOOL, grep_handler
from kageko.tools.ast_tool import AST_SUMMARIZE_TOOL, ast_summarize_handler

DELEGATE_TOOL = {
    "name": "delegate",
    "description": "Delegate a task to a subagent. Use for parallel work or isolated subtasks.",
    "parameters": {
        "type": "object",
        "properties": {
            "task": {"type": "string", "description": "The task to delegate to the subagent"},
            "allowed_tools": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional list of tool names the subagent can use",
            },
            "max_turns": {"type": "integer", "description": "Max turns for the subagent (default 10)", "default": 10},
        },
        "required": ["task"],
    },
    "category": "agent",
    "fn": None,  # Wired at runtime via make_delegate_handler
}


BUILTIN_TOOLS = [
    # ── File I/O (hashline_edit is the PRIMARY edit tool) ──────────────
    # ── File I/O ─────────────────────────────────────────────────────
    {"name": "file_read", "fn": file_read, "category": "file",
     "description": (
         "Read a file. Returns the full content (with hashline anchors for "
         "source files — `N#XXXXXXXX|line`). "
         "Use this instead of `cat`, `less`, or `bash python -c 'open(...).read()'`."
     ),
     "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "File path to read"}}, "required": ["path"]}},

    {"name": "file_write", "fn": file_write, "category": "file",
     "description": (
         "Write content to a file. Creates parent directories if needed. "
         "Use this instead of shell redirection (`>`, `>>`) or `tee`."
     ),
     "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},

    {"name": "file_list", "fn": file_list, "category": "file",
     "description": (
         "List files and directories at a given path. "
         "Use this instead of `ls`, `dir`, or `find <dir>`."
     ),
     "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "Directory path"}}, "required": ["path"]}},

    {"name": "hashline_edit", "fn": hashline_edit, "category": "code",
     "description": (
         "Edit a single line in an existing file by its anchor hash. "
         "First `file_read` the file to see anchors, then copy the 8-char hex "
         "anchor (the part between `#` and `|`) and pass it with the new content. "
         "Safer than `file_write` for partial edits — targets one line only. "
         "Use `file_write` when creating a brand-new file or replacing the entire content."
     ),
     "parameters": HASHLINE_TOOL["parameters"]},

    # ── Shell ─────────────────────────────────────────────────────────
    {"name": NATIVE_SHELL_TOOL["name"],
     "description": NATIVE_SHELL_TOOL["description"],
     "parameters": NATIVE_SHELL_TOOL["parameters"],
     "fn": native_shell_handler,
     "category": NATIVE_SHELL_TOOL["category"]},

    {"name": "bash", "fn": bash_run, "category": "shell",
     "description": (
         "Run a single shell command and return its output. "
         "Each invocation is independent — no cd or env var persists. "
         "Use ONLY for simple one-liners: `ls`, `wc -l`, `which python`, `echo $VAR`. "
         "For ANYTHING stateful (cd, source, export, multi-step) use `native_shell` instead. "
         "NEVER use bash to: cat/read files (→ file_read), list directories "
         "(→ file_list), find/grep code (→ grep), or run Python scripts "
         "(→ native_shell)."
     ),
     "parameters": {"type": "object", "properties": {"command": {"type": "string"}, "timeout": {"type": "integer", "default": 180}}, "required": ["command"]}},

    # ── Search & Analysis ──────────────────────────────────────────────
    {"name": GREP_TOOL["name"],
     "description": (
         "Search for a regex pattern across files. "
         "Faster than shell `grep` / `rg` and respects .gitignore. "
         "Use this instead of `grep`, `rg`, `find | xargs grep`, or "
         "`Select-String`."
     ),
     "parameters": GREP_TOOL["parameters"],
     "fn": grep_handler,
     "category": GREP_TOOL["category"]},

    {"name": AST_SUMMARIZE_TOOL["name"],
     "description": AST_SUMMARIZE_TOOL["description"],
     "parameters": AST_SUMMARIZE_TOOL["parameters"],
     "fn": ast_summarize_handler,
     "category": AST_SUMMARIZE_TOOL["category"]},

    # ── System ─────────────────────────────────────────────────────────
    {"name": "echo", "fn": echo, "category": "system",
     "description": "Echo back the given text",
     "parameters": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}},

    {"name": "todo_add", "fn": todo_add, "category": "system",
     "description": "Add a task to the todo list",
     "parameters": {"type": "object", "properties": {"task": {"type": "string"}, "priority": {"type": "string", "enum": ["low", "medium", "high"], "default": "medium"}}, "required": ["task"]}},

    {"name": "todo_list", "fn": todo_list, "category": "system",
     "description": "List all pending tasks",
     "parameters": {"type": "object", "properties": {}}},

    DELEGATE_TOOL,

    # ── Learning (Hermes-aligned: memory + skill management) ───────────
    *MEMORY_TOOLS,
    *SKILL_TOOLS,
]


def register_all(registry) -> None:
    """Register all builtin tools into the given ToolRegistry."""
    from kageko.tools.registry import Tool

    for spec in BUILTIN_TOOLS:
        if spec.get("fn") is None:
            continue
        if spec["name"] in registry.list_names():
            continue
        tool = Tool(
            name=spec["name"],
            description=spec.get("description", ""),
            parameters=spec.get("parameters", {}),
            handler=spec["fn"],
            category=spec.get("category", "general"),
        )
        registry.register(tool)


def wire_learning(memory_mgr) -> None:
    """Wire MemoryManager → MemoryStore + SkillStore + Curator to agent tools.

    Call once after creating MemoryManager, SkillStore, and Curator.
    """
    from kageko.learning.memory_store import MemoryStore
    from kageko.learning.skill_store import SkillStore

    if hasattr(memory_mgr, "store") and isinstance(memory_mgr.store, MemoryStore):
        wire_memory_store(memory_mgr.store)
    if hasattr(memory_mgr, "skill_store") and isinstance(memory_mgr.skill_store, SkillStore):
        wire_skill_store(memory_mgr.skill_store)
    if hasattr(memory_mgr, "curator"):
        _wire_curator(memory_mgr.curator)


__all__ = ["BUILTIN_TOOLS", "DELEGATE_TOOL", "register_all", "wire_learning"]
