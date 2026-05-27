from kageko.tools.builtin.file_tools import file_read, file_write, file_list
from kageko.tools.builtin.shell_tools import bash_run
from kageko.tools.builtin.shell_tools import NATIVE_SHELL_TOOL, native_shell_handler
from kageko.tools.builtin.system_tools import echo, todo_add, todo_list
from kageko.tools.builtin.hashline_tool import hashline_edit, HASHLINE_TOOL
from kageko.tools.builtin.hashline_tool import register as _reg_hashline
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
    "fn": None,  # Will be wired up at runtime via make_delegate_handler
}

BUILTIN_TOOLS = [
    {"name": "file_read", "fn": file_read, "category": "file",
     "description": "Read the contents of a file",
     "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "File path to read"}}, "required": ["path"]}},

    {"name": "file_write", "fn": file_write, "category": "file",
     "description": "Write content to a file (creates or overwrites)",
     "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},

    {"name": "file_list", "fn": file_list, "category": "file",
     "description": "List files in a directory",
     "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "Directory path"}}, "required": ["path"]}},

    {"name": "bash", "fn": bash_run, "category": "shell",
     "description": "Run a shell command",
     "parameters": {"type": "object", "properties": {"command": {"type": "string"}, "timeout": {"type": "integer", "default": 30}}, "required": ["command"]}},

    {"name": "echo", "fn": echo, "category": "system",
     "description": "Echo back the given text",
     "parameters": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}},

    {"name": "todo_add", "fn": todo_add, "category": "system",
     "description": "Add a task to the todo list",
     "parameters": {"type": "object", "properties": {"task": {"type": "string"}, "priority": {"type": "string", "enum": ["low", "medium", "high"], "default": "medium"}}, "required": ["task"]}},

    {"name": "todo_list", "fn": todo_list, "category": "system",
     "description": "List all pending tasks",
     "parameters": {"type": "object", "properties": {}}},

    {**HASHLINE_TOOL, "fn": hashline_edit},

    {"name": NATIVE_SHELL_TOOL["name"],
     "description": NATIVE_SHELL_TOOL["description"],
     "parameters": NATIVE_SHELL_TOOL["parameters"],
     "fn": native_shell_handler,
     "category": NATIVE_SHELL_TOOL["category"]},

    {"name": GREP_TOOL["name"],
     "description": GREP_TOOL["description"],
     "parameters": GREP_TOOL["parameters"],
     "fn": grep_handler,
     "category": GREP_TOOL["category"]},

    {"name": AST_SUMMARIZE_TOOL["name"],
     "description": AST_SUMMARIZE_TOOL["description"],
     "parameters": AST_SUMMARIZE_TOOL["parameters"],
     "fn": ast_summarize_handler,
     "category": AST_SUMMARIZE_TOOL["category"]},

    DELEGATE_TOOL,
]

def register_all(registry) -> None:
    """Register all builtin tools into the given ToolRegistry."""
    from kageko.tools.registry import Tool

    _reg_hashline(registry)

    for spec in BUILTIN_TOOLS:
        if spec.get("fn") is None:
            continue  # Skip tools without a handler (e.g. delegate, wired at runtime)
        if spec["name"] in registry.list_names():
            continue  # Skip tools already registered
        tool = Tool(
            name=spec["name"],
            description=spec.get("description", ""),
            parameters=spec.get("parameters", {}),
            handler=spec["fn"],
            category=spec.get("category", "general"),
        )
        registry.register(tool)


__all__ = ["BUILTIN_TOOLS", "DELEGATE_TOOL", "register_all"]
