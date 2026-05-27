from __future__ import annotations

from dataclasses import dataclass, field


CORE_TOOLS = [
    "read_file",
    "write_file",
    "edit_file",
    "run_bash",
    "hashline_edit",
    "grep",
    "web_search",
    "list_files",
]


@dataclass
class ToolsetDef:
    tools: list[str] = field(default_factory=list)
    includes: list[str] = field(default_factory=list)
    description: str = ""


TOOLSETS: dict[str, ToolsetDef] = {
    "coding": ToolsetDef(
        tools=CORE_TOOLS,
        includes=["search"],
        description="Core coding tools",
    ),
    "search": ToolsetDef(
        tools=["grep", "ast_grep", "web_search"],
        description="Search and discovery tools",
    ),
    "gateway": ToolsetDef(
        tools=["send_message", "list_channels"],
        includes=["coding"],
        description="Gateway + coding tools",
    ),
    "safe": ToolsetDef(
        tools=["read_file", "grep", "web_search", "list_files"],
        description="Read-only tools, no mutations",
    ),
}


def resolve_toolset(name: str) -> list[str]:
    """Resolve a toolset name to a flat list of tool names, following includes."""
    if name not in TOOLSETS:
        return []
    ts = TOOLSETS[name]
    result = list(ts.tools)
    for inc in ts.includes:
        result.extend(resolve_toolset(inc))
    # Deduplicate while preserving order
    seen = set()
    deduped = []
    for t in result:
        if t not in seen:
            seen.add(t)
            deduped.append(t)
    return deduped
