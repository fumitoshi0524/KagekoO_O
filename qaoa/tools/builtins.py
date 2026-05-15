"""Register all built-in tools into a ToolRegistry."""

from __future__ import annotations

from pathlib import Path
import subprocess

from .registry import ToolRegistry
from ..skills.loader import SkillLoader
from ..skills.generator import SkillGenerator


def register_builtin_tools(registry: ToolRegistry, *, workspace: Path,
                           skills_dir: Path | None = None,
                           llm=None, skill_registry=None) -> SkillLoader:
    """Register all built-in tools. Returns the SkillLoader for skill tool access."""
    dirs: list[Path] = []
    if skills_dir is not None:
        dirs.append(skills_dir)
    dirs.append(workspace / "skills")
    loader = SkillLoader(dirs)

    # ── echo ────────────────────────────────────────────────────────
    registry.register(
        "echo",
        lambda p: p,
        description="Echo back the payload unchanged.",
        input_contract="any plain text",
        output_contract="same plain text",
        tags=("utility",), risk_level="read", category="system", domain="technology",
    )

    # ── file.read ───────────────────────────────────────────────────
    def _file_read(payload: str) -> str:
        path = payload.strip()
        # Try workspace-relative first, then absolute
        target = _safe_path(workspace, path, strict=False)
        if not target.exists():
            # Try as absolute path
            abs_path = Path(path)
            if abs_path.is_absolute() and abs_path.exists():
                return abs_path.read_text(encoding="utf-8")
            nearby = list(workspace.glob("*"))
            hint = ", ".join(f.name for f in nearby[:10]) if nearby else "empty directory"
            raise FileNotFoundError(
                f"File not found: '{path}' (workspace: {workspace}). "
                f"Files in workspace: {hint}"
            )
        return target.read_text(encoding="utf-8")

    registry.register(
        "file.read",
        _file_read,
        description="Read UTF-8 text file content from workspace-relative path.",
        input_contract="workspace-relative file path",
        output_contract="full file content as text",
        tags=("filesystem", "read"), risk_level="read", category="search", domain="technology",
    )

    # ── file.write ──────────────────────────────────────────────────
    registry.register(
        "file.write",
        lambda p: _file_write(workspace, p),
        description="Write UTF-8 text content to workspace-relative path.",
        input_contract="'<relative_path>\\n<content>'",
        output_contract="'wrote:<relative_path>' confirmation",
        tags=("filesystem", "write"), risk_level="write", category="operations", domain="technology",
    )

    # ── bash.run ────────────────────────────────────────────────────
    registry.register(
        "bash.run",
        lambda p: _bash_run(workspace, p),
        description="Execute a shell command inside workspace.",
        input_contract="shell command string",
        output_contract="stdout text or '<no-output>'",
        tags=("shell",), risk_level="destructive", category="operations", domain="technology",
    )

    # ── todo.write ──────────────────────────────────────────────────
    registry.register(
        "todo.write",
        lambda p: _todo_write(workspace, p),
        description="Append one TODO item to workspace TODO.md. Format: 'title|details'.",
        input_contract="'title|details' (details optional)",
        output_contract="'todo-added:<title>' confirmation",
        tags=("productivity",), risk_level="write", category="operations", domain="business",
    )

    # ── todo.done ───────────────────────────────────────────────────
    registry.register(
        "todo.done",
        lambda p: _todo_done(workspace, p),
        description="Mark a TODO item as completed in workspace TODO.md. Provide the title text to match.",
        input_contract="title text to mark as done",
        output_contract="'todo-done:<title>' or 'todo-not-found'",
        tags=("productivity",), risk_level="write", category="operations", domain="business",
    )

    # ── skill.load ──────────────────────────────────────────────────
    registry.register(
        "skill.load",
        lambda p: loader.load_one(p.strip()).instructions,
        description="Load raw skill instruction text.",
        input_contract="skill name identifier",
        output_contract="skill content text",
        tags=("skills",), risk_level="read", category="search", domain="technology",
    )

    # ── skill.describe ──────────────────────────────────────────────
    registry.register(
        "skill.describe",
        lambda p: _skill_describe(loader, p),
        description="Return normalized metadata for one skill as JSON.",
        input_contract="skill name identifier",
        output_contract="JSON object text",
        tags=("skills", "metadata"), risk_level="read", category="search", domain="technology",
    )

    # ── skill.list ──────────────────────────────────────────────────
    registry.register(
        "skill.list",
        lambda p: _skill_list(loader, p),
        description="List discoverable skills as JSON array.",
        input_contract="optional query filter",
        output_contract="JSON array text",
        tags=("skills", "metadata"), risk_level="read", category="search", domain="technology",
    )

    # ── skill.generate ──────────────────────────────────────────────
    def _generate_skill(payload: str) -> str:
        import json
        if llm is None:
            return json.dumps({"error": "LLM not available for skill generation"})
        gen = SkillGenerator(llm=llm, tools=registry, output_dir=workspace / "skills")
        try:
            skill = gen.generate(payload)
            if skill_registry:
                skill_registry.register(skill)
            gen.save_to_disk(skill)
            return json.dumps({
                "name": skill.name,
                "description": skill.description,
                "tools": skill.allowed_tools,
                "saved_to": str(workspace / "skills" / skill.name / "SKILL.md"),
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)})

    registry.register(
        "skill.generate",
        _generate_skill,
        description="Generate a new skill from a natural language description. "
                    "Creates the skill, saves it to skills/, and registers it. "
                    "Use when no existing skill matches the user's request.",
        input_contract="skill name and goal, e.g. 'python-cli-builder: Build Python CLI apps with typer+rich'",
        output_contract="JSON with generated skill metadata",
        tags=("skills", "generate"), risk_level="read", category="generate", domain="technology",
    )

    return loader


def _file_write(workspace: Path, payload: str) -> str:
    parts = payload.split("\n", 1)
    if len(parts) == 2:
        first_line = parts[0].strip()
        # Check if first line looks like a file path
        if "/" in first_line or "\\" in first_line or "." in first_line:
            path = _normalize_skill_path(first_line)
            target = _safe_path(workspace, path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(parts[1], encoding="utf-8")
            return f"wrote:{target.relative_to(workspace)}"

    # No valid path — auto-generate one from content
    content = payload.strip()
    fname, in_skills = _guess_filename(content)
    if in_skills:
        target = workspace / "skills" / fname
    else:
        target = workspace / fname
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content + "\n", encoding="utf-8")
    return f"wrote:{target.relative_to(workspace)}"


def _normalize_skill_path(path: str) -> str:
    """Normalize skill file paths to directory format.
    skills/name_SKILL.md -> skills/name/SKILL.md
    skills/name.md       -> skills/name/SKILL.md
    """
    import re
    if "/" in path or "\\" in path:
        sep = "/" if "/" in path else "\\"
        parts = path.rsplit(sep, 1)
        if len(parts) == 2:
            folder, fname = parts
            if folder == "skills" or folder.endswith("/skills") or folder.endswith("\\skills"):
                # Normalize skill file to directory format
                name = re.sub(r'_SKILL\.md$', '', fname)
                name = re.sub(r'\.md$', '', name)
                return f"{folder}{sep}{name}{sep}SKILL.md"
    return path


def _guess_filename(content: str) -> tuple[str, bool]:
    """Guess a filename from content. Returns (filename, is_skill).
    Skills are saved as <name>/SKILL.md (directory format)."""
    import re
    import hashlib
    # YAML frontmatter with category/domain/tools -> skill directory
    fm_match = re.match(r"---\s*\n(.*?)\n---", content, re.DOTALL)
    if fm_match:
        frontmatter = fm_match.group(1)
        name = None
        has_skill_fields = False
        for line in frontmatter.splitlines():
            if line.startswith("name:") or line.startswith("title:"):
                name = line.split(":", 1)[1].strip().strip('"').strip("'")
                name = re.sub(r"[^a-zA-Z0-9_-]", "_", name).strip("_")
            if any(line.startswith(k) for k in ("category:", "domain:", "tools:", "permissions:")):
                has_skill_fields = True
        if name and has_skill_fields:
            return f"{name}/SKILL.md", True
        if name:
            return f"{name}.md", False
    # Shebang
    if content.startswith("#!/"):
        return "script.py", False
    # Fallback
    h = hashlib.md5(content.encode()).hexdigest()[:8]
    return f"output_{h}.txt", False


def _find_shell() -> tuple[str, str]:
    """Find the best available shell using standard discovery — no hardcoded paths."""
    import os
    import shutil

    # 1. $SHELL env var
    env_shell = os.environ.get("SHELL", "")
    if env_shell and Path(env_shell).exists():
        return env_shell, f"$SHELL ({env_shell})"

    # 2. shutil.which — finds bash/sh on PATH (Git Bash, MSYS2, Cygwin, WSL)
    for name in ["bash", "zsh", "sh"]:
        found = shutil.which(name)
        if found:
            return found, f"{name} (PATH)"

    # 3. WSL
    if shutil.which("wsl"):
        return "wsl", "wsl"

    # 4. PowerShell on Windows
    if os.name == "nt" and shutil.which("powershell"):
        return "powershell", "powershell"

    # 5. Fallback
    return "cmd.exe", "cmd.exe (Windows — use dir/type/cd, not ls/cat/pwd)"


_SHELL_PATH, _SHELL_TYPE = _find_shell()


def _bash_run(workspace: Path, payload: str) -> str:
    command = payload.strip()
    if command == "":
        raise ValueError("bash.run payload cannot be empty.")
    if _SHELL_PATH == "wsl":
        command = f"wsl -- {command}"
    elif _SHELL_PATH == "powershell":
        command = f'powershell -Command "{command}"'
    elif _SHELL_PATH == "cmd.exe":
        pass
    else:
        command = f'"{_SHELL_PATH}" -c "{command}"'
    completed = subprocess.run(
        command, shell=True, check=False,
        capture_output=True, text=True, encoding="utf-8",
        errors="replace", cwd=str(workspace),
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"bash.run failed (exit={completed.returncode}). "
            f"Shell: {_SHELL_TYPE}. "
            f"stderr={completed.stderr.strip() or '<none>'}"
        )
    return completed.stdout.strip() or "<no-output>"


def _todo_write(workspace: Path, payload: str) -> str:
    parts = payload.split("|", 1)
    title = parts[0].strip()
    details = parts[1].strip() if len(parts) > 1 else ""
    if title == "":
        raise ValueError("todo.write requires title in payload 'title|details'.")
    todo_file = workspace / "TODO.md"
    existing = todo_file.read_text(encoding="utf-8") if todo_file.exists() else "# TODO\n\n"
    line = f"- [ ] {title}"
    if details:
        line = f"{line} -- {details}"
    todo_file.write_text(existing.rstrip() + f"\n{line}\n", encoding="utf-8")
    return f"todo-added:{title}"


def _todo_done(workspace: Path, payload: str) -> str:
    title = payload.strip()
    if title == "":
        raise ValueError("todo.done requires the title text to match.")
    todo_file = workspace / "TODO.md"
    if not todo_file.exists():
        return "todo-not-found"
    content = todo_file.read_text(encoding="utf-8")
    new_lines: list[str] = []
    found = False
    for line in content.splitlines():
        if f"- [ ] {title}" in line:
            new_lines.append(line.replace("- [ ]", "- [x]", 1))
            found = True
        else:
            new_lines.append(line)
    if found:
        todo_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        return f"todo-done:{title}"
    return "todo-not-found"


def _skill_describe(loader: SkillLoader, payload: str) -> str:
    import json
    spec = loader.load_one(payload.strip())
    return json.dumps({
        "name": spec.name, "description": spec.description,
        "format": spec.format,
        "path": str(spec.source_path) if spec.source_path else None,
        "allowed_tools": spec.allowed_tools, "permissions": spec.permissions,
    }, ensure_ascii=False)


def _skill_list(loader: SkillLoader, payload: str) -> str:
    import json
    query = payload.strip().lower()
    specs = loader.load_all()
    if query:
        specs = [s for s in specs if query in s.name.lower() or query in s.description.lower()]
    return json.dumps([
        {"name": s.name, "description": s.description, "format": s.format,
         "path": str(s.source_path) if s.source_path else None}
        for s in specs
    ], ensure_ascii=False)


def _safe_path(workspace: Path, relative_path: str, strict: bool = True) -> Path:
    raw = Path(relative_path)
    target = (workspace / raw).resolve()
    root = workspace.resolve()
    if root == target or root in target.parents:
        return target
    if not strict:
        # Allow absolute paths as fallback
        return target
    raise ValueError("Path must stay inside workspace.")
