"""Search tools for finding files and content.

Parity with ClawCode -- same GlobTool, GrepTool, create_glob_tool, create_grep_tool,
with native/ripgrep/Python fallback chain.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .base import BaseTool, ToolInfo, ToolCall, ToolResponse, ToolContext
from .file_ops import resolve_tool_path
from ...utils.text import sanitize_text


def _format_native_grep_output(
    data: dict[str, Any],
    base: Path,
    context_lines: int,
) -> tuple[list[str], int, int]:
    """Format ``kageko_performance.grep_path`` result like ripgrep-style output."""
    raw_matches = data.get("matches") or []
    results: list[str] = []
    match_count = 0
    files_with_hits: set[str] = set()

    def full_path_for(rel: str) -> str:
        p = Path(rel)
        if p.is_absolute():
            return str(p)
        try:
            return str((base / rel).resolve())
        except OSError:
            return str(base / rel)

    for m in raw_matches:
        if not isinstance(m, dict):
            continue
        rel = str(m.get("path") or "")
        line_num = int(m.get("line_number") or 0)
        line_text = str(m.get("line") or "")
        path_text = full_path_for(rel)
        files_with_hits.add(path_text)
        match_count += 1

        if context_lines <= 0:
            results.append(f"{path_text}:{line_num}: {line_text}")
            continue

        before = m.get("context_before") or []
        after = m.get("context_after") or []
        events: list[tuple[str, int, str]] = []
        for cl in before:
            if isinstance(cl, dict):
                events.append(
                    (
                        "context",
                        int(cl.get("line_number") or 0),
                        str(cl.get("line") or ""),
                    )
                )
        events.append(("match", line_num, line_text))
        for cl in after:
            if isinstance(cl, dict):
                events.append(
                    (
                        "context",
                        int(cl.get("line_number") or 0),
                        str(cl.get("line") or ""),
                    )
                )
        events.sort(key=lambda x: x[1])

        results.append(f"{path_text}:{line_num}")
        block: list[str] = []
        for kind, sn, stext in events:
            prefix = ">>" if kind == "match" and sn == line_num else "  "
            block.append(f"{prefix} {sn}: {stext}")
        results.append("\n".join(block))

    return results, match_count, len(files_with_hits)


def _glob_via_native(pattern: str, base: Path) -> list[str] | None:
    """Fast glob via PyO3 extension; returns ``None`` if unavailable or on error."""
    try:
        from . import performance_bridge as pb

        if pb.get_performance_module() is None:
            return None
        return pb.glob_scan(
            pattern=pattern,
            path=str(base.resolve()),
            recursive=True,
            include_hidden=False,
            gitignore=True,
            max_results=10000,
        )
    except Exception:
        return None


def _resolve_ripgrep_path() -> str | None:
    """Return path to ``rg`` if it is on PATH, else ``None``."""
    return shutil.which("rg")


def _extension_globs_for_ripgrep(extensions: set[str]) -> list[str]:
    """Build ripgrep ``--glob`` patterns ``**/*<ext>`` for each extension."""
    globs: list[str] = []
    for ext in sorted(extensions):
        e = ext if ext.startswith(".") else f".{ext}"
        globs.append(f"**/*{e}")
    return globs


def _parse_rg_json_output(
    raw_stdout: str,
    base: Path,
    context_lines: int,
) -> tuple[list[str], int, int]:
    """Parse ``rg --json`` lines into formatted result strings.

    Returns:
        (result_lines, match_count, unique_files_with_match)
    """
    results: list[str] = []
    match_count = 0
    files_with_hits: set[str] = set()

    base_resolved = base.resolve()

    def normalize_path(path_text: str) -> str:
        p = Path(path_text)
        if p.is_absolute():
            return str(p)
        try:
            return str((base_resolved / p).resolve())
        except OSError:
            return str(base_resolved / p)

    lines = raw_stdout.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            i += 1
            continue

        if obj.get("type") != "begin":
            i += 1
            continue

        begin_path = (obj.get("data") or {}).get("path") or {}
        path_key = begin_path.get("text") or ""

        events: list[tuple[str, int, str]] = []
        i += 1
        while i < len(lines):
            inner = lines[i].strip()
            if not inner:
                i += 1
                continue
            try:
                rec = json.loads(inner)
            except json.JSONDecodeError:
                i += 1
                continue

            t = rec.get("type")
            if t == "end":
                i += 1
                break
            if t in ("context", "match"):
                data = rec.get("data") or {}
                ln = int(data.get("line_number") or 0)
                text = (data.get("lines") or {}).get("text") or ""
                text = text.rstrip("\n").rstrip("\r")
                events.append((t, ln, text))
            i += 1

        if context_lines <= 0:
            for kind, ln, text in events:
                if kind != "match":
                    continue
                match_count += 1
                path_text = normalize_path(path_key)
                files_with_hits.add(path_text)
                results.append(f"{path_text}:{ln}: {text}")
        else:
            ei = 0
            while ei < len(events):
                kind, ln, text = events[ei]
                if kind != "match":
                    ei += 1
                    continue
                start = ei
                ctx_before = 0
                while start > 0 and events[start - 1][0] == "context" and ctx_before < context_lines:
                    start -= 1
                    ctx_before += 1
                end = ei
                ctx_after = 0
                while (
                    end + 1 < len(events)
                    and events[end + 1][0] == "context"
                    and ctx_after < context_lines
                ):
                    end += 1
                    ctx_after += 1
                segment = events[start : end + 1]
                path_text = normalize_path(path_key)
                files_with_hits.add(path_text)
                match_count += 1
                results.append(f"{path_text}:{ln}")
                block: list[str] = []
                for sk, sn, stext in sorted(segment, key=lambda x: x[1]):
                    prefix = ">>" if sk == "match" and sn == ln else "  "
                    block.append(f"{prefix} {sn}: {stext}")
                results.append("\n".join(block))
                ei = end + 1

    return results, match_count, len(files_with_hits)


def create_glob_tool(permissions: Any = None) -> "GlobTool":
    """Create a glob tool instance.

    Args:
        permissions: Permission service

    Returns:
        GlobTool instance
    """
    return GlobTool(permissions=permissions)


def create_grep_tool(permissions: Any = None) -> "GrepTool":
    """Create a grep tool instance.

    Args:
        permissions: Permission service

    Returns:
        GrepTool instance
    """
    return GrepTool(permissions=permissions)


class GlobTool(BaseTool):
    """Tool for finding files by pattern."""

    IGNORE_PATTERNS = {
        "__pycache__",
        ".git",
        ".svn",
        "node_modules",
        ".venv",
        "venv",
        "*.pyc",
        ".DS_Store",
    }

    def __init__(self, permissions: Any = None) -> None:
        """Initialize the glob tool.

        Args:
            permissions: Permission service
        """
        self._permissions = permissions

    def info(self) -> ToolInfo:
        """Get tool information.

        Returns:
            ToolInfo describing this tool
        """
        return ToolInfo(
            name="glob",
            category="search",
            domain="technology",
            description="Find files matching a pattern. "
            "Supports wildcards (*, **, ?). Use ** for recursive matching.",
            parameters={
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern (e.g., '*.py', '**/*.txt', 'src/**/test_*.py').",
                    },
                    "path": {
                        "type": "string",
                        "description": "Base path for search (default: current directory).",
                    },
                },
                "required": ["pattern"],
            },
            required=["pattern"],
        )

    async def run(
        self,
        call: ToolCall,
        context: ToolContext,
    ) -> ToolResponse:
        """Find files by pattern.

        Args:
            call: Tool call with pattern
            context: Tool execution context

        Returns:
            Tool response with matching files
        """
        params = call.input if isinstance(call.input, dict) else {}
        pattern = params.get("pattern", "")
        base_path = params.get("path", ".")

        if not pattern:
            return ToolResponse(
                content="Error: No pattern provided",
                is_error=True,
            )

        base = resolve_tool_path(base_path, context.working_directory)

        # Check if path exists
        if not base.exists():
            return ToolResponse(
                content=f"Error: Path not found: {base_path}",
                is_error=True,
            )

        try:
            native_paths = _glob_via_native(pattern, base)
            if native_paths is not None:
                filtered_np: list[str] = []
                for p in native_paths:
                    parts = Path(p).parts
                    if not any(part in GlobTool.IGNORE_PATTERNS for part in parts):
                        filtered_np.append(p)
                filtered_np.sort()
                if not filtered_np:
                    return ToolResponse(
                        content=f"No matches found for pattern: {pattern}",
                        metadata="0 files",
                    )
                return ToolResponse(
                    content="\n".join(filtered_np),
                    metadata=f"{len(filtered_np)} files matching '{pattern}' (native)",
                )

            # Use glob to find matches
            matches = list(base.glob(pattern))

            # Filter out ignored patterns
            filtered = []
            for match in matches:
                # Check if any part of path is ignored
                parts = match.parts
                if not any(p in self.IGNORE_PATTERNS for p in parts):
                    filtered.append(str(match))

            if not filtered:
                return ToolResponse(
                    content=f"No matches found for pattern: {pattern}",
                    metadata="0 files",
                )

            return ToolResponse(
                content="\n".join(sorted(filtered)),
                metadata=f"{len(filtered)} files matching '{pattern}'",
            )

        except Exception as e:
            return ToolResponse(
                content=f"Error searching files: {e}",
                is_error=True,
            )


class GrepTool(BaseTool):
    """Tool for searching file contents."""

    DEFAULT_EXTENSIONS = {
        ".py",
        ".js",
        ".ts",
        ".tsx",
        ".jsx",
        ".java",
        ".c",
        ".cpp",
        ".h",
        ".hpp",
        ".cs",
        ".go",
        ".rs",
        ".rb",
        ".php",
        ".swift",
        ".kt",
        ".scala",
        ".sh",
        ".bash",
        ".zsh",
        ".fish",
        ".ps1",
        ".bat",
        ".cmd",
        ".md",
        ".txt",
        ".toml",
        ".yaml",
        ".yml",
        ".json",
        ".xml",
        ".html",
        ".css",
        ".scss",
        ".sass",
        ".less",
    }

    IGNORE_PATTERNS = {
        "__pycache__",
        ".git",
        ".svn",
        "node_modules",
        ".venv",
        "venv",
        "*.pyc",
        ".DS_Store",
        "package-lock.json",
        "yarn.lock",
        "poetry.lock",
    }

    def __init__(self, permissions: Any = None) -> None:
        """Initialize the grep tool.

        Args:
            permissions: Permission service
        """
        self._permissions = permissions
        self._rg_path_resolved = False
        self._cached_rg_path: str | None = None

    def _get_ripgrep_executable(self) -> str | None:
        if not self._rg_path_resolved:
            self._cached_rg_path = _resolve_ripgrep_path()
            self._rg_path_resolved = True
        return self._cached_rg_path

    def _grep_via_ripgrep(
        self,
        pattern: str,
        base: Path,
        file_pattern: str,
        case_insensitive: bool,
        context_lines: int,
    ) -> ToolResponse | None:
        """Run search via ripgrep. Returns ``None`` to fall back to Python implementation."""
        rg = self._get_ripgrep_executable()
        if not rg:
            return None

        cmd: list[str] = [
            rg,
            "--json",
            "-n",
            "--color",
            "never",
        ]
        if case_insensitive:
            cmd.append("-i")
        if context_lines > 0:
            cmd.extend(["-C", str(int(context_lines))])

        fp = (file_pattern or "").strip()
        if base.is_file():
            search_target = str(base.resolve())
        else:
            search_target = str(base.resolve())
            if fp:
                cmd.extend(["--glob", fp])
            else:
                for g in _extension_globs_for_ripgrep(self.DEFAULT_EXTENSIONS):
                    cmd.extend(["--glob", g])

        cmd.extend(["--", pattern, search_target])

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None

        if proc.returncode not in (0, 1):
            return None

        try:
            out_lines, n_matches, n_files = _parse_rg_json_output(
                proc.stdout,
                base,
                context_lines,
            )
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            return None

        if not out_lines:
            searched = "0"
            for sl in reversed(proc.stdout.splitlines()):
                sl = sl.strip()
                if not sl:
                    continue
                try:
                    j = json.loads(sl)
                    if j.get("type") == "summary":
                        st = (j.get("data") or {}).get("stats") or {}
                        searched = str(st.get("searches", 0))
                        break
                except json.JSONDecodeError:
                    continue
            return ToolResponse(
                content=f"No matches found for pattern: {pattern}",
                metadata=f"Searched {searched} paths (ripgrep)",
            )

        return ToolResponse(
            content=sanitize_text("\n".join(out_lines)),
            metadata=f"{n_matches} matches in {n_files} files (ripgrep)",
        )

    def _grep_via_native(
        self,
        pattern: str,
        base: Path,
        file_pattern: str,
        case_insensitive: bool,
        context_lines: int,
    ) -> ToolResponse | None:
        """Search via ``kageko_performance`` (Rust). Returns ``None`` to use other backends."""
        try:
            from . import performance_bridge as pb

            if pb.get_performance_module() is None:
                return None
            path_str = str(base.resolve())
            fp = (file_pattern or "").strip()
            if base.is_file():
                glob_opt: str | None = None
            else:
                glob_opt = fp if fp else None

            data = pb.grep_path(
                pattern=pattern,
                path=path_str,
                glob_pattern=glob_opt,
                ignore_case=case_insensitive,
                multiline=False,
                hidden=False,
                gitignore=True,
                max_count=None,
                context_before=int(context_lines),
                context_after=int(context_lines),
                max_columns=None,
            )
        except Exception:
            return None

        if not isinstance(data, dict):
            return None

        matches = data.get("matches") or []
        if not matches:
            searched = data.get("files_searched", 0)
            return ToolResponse(
                content=f"No matches found for pattern: {pattern}",
                metadata=f"Searched {searched} paths (native)",
            )

        try:
            out_lines, n_matches, n_files = _format_native_grep_output(
                data,
                base,
                context_lines,
            )
        except Exception:
            return None

        if not out_lines:
            return None

        return ToolResponse(
            content=sanitize_text("\n".join(out_lines)),
            metadata=f"{n_matches} matches in {n_files} files (native)",
        )

    def info(self) -> ToolInfo:
        """Get tool information.

        Returns:
            ToolInfo describing this tool
        """
        return ToolInfo(
            name="grep",
            category="search",
            domain="technology",
            description="Search for text/pattern in file contents. "
            "Supports regular expressions (Python ``re`` syntax for validation). "
            "If the optional ``kageko_performance`` Rust extension is installed, search "
            "uses that first; else when ``rg`` is on PATH, ripgrep is used; otherwise the "
            "built-in scanner runs. Regex dialect may differ between backends; failures "
            "fall back to the next option.",
            parameters={
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Regular expression pattern to search for.",
                    },
                    "path": {
                        "type": "string",
                        "description": "Base path for search (default: current directory).",
                    },
                    "file_pattern": {
                        "type": "string",
                        "description": "File pattern to limit search (e.g., '*.py', 'src/**').",
                    },
                    "case_insensitive": {
                        "type": "boolean",
                        "description": "Case-insensitive search (default: false).",
                    },
                    "context_lines": {
                        "type": "integer",
                        "description": "Number of context lines to show (default: 0).",
                    },
                },
                "required": ["pattern"],
            },
            required=["pattern"],
        )

    async def run(
        self,
        call: ToolCall,
        context: ToolContext,
    ) -> ToolResponse:
        """Search file contents.

        Args:
            call: Tool call with search parameters
            context: Tool execution context

        Returns:
            Tool response with search results
        """
        params = call.input if isinstance(call.input, dict) else {}
        pattern = params.get("pattern", "")
        base_path = params.get("path", ".")
        file_pattern = params.get("file_pattern", "")
        case_insensitive = params.get("case_insensitive", False)
        context_lines = params.get("context_lines", 0)

        if not pattern:
            return ToolResponse(
                content="Error: No pattern provided",
                is_error=True,
            )

        base = resolve_tool_path(base_path, context.working_directory)

        # Check if path exists
        if not base.exists():
            return ToolResponse(
                content=f"Error: Path not found: {base_path}",
                is_error=True,
            )

        try:
            # Compile regex
            flags = re.IGNORECASE if case_insensitive else 0
            try:
                regex = re.compile(pattern, flags)
            except re.error as e:
                return ToolResponse(
                    content=f"Error: Invalid regex pattern: {e}",
                    is_error=True,
                )

            native_rp = self._grep_via_native(
                pattern,
                base,
                file_pattern,
                case_insensitive,
                context_lines,
            )
            if native_rp is not None:
                return native_rp

            rp = self._grep_via_ripgrep(
                pattern,
                base,
                file_pattern,
                case_insensitive,
                context_lines,
            )
            if rp is not None:
                return rp

            # Find files to search
            files = self._find_files(base, file_pattern)

            # Search files
            results = []
            total_matches = 0

            for file_path in files:
                matches = self._search_file(
                    file_path,
                    regex,
                    context_lines,
                )

                if matches:
                    total_matches += len(matches)
                    results.extend(matches)

            if not results:
                return ToolResponse(
                    content=f"No matches found for pattern: {pattern}",
                    metadata=f"Searched {len(files)} files",
                )

            return ToolResponse(
                content=sanitize_text("\n".join(results)),
                metadata=f"{total_matches} matches in {len(files)} files",
            )

        except Exception as e:
            return ToolResponse(
                content=f"Error searching files: {e}",
                is_error=True,
            )

    def _find_files(self, base: Path, file_pattern: str) -> list[Path]:
        """Find files to search.

        Args:
            base: Base directory
            file_pattern: File pattern filter

        Returns:
            List of file paths
        """
        files = []

        if file_pattern:
            # Use glob pattern
            matches = list(base.glob(file_pattern))

            for match in matches:
                if match.is_file() and self._should_search_file(match):
                    files.append(match)
        else:
            # Walk directory
            for root, dirs, filenames in os.walk(base):
                # Filter ignored directories
                dirs[:] = [d for d in dirs if d not in self.IGNORE_PATTERNS]

                for filename in filenames:
                    file_path = Path(root) / filename

                    if self._should_search_file(file_path):
                        files.append(file_path)

        return files

    def _should_search_file(self, path: Path) -> bool:
        """Check if file should be searched.

        Args:
            path: File path

        Returns:
            True if file should be searched
        """
        # Check extension
        if path.suffix.lower() not in self.DEFAULT_EXTENSIONS:
            return False

        # Check if file is not binary
        if path.suffix.lower() in {".pyc", ".so", ".dll", ".exe"}:
            return False

        return True

    def _search_file(
        self,
        file_path: Path,
        regex: re.Pattern,
        context_lines: int,
    ) -> list[str]:
        """Search a single file.

        Args:
            file_path: File to search
            regex: Compiled regex pattern
            context_lines: Number of context lines

        Returns:
            List of formatted match strings
        """
        results = []

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            for i, line in enumerate(lines):
                if regex.search(line):
                    # Get context
                    start = max(0, i - context_lines)
                    end = min(len(lines), i + context_lines + 1)

                    # Format match
                    line_num = i + 1
                    rel_path = str(file_path)

                    if context_lines > 0:
                        # Show context
                        context = []
                        for j in range(start, end):
                            prefix = "  " if j != i else ">>"
                            context.append(f"{prefix} {j + 1}: {lines[j].rstrip()}")
                        results.append(f"{rel_path}:{line_num}")
                        results.append("\n".join(context))
                    else:
                        # Just show matching line
                        results.append(f"{rel_path}:{line_num}: {line.rstrip()}")

        except Exception:
            pass

        return results
