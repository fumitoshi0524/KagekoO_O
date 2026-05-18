# QAOA category: system, domain: technology
"""Cross-platform shell helpers for the bash tool.

Parity with ClawCode -- same ShellFamily, ShellLaunchSpec, build_shell_launch_spec,
detect_runtime, classify_shell_executable, resolve_git_bash_executable, expand_command,
failure_hints, runtime_hint_line.

Normalizes common Unix-style invocations for Windows shells, builds argv for
subprocess (PowerShell/posix cannot use shell=True with /c), and produces
failure hints so the model can retry with compatible commands or built-in tools.
"""

from __future__ import annotations

import os
import platform
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from qaoa.llm.tools.environments.env_vars import _LEGACY_GIT_BASH_ENV_KEY


@dataclass(frozen=True)
class _ParsedSimpleGrep:
    """Single-file ``grep`` invocation (no pipes), for Windows rewriting."""

    pattern: str
    path: str
    fixed_strings: bool
    ignore_case: bool

OsKind = Literal["windows", "darwin", "linux", "other"]
ShellFamily = Literal["cmd", "powershell", "posix"]


def detect_runtime() -> OsKind:
    s = platform.system()
    if s == "Windows":
        return "windows"
    if s == "Darwin":
        return "darwin"
    if s == "Linux":
        return "linux"
    return "other"


def classify_shell_executable(shell_path: str) -> ShellFamily:
    """Infer shell family from configured executable name or path."""
    low = (shell_path or "").lower().replace("\\", "/")
    if "pwsh" in low or "powershell" in low:
        return "powershell"
    if low.endswith("cmd.exe") or low.rstrip("/").endswith("/cmd"):
        return "cmd"
    return "posix"


def resolve_shell_executable_path(shell_path: str) -> str:
    """Resolve shell to an absolute path when possible (PATH lookup)."""
    if not shell_path:
        return shell_path
    p = shell_path.strip()
    try:
        if Path(p).is_file():
            return str(Path(p).resolve())
    except OSError:
        pass
    w = shutil.which(Path(p).name if p else "")
    if w:
        return w
    w = shutil.which(p)
    return w or p


def _is_untrusted_windows_bash_path(path: str) -> bool:
    """True if ``path`` looks like the WSL / Store stub (WindowsApps), not Git Bash."""
    if not path:
        return True
    norm = path.replace("\\", "/").lower()
    # Microsoft Store placeholder prints WSL install hints; must not use as Git Bash.
    return "windowsapps" in norm


def resolve_git_bash_executable() -> str | None:
    """Locate Git Bash ``bash.exe`` on Windows for POSIX-style commands.

    Returns ``None`` if not found (caller should fall back to ``ShellConfig``).
    Never raises.

    PATH may expose ``bash.exe`` under ``Microsoft\\WindowsApps`` (WSL install stub);
    that executable is not Git Bash and is ignored. We therefore prefer well-known
    Git for Windows locations before ``shutil.which("bash")``, and reject
    WindowsApps matches from ``which``. Override explicitly with
    ``KAGEKO_GIT_BASH_PATH`` or the legacy compatibility env key (same as
    ``local.find_bash``).

    Lookup order:

    1. ``KAGEKO_GIT_BASH_PATH`` if the file exists
    2. Legacy compatibility env key if the file exists
    3. Common Git for Windows install paths under Program Files / LocalAppData
    4. ``shutil.which("bash")`` if the result exists on disk and is not WindowsApps
    """
    if detect_runtime() != "windows":
        return None

    for env_key in ("KAGEKO_GIT_BASH_PATH", _LEGACY_GIT_BASH_ENV_KEY):
        custom = os.environ.get(env_key, "").strip()
        if custom:
            try:
                p = Path(custom)
                if p.is_file():
                    return str(p.resolve())
            except OSError:
                continue

    for candidate in (
        os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "Git", "bin", "bash.exe"),
        os.path.join(
            os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
            "Git",
            "bin",
            "bash.exe",
        ),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Git", "bin", "bash.exe"),
    ):
        if not candidate:
            continue
        try:
            if Path(candidate).is_file():
                return str(Path(candidate).resolve())
        except OSError:
            continue

    found = shutil.which("bash")
    if found and not _is_untrusted_windows_bash_path(found):
        try:
            if Path(found).is_file():
                return str(Path(found).resolve())
        except OSError:
            return found

    return None


@dataclass(frozen=True)
class ShellLaunchSpec:
    """How to spawn the user command."""

    mode: Literal["shell", "exec"]
    shell_cmdline: str | None = None
    shell_executable: str | None = None
    argv: list[str] | None = None


def build_shell_launch_spec(
    command: str,
    shell_path: str,
    shell_args: list[str],
) -> ShellLaunchSpec:
    """Build subprocess parameters: cmd uses shell=True; PS/posix use exec + -Command/-c."""
    family = classify_shell_executable(shell_path)
    resolved = resolve_shell_executable_path(shell_path) or shell_path

    if family == "powershell":
        argv = [resolved, "-NoProfile", "-NonInteractive", *shell_args, "-Command", command]
        return ShellLaunchSpec(mode="exec", argv=argv)

    if family == "posix":
        argv = [resolved, *shell_args, "-c", command]
        return ShellLaunchSpec(mode="exec", argv=argv)

    return ShellLaunchSpec(
        mode="shell",
        shell_cmdline=command,
        shell_executable=resolved or None,
    )


def _ps_escape_single(path: str) -> str:
    return path.replace("'", "''")


def _powershell_command_for_cmd_exe(inner: str) -> str:
    """Wrap PowerShell ``-Command`` for ``cmd.exe``; double embedded ``\"`` per cmd quoting rules."""
    escaped = inner.replace('"', '""')
    return f'powershell -NoProfile -NonInteractive -Command "{escaped}"'


def _parse_simple_grep_for_windows(stripped: str) -> _ParsedSimpleGrep | None:
    """Parse ``grep [flags] pattern path`` when it is a single line with no pipes."""
    s = (stripped or "").strip()
    if not re.match(r"^grep\b", s, flags=re.IGNORECASE):
        return None
    rest = s[4:].lstrip()
    fixed = False
    ignore_case = False
    while rest.startswith("-"):
        tm = re.match(r"-([A-Za-z]{1,16})\s*", rest)
        if not tm:
            break
        for ch in tm.group(1).lower():
            if ch == "f":
                fixed = True
            elif ch == "i":
                ignore_case = True
            # n, E, h, etc. -- only F/i affect Select-String for our rewrite
        rest = rest[tm.end() :].lstrip()
    if not rest:
        return None
    pattern: str
    if rest[0] in "\"'":
        q = rest[0]
        i = 1
        buf: list[str] = []
        while i < len(rest):
            if rest[i] == "\\" and i + 1 < len(rest):
                buf.append(rest[i : i + 2])
                i += 2
                continue
            if rest[i] == q:
                pattern = "".join(buf)
                rest = rest[i + 1 :].lstrip()
                break
            buf.append(rest[i])
            i += 1
        else:
            return None
    else:
        um = re.match(r"(\S+)\s+", rest)
        if not um:
            return None
        pattern = um.group(1)
        rest = rest[um.end() :].lstrip()
    if not rest:
        return None
    path_raw = rest.strip()
    if not path_raw or any(c in path_raw for c in "*?[]&<>|^"):
        return None
    if path_raw[0] in "\"'":
        q = path_raw[0]
        i = 1
        buf2: list[str] = []
        while i < len(path_raw):
            if path_raw[i] == "\\" and i + 1 < len(path_raw):
                buf2.append(path_raw[i : i + 2])
                i += 2
                continue
            if path_raw[i] == q:
                file_path = "".join(buf2)
                if path_raw[i + 1 :].strip():
                    return None
                break
            buf2.append(path_raw[i])
            i += 1
        else:
            return None
    else:
        if not re.fullmatch(r"\S+", path_raw):
            return None
        file_path = path_raw
    return _ParsedSimpleGrep(
        pattern=pattern,
        path=file_path,
        fixed_strings=fixed,
        ignore_case=ignore_case,
    )


def _grep_pattern_for_select_string(pattern: str, *, fixed_strings: bool) -> str:
    """Map common GNU grep BRE escapes to a PowerShell ``-Pattern`` regex string."""
    if fixed_strings:
        return pattern
    # Basic grep alternation: \|  ->  |
    return pattern.replace("\\|", "|")


def _parse_find_name_globs(find_part: str) -> tuple[str, list[str]] | None:
    """Parse ``find START -name GLOB (-o -name GLOB)*``; return start and ``*.ext`` -> ``.ext`` list."""
    s = find_part.strip()
    m = re.match(r"^find\s+(\S+)\s+(.+)", s, flags=re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    start = m.group(1).strip().strip("\"'")
    rest = m.group(2).strip()
    globs: list[str] = []
    while True:
        nm = re.match(r"-name\s+(['\"])(.+?)\1\s*", rest, flags=re.IGNORECASE | re.DOTALL)
        if not nm:
            return None
        globs.append(nm.group(2))
        rest = rest[nm.end() :].strip()
        if not rest:
            break
        if rest.lower().startswith("-o"):
            rest = rest[2:].strip()
            continue
        return None
    if not globs:
        return None
    exts: list[str] = []
    for g in globs:
        em = re.fullmatch(r"\*\.([A-Za-z0-9]+)", g)
        if not em:
            return None
        exts.append("." + em.group(1).lower())
    return start, exts


def _rewrite_find_pipe_head_only(stripped: str, *, cmd_exe: bool) -> str | None:
    """``find ... -name '*.a' -o ... | head N`` -> list matching file paths (no ``grep``)."""
    s = stripped.strip()
    m = re.search(r"\|\s*head\s+(?:-n\s+)?-?\s*(\d+)\s*$", s, flags=re.IGNORECASE)
    if not m:
        return None
    find_part = s[: m.start()].strip()
    if not re.match(r"^find\b", find_part, flags=re.IGNORECASE):
        return None
    if re.search(r"\|\s*grep\b", find_part, flags=re.IGNORECASE):
        return None
    head_n = m.group(1)
    parsed = _parse_find_name_globs(find_part)
    if parsed is None:
        return None
    start, exts = parsed
    ps_start = _ps_escape_single(start)
    ext_ps = ",".join(f"'{e}'" for e in exts)
    inner = (
        f"Get-ChildItem -LiteralPath '{ps_start}' -Recurse -File | "
        f"Where-Object {{ @({ext_ps}) -contains $_.Extension.ToLower() }} | "
        f"ForEach-Object {{ $_.FullName }} | "
        f"Select-Object -First {head_n}"
    )
    if cmd_exe:
        return _powershell_command_for_cmd_exe(inner)
    return inner


def _rewrite_find_pipe_wc_line_count(stripped: str, *, cmd_exe: bool) -> str | None:
    """``find ... -name '*.a' -o ... | wc -l`` -> count files (like ``ls ... | wc -l``)."""
    s = stripped.strip()
    if not re.search(r"\|\s*wc\s+-l\s*$", s, flags=re.IGNORECASE):
        return None
    find_part = re.sub(r"\|\s*wc\s+-l\s*$", "", s, flags=re.IGNORECASE).strip()
    if not re.match(r"^find\b", find_part, flags=re.IGNORECASE):
        return None
    parsed = _parse_find_name_globs(find_part)
    if parsed is None:
        return None
    start, exts = parsed
    ps_start = _ps_escape_single(start)
    ext_ps = ",".join(f"'{e}'" for e in exts)
    inner = (
        f"(Get-ChildItem -LiteralPath '{ps_start}' -Recurse -File | "
        f"Where-Object {{ @({ext_ps}) -contains $_.Extension.ToLower() }} | "
        "Measure-Object | Select-Object -ExpandProperty Count)"
    )
    if cmd_exe:
        return _powershell_command_for_cmd_exe(inner)
    return inner


def _rewrite_ls_la_stderr_or_echo(stripped: str, *, cmd_exe: bool) -> str | None:
    """``ls -la DIR [2>/dev/null] || echo 'msg'`` -> PowerShell Test-Path branch."""
    s = stripped.strip()
    if "||" not in s or not re.match(r"^ls\s+-la?\s+", s, flags=re.IGNORECASE):
        return None
    m = re.match(
        r"^ls\s+-la?\s+(?P<path>.+?)\s+2>/dev/null\s*\|\|\s*echo\s+(?P<q>[\"'])(?P<msg>.*?)(?P=q)\s*$",
        s,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not m:
        m = re.match(
            r"^ls\s+-la?\s+(?P<path>.+?)\s*\|\|\s*echo\s+(?P<q>[\"'])(?P<msg>.*?)(?P=q)\s*$",
            s,
            flags=re.IGNORECASE | re.DOTALL,
        )
    if not m:
        return None
    path_arg = m.group("path").strip().strip("\"'")
    msg = m.group("msg").replace("'", "''")
    ps_path = _ps_escape_single(path_arg)
    inner = (
        f"if (Test-Path -LiteralPath '{ps_path}') "
        f"{{ Get-ChildItem -LiteralPath '{ps_path}' -Force | Format-Table -AutoSize }} "
        f"else {{ Write-Output '{msg}' }}"
    )
    if cmd_exe:
        return _powershell_command_for_cmd_exe(inner)
    return inner


def _rewrite_grep_context_file_pipe_head(stripped: str, *, cmd_exe: bool) -> str | None:
    """``grep -A n -B n PATTERN FILE | head N`` -> Select-String -Context + Select-Object -First."""
    s = stripped.strip()
    hm = re.search(r"\|\s*head\s+(?:-n\s+)?-?\s*(\d+)\s*$", s, flags=re.IGNORECASE)
    if not hm:
        return None
    head_n = hm.group(1)
    prefix = s[: hm.start()].strip()
    if not re.match(r"^grep\b", prefix, flags=re.IGNORECASE):
        return None
    rest = prefix[4:].lstrip()
    ctx_after = 0
    ctx_before = 0
    fixed_strings = False
    ignore_case = False
    while True:
        em = re.match(r"-E\s*", rest, flags=re.IGNORECASE)
        if em:
            rest = rest[em.end() :].lstrip()
            continue
        fm = re.match(r"-F\s*", rest, flags=re.IGNORECASE)
        if fm:
            fixed_strings = True
            rest = rest[fm.end() :].lstrip()
            continue
        im = re.match(r"-i\s*", rest, flags=re.IGNORECASE)
        if im:
            ignore_case = True
            rest = rest[im.end() :].lstrip()
            continue
        am = re.match(r"-A\s*(\d+)\s*", rest, flags=re.IGNORECASE)
        if am:
            ctx_after = int(am.group(1))
            rest = rest[am.end() :].lstrip()
            continue
        bm = re.match(r"-B\s*(\d+)\s*", rest, flags=re.IGNORECASE)
        if bm:
            ctx_before = int(bm.group(1))
            rest = rest[bm.end() :].lstrip()
            continue
        break
    if ctx_before == 0 and ctx_after == 0:
        return None
    if not rest or rest[0] not in "\"'":
        return None
    q = rest[0]
    i = 1
    pbuf: list[str] = []
    while i < len(rest):
        if rest[i] == "\\" and i + 1 < len(rest):
            pbuf.append(rest[i : i + 2])
            i += 2
            continue
        if rest[i] == q:
            pat = "".join(pbuf)
            rest = rest[i + 1 :].lstrip()
            break
        pbuf.append(rest[i])
        i += 1
    else:
        return None
    if not rest:
        return None
    file_raw = rest.strip()
    if file_raw[0] in "\"'":
        fq = file_raw[0]
        j = 1
        fbuf: list[str] = []
        while j < len(file_raw):
            if file_raw[j] == "\\" and j + 1 < len(file_raw):
                fbuf.append(file_raw[j : j + 2])
                j += 2
                continue
            if file_raw[j] == fq:
                file_path = "".join(fbuf)
                break
            fbuf.append(file_raw[j])
            j += 1
        else:
            return None
    else:
        if not re.fullmatch(r"\S+", file_raw):
            return None
        file_path = file_raw
    ps_file = _ps_escape_single(file_path)
    ps_pat = _ps_escape_single(pat)
    simple = " -SimpleMatch" if fixed_strings else ""
    ci = " -CaseSensitive:$false" if ignore_case else ""
    inner = (
        f"Select-String -LiteralPath '{ps_file}' -Pattern '{ps_pat}'{simple}{ci} "
        f"-Context {ctx_before},{ctx_after} | Select-Object -First {head_n}"
    )
    if cmd_exe:
        return _powershell_command_for_cmd_exe(inner)
    return inner


def _rewrite_find_pipe_grep_e_pipe_head(stripped: str, *, cmd_exe: bool) -> str | None:
    """``find ... -name '*.a' -o -name '*.b' | grep -E 're' | head N`` -> Get-ChildItem + Where-Object."""
    s = stripped.strip()
    parts = re.split(r"\s*\|\s*grep\s+-E\s+", s, maxsplit=1, flags=re.IGNORECASE)
    if len(parts) != 2:
        return None
    find_part, grest = parts[0].strip(), parts[1].strip()
    if not re.match(r"^find\b", find_part, flags=re.IGNORECASE):
        return None
    gm = re.match(
        r'^(["\'])(.+?)\1\s*\|\s*head\s+(?:-n\s+|-)(\d+)\s*$',
        grest,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not gm:
        return None
    regex_pat = gm.group(2)
    head_n = gm.group(3)
    parsed = _parse_find_name_globs(find_part)
    if parsed is None:
        return None
    start, exts = parsed
    ps_start = _ps_escape_single(start)
    rx_esc = _ps_escape_single(regex_pat)
    ext_ps = ",".join(f"'{e}'" for e in exts)
    inner = (
        f"Get-ChildItem -LiteralPath '{ps_start}' -Recurse -File | "
        f"Where-Object {{ @({ext_ps}) -contains $_.Extension.ToLower() }} | "
        f"ForEach-Object {{ $_.FullName }} | "
        f"Where-Object {{ $_ -match '{rx_esc}' }} | "
        f"Select-Object -First {head_n}"
    )
    if cmd_exe:
        return _powershell_command_for_cmd_exe(inner)
    return inner


def _replace_pipe_grep_e_with_where_object(command: str) -> str:
    """Turn ``| grep -E 'pattern' |`` into PowerShell ``| Where-Object { $_ -match '...' } |``."""

    def repl(m: re.Match[str]) -> str:
        pat = m.group(2)
        esc = pat.replace("'", "''")
        return f"| Where-Object {{ $_ -match '{esc}' }} "

    return re.sub(
        r"\|\s*grep\s+-E\s+(['\"])(.+?)\1\s*",
        repl,
        command,
        flags=re.IGNORECASE | re.DOTALL,
    )


def _rewrite_wc_l_single_file(stripped: str, *, cmd_exe: bool) -> str | None:
    """``wc -l FILE`` (no pipe) -> ``Get-Content`` + ``Measure-Object -Line``."""
    s = (stripped or "").strip()
    s = re.sub(r"\s+2>/dev/null\s*$", "", s, flags=re.IGNORECASE).strip()
    if "|" in s:
        return None
    m = re.fullmatch(r"wc\s+(?:-l|--lines)\s+(.+)", s, flags=re.IGNORECASE)
    if not m:
        return None
    path_raw = m.group(1).strip()
    if any(c in path_raw for c in "&|<>^"):
        return None
    if path_raw[0] in "\"'":
        q = path_raw[0]
        i = 1
        buf: list[str] = []
        while i < len(path_raw):
            if path_raw[i] == "\\" and i + 1 < len(path_raw):
                buf.append(path_raw[i : i + 2])
                i += 2
                continue
            if path_raw[i] == q:
                file_path = "".join(buf)
                if path_raw[i + 1 :].strip():
                    return None
                break
            buf.append(path_raw[i])
            i += 1
        else:
            return None
    else:
        if not re.fullmatch(r"\S+", path_raw):
            return None
        file_path = path_raw
    if not file_path:
        return None
    ps_path = _ps_escape_single(file_path)
    inner = f"(Get-Content -LiteralPath '{ps_path}' | Measure-Object -Line).Lines"
    if cmd_exe:
        return _powershell_command_for_cmd_exe(inner)
    return inner


def _rewrite_ls_pipe_wc_line_count(stripped: str, *, cmd_exe: bool) -> str | None:
    """``ls [dir] | wc -l`` -> PowerShell object count (same intent as Unix line count)."""
    m = re.fullmatch(
        r"ls(?:\s+(?P<path>\S+))?\s*\|\s*wc\s+-l\s*",
        stripped,
        flags=re.IGNORECASE,
    )
    if not m:
        return None
    path_arg = (m.group("path") or ".").strip().strip("\"'")
    if any(c in path_arg for c in "&|<>^"):
        return None
    ps_path = _ps_escape_single(path_arg)
    inner = (
        f"(Get-ChildItem -LiteralPath '{ps_path}' "
        "| Measure-Object | Select-Object -ExpandProperty Count)"
    )
    if cmd_exe:
        return _powershell_command_for_cmd_exe(inner)
    return inner


def _rewrite_grep_line_for_windows(stripped: str, *, cmd_exe: bool) -> str | None:
    """Turn a simple ``grep`` into ``Select-String`` (or a cmd-friendly PowerShell wrapper)."""
    parsed = _parse_simple_grep_for_windows(stripped)
    if parsed is None:
        return None
    ps_pat = _grep_pattern_for_select_string(parsed.pattern, fixed_strings=parsed.fixed_strings)
    ps_pat_esc = _ps_escape_single(ps_pat)
    ps_file = _ps_escape_single(parsed.path)
    simple = " -SimpleMatch" if parsed.fixed_strings else ""
    ci = " -CaseSensitive:$false" if parsed.ignore_case else ""
    inner = (
        f"Select-String -LiteralPath '{ps_file}' -Pattern '{ps_pat_esc}'{simple}{ci}"
    )
    if cmd_exe:
        return _powershell_command_for_cmd_exe(inner)
    return inner


def _rewrite_unix_date_line_for_windows(stripped: str, *, cmd_exe: bool) -> str | None:
    """If *stripped* is a read-only GNU-style ``date`` line, return PowerShell equivalent."""
    if not stripped:
        return None
    inner: str | None = None
    if stripped == "date":
        inner = "Get-Date"
    elif stripped in ("date +%Y-%m-%d", "date +%F"):
        inner = "Get-Date -Format 'yyyy-MM-dd'"
    else:
        m = re.fullmatch(r"date\s+(['\"])(\+\S+)\1\s*", stripped)
        if m and m.group(2) in ("+%Y-%m-%d", "+%F"):
            inner = "Get-Date -Format 'yyyy-MM-dd'"
    if inner is None:
        return None
    if cmd_exe:
        return _powershell_command_for_cmd_exe(inner)
    return inner


def _expand_windows_cmd(command: str) -> str:
    """Translate common Unix-only patterns when the shell is Windows cmd.exe."""
    stripped = (command or "").strip()
    if not stripped:
        return command

    date_rw = _rewrite_unix_date_line_for_windows(stripped, cmd_exe=True)
    if date_rw is not None:
        return date_rw

    grep_ctx = _rewrite_grep_context_file_pipe_head(stripped, cmd_exe=True)
    if grep_ctx is not None:
        return grep_ctx

    grep_rw = _rewrite_grep_line_for_windows(stripped, cmd_exe=True)
    if grep_rw is not None:
        return grep_rw

    ls_wc = _rewrite_ls_pipe_wc_line_count(stripped, cmd_exe=True)
    if ls_wc is not None:
        return ls_wc

    wc_file = _rewrite_wc_l_single_file(stripped, cmd_exe=True)
    if wc_file is not None:
        return wc_file

    find_grep = _rewrite_find_pipe_grep_e_pipe_head(stripped, cmd_exe=True)
    if find_grep is not None:
        return find_grep

    find_head = _rewrite_find_pipe_head_only(stripped, cmd_exe=True)
    if find_head is not None:
        return find_head

    find_wc = _rewrite_find_pipe_wc_line_count(stripped, cmd_exe=True)
    if find_wc is not None:
        return find_wc

    ls_or_echo = _rewrite_ls_la_stderr_or_echo(stripped, cmd_exe=True)
    if ls_or_echo is not None:
        return ls_or_echo

    if stripped == "pwd":
        return "cd"

    simple_ls = re.fullmatch(
        r"ls(?:\s+(?P<path>.*?))?(?:\s+2>/dev/null)?(?:\s*\|\s*head\s*-?\s*(?P<head>\d+))?\s*",
        stripped,
        flags=re.IGNORECASE,
    )
    if simple_ls:
        path_arg = (simple_ls.group("path") or ".").strip().strip("\"'")
        head_n = simple_ls.group("head")
        ps_path = _ps_escape_single(path_arg)
        select = f" | Select-Object -First {head_n}" if head_n else ""
        inner_ls = f"Get-ChildItem -Name -LiteralPath '{ps_path}' 2>$null{select}"
        return _powershell_command_for_cmd_exe(inner_ls)

    m = re.fullmatch(r"ls\s+-la?\s+(?P<path>.+)", stripped, flags=re.IGNORECASE)
    if m:
        path_arg = m.group("path").strip().strip("\"'")
        ps_path = _ps_escape_single(path_arg)
        inner_la = f"Get-ChildItem -LiteralPath '{ps_path}' | Format-Table -AutoSize"
        return _powershell_command_for_cmd_exe(inner_la)

    m = re.fullmatch(r"cat\s+(?P<path>.+)", stripped, flags=re.IGNORECASE)
    if m:
        path_arg = m.group("path").strip().strip("\"'")
        if " " not in path_arg and not any(c in path_arg for c in "&|<>^"):
            return f"type {path_arg}"

    m = re.fullmatch(
        r"head\s+(?:-n\s+)?(?P<n>\d+)\s+(?P<path>.+)",
        stripped,
        flags=re.IGNORECASE,
    )
    if m:
        n, path_arg = m.group("n"), m.group("path").strip().strip("\"'")
        ps_path = _ps_escape_single(path_arg)
        inner_head = f"Get-Content -LiteralPath '{ps_path}' -TotalCount {n}"
        return _powershell_command_for_cmd_exe(inner_head)

    m = re.fullmatch(
        r"tail\s+(?:-n\s+)?(?P<n>\d+)\s+(?P<path>.+)",
        stripped,
        flags=re.IGNORECASE,
    )
    if m:
        n, path_arg = m.group("n"), m.group("path").strip().strip("\"'")
        ps_path = _ps_escape_single(path_arg)
        inner_tail = f"Get-Content -LiteralPath '{ps_path}' -Tail {n}"
        return _powershell_command_for_cmd_exe(inner_tail)

    m = re.fullmatch(r"which\s+(?P<name>\S+)", stripped, flags=re.IGNORECASE)
    if m:
        return f"where {m.group('name')}"

    if re.fullmatch(r"uname(\s.*)?", stripped, flags=re.IGNORECASE):
        return "ver & echo %OS%"

    out = re.sub(r"\s+2>/dev/null\s*$", " 2>nul", stripped, flags=re.IGNORECASE)
    if out != stripped:
        return out

    return command


def _expand_windows_powershell(command: str) -> str:
    """Light-touch fixes when the shell is already PowerShell."""
    stripped = (command or "").strip()
    if not stripped:
        return command

    date_rw = _rewrite_unix_date_line_for_windows(stripped, cmd_exe=False)
    if date_rw is not None:
        return date_rw

    grep_ctx = _rewrite_grep_context_file_pipe_head(stripped, cmd_exe=False)
    if grep_ctx is not None:
        return grep_ctx

    grep_rw = _rewrite_grep_line_for_windows(stripped, cmd_exe=False)
    if grep_rw is not None:
        return grep_rw

    ls_wc = _rewrite_ls_pipe_wc_line_count(stripped, cmd_exe=False)
    if ls_wc is not None:
        return ls_wc

    wc_file = _rewrite_wc_l_single_file(stripped, cmd_exe=False)
    if wc_file is not None:
        return wc_file

    find_grep = _rewrite_find_pipe_grep_e_pipe_head(stripped, cmd_exe=False)
    if find_grep is not None:
        return find_grep

    find_head = _rewrite_find_pipe_head_only(stripped, cmd_exe=False)
    if find_head is not None:
        return find_head

    find_wc = _rewrite_find_pipe_wc_line_count(stripped, cmd_exe=False)
    if find_wc is not None:
        return find_wc

    ls_or_echo = _rewrite_ls_la_stderr_or_echo(stripped, cmd_exe=False)
    if ls_or_echo is not None:
        return ls_or_echo

    out = stripped

    # Bash-style stderr discard (any position; LLM often emits this in pipelines)
    out = re.sub(r"2>/dev/null", "2>$null", out, flags=re.IGNORECASE)

    # ``grep -E`` in the middle of a pipeline (no standalone ``grep.exe`` on Windows).
    out = _replace_pipe_grep_e_with_where_object(out)

    # Pipelines: `head` / `tail` are not Windows commands -- use Select-Object.
    # Order: more specific patterns first (e.g. -n 50 before bare -50).
    out = re.sub(
        r"\|\s*head\s+-n\s*(\d+)\b",
        r"| Select-Object -First \1",
        out,
        flags=re.IGNORECASE,
    )
    out = re.sub(
        r"\|\s*head\s+-\s*(\d+)\b",
        r"| Select-Object -First \1",
        out,
        flags=re.IGNORECASE,
    )
    out = re.sub(
        r"\|\s*head\s+(\d+)\b",
        r"| Select-Object -First \1",
        out,
        flags=re.IGNORECASE,
    )
    out = re.sub(r"\|\s*head\s*$", "| Select-Object -First 10", out, flags=re.IGNORECASE)

    out = re.sub(
        r"\|\s*tail\s+-n\s*(\d+)\b",
        r"| Select-Object -Last \1",
        out,
        flags=re.IGNORECASE,
    )
    out = re.sub(
        r"\|\s*tail\s+-\s*(\d+)\b",
        r"| Select-Object -Last \1",
        out,
        flags=re.IGNORECASE,
    )
    out = re.sub(
        r"\|\s*tail\s+(\d+)\b",
        r"| Select-Object -Last \1",
        out,
        flags=re.IGNORECASE,
    )

    # ``wc -l`` is not on Windows; count pipeline objects (lines, dir entries, etc.).
    out = re.sub(
        r"\|\s*wc\s+-l\s*$",
        "| Measure-Object | Select-Object -ExpandProperty Count",
        out,
        flags=re.IGNORECASE,
    )

    m = re.fullmatch(r"which\s+(?P<name>\S+)", out, flags=re.IGNORECASE)
    if m:
        return f"Get-Command {m.group('name')} | Select-Object -ExpandProperty Source"
    return out


def expand_command(command: str, shell_family: ShellFamily) -> str:
    """Rewrite the command string before spawn, based on shell family."""
    if shell_family == "cmd":
        return _expand_windows_cmd(command)
    if shell_family == "powershell":
        return _expand_windows_powershell(command)
    return command


def failure_hints(
    command: str,
    returncode: int,
    stderr: str,
    os_kind: OsKind,
    shell_family: ShellFamily,
) -> str | None:
    """Return an extra hint paragraph for failed invocations, or None."""
    err_low = (stderr or "").lower()
    cmd_low = (command or "").lower()

    if "not a git repository" in err_low and re.search(r"\bgit\b", cmd_low):
        return (
            "\n[Kageko shell hint] Git is not in a repository in this working directory; "
            "omit `cwd` to use the open project folder, or set `cwd` to the repo root."
        )

    if os_kind != "windows":
        return None
    parts: list[str] = []

    cmd_missing = returncode == 9009 or "not recognized" in err_low
    if not cmd_missing and stderr:
        # Localized Windows: e.g. Chinese "'grep' is not an internal or external command..."
        if "not an internal or external command" in stderr:
            cmd_missing = True
    if cmd_missing or ("not found" in err_low and returncode != 0):
        parts.append("Windows could not run part of this command (missing executable or typo).")

    tool_map: list[tuple[str, str]] = [
        ("grep", "Use the built-in `grep` tool, or PowerShell: Select-String -Path *.py -Pattern 'text'."),
        ("sed", "Avoid Unix `sed` on Windows cmd; use the `edit`/`patch` tools or PowerShell -replace."),
        ("awk", "Avoid `awk` on Windows; use a small Python one-liner or the `grep`/`view` tools."),
        ("head", "Use the `view` tool with offset/limit, or PowerShell: Get-Content -TotalCount N."),
        ("tail", "Use the `view` tool or PowerShell: Get-Content -Tail N."),
        ("cat", "Use the `view` tool to read files."),
        ("ls", "Use the built-in `ls` tool or PowerShell: Get-ChildItem."),
        ("find", "Use the `glob` tool for file names; for content search use `grep`."),
        ("wc", "Windows has no `wc`; use PowerShell: ... | Measure-Object -Line, or the built-in `ls` tool."),
    ]
    for name, hint in tool_map:
        if not re.search(rf"\b{re.escape(name)}\b", cmd_low):
            continue
        if cmd_missing or name in err_low:
            parts.append(hint)
            break

    if shell_family == "cmd" and any(x in cmd_low for x in ("2>$null", "get-childitem", "select-string")):
        parts.append(
            "This looks like PowerShell syntax; set `shell.path` to `powershell.exe` in settings, "
            "or wrap the snippet in: powershell -NoProfile -NonInteractive -Command \"...\"."
        )

    if len(parts) == 0 and returncode != 0:
        parts.append(
            "On Windows, prefer built-in tools (`view`, `ls`, `glob`, `grep`) over Unix shell "
            "utilities when possible."
        )

    if not parts:
        return None

    return "\n[Kageko shell hint] " + " ".join(parts)


def runtime_hint_line() -> str:
    """One line for system prompts (current OS)."""
    return f"Current runtime: {detect_runtime()} ({platform.system()})."
