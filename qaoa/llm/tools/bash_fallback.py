# QAOA category: operations, domain: technology
"""Narrow Python fallbacks when the bash subprocess fails (e.g. WSL store stub).

Parity with ClawCode -- same functions: try_python_shell_fallback, should_attempt_python_fallback.

Only a whitelist of simple command shapes is handled; arbitrary shell is not
interpreted. Paths are constrained via ``resolve_tool_path`` and workspace checks.
"""

from __future__ import annotations

import re
from pathlib import Path


from .file_ops import assert_resolved_path_in_workspace, resolve_tool_path


def _workspace_base(cwd: str | None, workspace: str) -> Path:
    for raw in (cwd, workspace):
        if raw and str(raw).strip():
            try:
                p = Path(raw).expanduser().resolve()
                if p.is_dir():
                    return p
            except OSError:
                pass
    try:
        return Path.cwd().resolve()
    except OSError:
        return Path.cwd()


def _under_workspace(resolved: Path, workspace: str) -> bool:
    wd = (workspace or "").strip()
    if not wd:
        return True
    return assert_resolved_path_in_workspace(resolved, wd) is None


def _resolve_cd_path(cd_part: str, base: Path, workspace: str) -> Path | None:
    raw = cd_part.strip().strip("\"'")
    if raw == "..":
        try:
            parent = base.resolve().parent
        except OSError:
            return None
        if not _under_workspace(parent, workspace):
            return None
        return parent if parent.is_dir() else None
    p = resolve_tool_path(raw, str(base))
    try:
        p = p.resolve()
    except OSError:
        return None
    if not p.is_dir():
        return None
    if not _under_workspace(p, workspace):
        return None
    return p


def _list_dir_names(target: Path, workspace: str) -> str | None:
    try:
        r = target.resolve()
    except OSError:
        return None
    if not r.is_dir() or not _under_workspace(r, workspace):
        return None
    try:
        names = sorted((p.name for p in r.iterdir()), key=str.lower)
    except OSError:
        return None
    return "\n".join(names)


def _match_powershell_head_select_string(s: str) -> tuple[str, str, str] | None:
    t = s.strip()
    low = t.lower()
    if not (low.startswith("powershell") or low.startswith("pwsh")):
        return None
    qm = re.match(r'(?is)^\s*(?:powershell|pwsh)\s+["\'](.+)["\']\s*$', t)
    if not qm:
        return None
    inner = qm.group(1)
    m = re.search(
        r"(?is)Get-Content\s+(\S+)\s+-Head\s+(\d+).*?Select-String\s+.*?-Pattern\s+([\"'])([^\"']*)\3",
        inner,
    )
    if not m:
        return None
    return m.group(1), m.group(2), m.group(4)


def _fallback_powershell_content(
    file_arg: str,
    head_n: int,
    pattern: str,
    base: Path,
    workspace: str,
) -> str | None:
    try:
        rp = resolve_tool_path(file_arg, str(base))
        if not rp.is_file():
            return None
        rp = rp.resolve()
        if not _under_workspace(rp, workspace):
            return None
    except OSError:
        return None
    try:
        cre = re.compile(pattern)
    except re.error:
        return None
    lines_out: list[str] = []
    n_read = 0
    try:
        with rp.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if n_read >= head_n:
                    break
                n_read += 1
                if cre.search(line):
                    lines_out.append(line.rstrip("\n\r"))
    except OSError:
        return None
    return "\n".join(lines_out)


def _match_cd_echo_pwd(s: str) -> tuple[str, str] | None:
    m = re.match(
        r'(?is)^\s*cd\s+(.+?)\s*&&\s*echo\s+"(.+?)"\s*&&\s*pwd\s*$',
        s.strip(),
    )
    if m:
        return m.group(1).strip(), m.group(2)
    m2 = re.match(
        r"(?is)^\s*cd\s+(.+?)\s*&&\s*echo\s+'(.+?)'\s*&&\s*pwd\s*$",
        s.strip(),
    )
    if m2:
        return m2.group(1).strip(), m2.group(2)
    return None


def _fallback_cd_echo_pwd(
    cd_part: str,
    echo_text: str,
    base: Path,
    workspace: str,
) -> str | None:
    target = _resolve_cd_path(cd_part, base, workspace)
    if target is None:
        return None
    try:
        pwd_line = str(target.resolve())
    except OSError:
        return None
    return f"{echo_text}\n{pwd_line}"


def _match_cd_pwd(s: str) -> str | None:
    m = re.match(r"(?is)^\s*cd\s+(.+?)\s*&&\s*pwd\s*$", s.strip())
    if m:
        return m.group(1).strip().strip("\"'")
    return None


def _fallback_cd_pwd(cd_part: str, base: Path, workspace: str) -> str | None:
    target = _resolve_cd_path(cd_part, base, workspace)
    if target is None:
        return None
    try:
        return str(target.resolve())
    except OSError:
        return None


def _fallback_pwd_only(base: Path, workspace: str) -> str | None:
    if not base.is_dir():
        return None
    try:
        r = base.resolve()
    except OSError:
        return None
    if not _under_workspace(r, workspace):
        return None
    return str(r)


def _match_cd_dir(s: str) -> str | None:
    m = re.match(r"(?is)^\s*cd\s+(.+?)\s*&&\s*dir\s*$", s.strip())
    if m:
        return m.group(1).strip().strip("\"'")
    return None


def _fallback_cd_dir(cd_part: str, base: Path, workspace: str) -> str | None:
    target = _resolve_cd_path(cd_part, base, workspace)
    if target is None:
        return None
    return _list_dir_names(target, workspace)


def try_python_shell_fallback(command: str, cwd: str | None, workspace: str) -> str | None:
    """Return stdout replacement if a whitelist pattern matches and run succeeds."""
    original = (command or "").strip()
    if not original:
        return None

    base = _workspace_base(cwd, workspace)
    ws = (workspace or "").strip()

    m = _match_powershell_head_select_string(original)
    if m:
        file_arg, n_str, pattern = m
        try:
            n = int(n_str)
        except ValueError:
            return None
        if n < 1 or n > 10_000:
            return None
        return _fallback_powershell_content(file_arg, n, pattern, base, ws)

    m2 = _match_cd_echo_pwd(original)
    if m2:
        return _fallback_cd_echo_pwd(m2[0], m2[1], base, ws)

    m3 = _match_cd_pwd(original)
    if m3:
        return _fallback_cd_pwd(m3, base, ws)

    if re.fullmatch(r"\s*pwd\s*", original, flags=re.IGNORECASE):
        return _fallback_pwd_only(base, ws)

    m5 = _match_cd_dir(original)
    if m5:
        return _fallback_cd_dir(m5, base, ws)

    if re.fullmatch(r"\s*(dir|ls)\s*", original, flags=re.IGNORECASE):
        return _list_dir_names(base, ws)

    return None


def should_attempt_python_fallback(
    returncode: int,
    stdout: str,
    stderr: str,
    *,
    bash_python_fallback: bool,
    without_env_hint: bool,
) -> bool:
    """Whether bash failure output warrants trying the Python whitelist."""
    if returncode == 0:
        return False
    if not bash_python_fallback:
        return False
    blob = f"{stdout}\n{stderr}".lower()
    if "wslstore" in blob or "aka.ms/wsl" in blob or "microsoft store" in blob:
        return True
    if "linux" in blob and "windows" in blob and "wsl" in blob:
        return True
    return bool(without_env_hint)
