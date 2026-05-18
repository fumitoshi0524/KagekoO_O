"""Git helpers for /rewind: inspect and restore tracked files (never touches untracked)."""

from __future__ import annotations

import subprocess
from pathlib import Path


def _run_git(
    cwd: Path,
    args: list[str],
    *,
    timeout: float = 60.0,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )


def is_git_repo(cwd: Path) -> bool:
    p = _run_git(cwd, ["rev-parse", "--is-inside-work-tree"], timeout=10.0)
    return p.returncode == 0 and "true" in (p.stdout or "").strip().lower()


def git_tracked_paths_differing_from_head(cwd: Path) -> tuple[list[str], str | None]:
    """Paths where index or worktree differs from HEAD (tracked only; no untracked ??)."""
    p = _run_git(cwd, ["diff", "--name-only", "HEAD"])
    if p.returncode != 0:
        err = (p.stderr or p.stdout or "").strip() or f"git exit {p.returncode}"
        return [], err
    paths = [line.strip() for line in (p.stdout or "").splitlines() if line.strip()]
    return paths, None


def git_status_porcelain_summary(cwd: Path) -> tuple[str, str | None]:
    p = _run_git(cwd, ["status", "--porcelain"], timeout=30.0)
    if p.returncode != 0:
        return "", (p.stderr or "").strip() or f"git exit {p.returncode}"
    return (p.stdout or "").strip(), None


def git_diff_stat(cwd: Path) -> tuple[str, str | None]:
    p = _run_git(cwd, ["diff", "--stat", "HEAD"], timeout=60.0)
    if p.returncode != 0:
        return "", (p.stderr or "").strip() or f"git exit {p.returncode}"
    return (p.stdout or "").strip(), None


def git_rev_parse_short(cwd: Path, rev: str = "HEAD") -> tuple[str | None, str | None]:
    p = _run_git(cwd, ["rev-parse", "--short", rev], timeout=10.0)
    if p.returncode != 0:
        err = (p.stderr or p.stdout or "").strip() or f"git exit {p.returncode}"
        return None, err
    sha = (p.stdout or "").strip()
    return (sha if sha else None), None


def git_diff_stat_range(cwd: Path, base: str, head: str = "HEAD") -> tuple[str, str | None]:
    """Diff from commit `base` to `head`. If `head` is HEAD, include working tree vs `base` (not just last commit)."""
    if head == "HEAD":
        args = ["diff", "--stat", base]
    else:
        args = ["diff", "--stat", f"{base}..{head}"]
    p = _run_git(cwd, args, timeout=120.0)
    if p.returncode != 0:
        return "", (p.stderr or p.stdout or "").strip() or f"git exit {p.returncode}"
    return (p.stdout or "").strip(), None


def git_diff_name_status_range(cwd: Path, base: str, head: str = "HEAD") -> tuple[str, str | None]:
    if head == "HEAD":
        args = ["diff", "--name-status", base]
    else:
        args = ["diff", "--name-status", f"{base}..{head}"]
    p = _run_git(cwd, args, timeout=120.0)
    if p.returncode != 0:
        return "", (p.stderr or p.stdout or "").strip() or f"git exit {p.returncode}"
    return (p.stdout or "").strip(), None


def git_stash_push_message(cwd: Path, message: str) -> tuple[bool, str]:
    p = _run_git(cwd, ["stash", "push", "-m", message], timeout=120.0)
    if p.returncode != 0:
        msg = (p.stderr or p.stdout or "").strip() or f"git stash failed ({p.returncode})"
        return False, msg
    return True, ""


def git_restore_tracked_paths_to_head(cwd: Path, paths: list[str]) -> tuple[bool, str]:
    """Restore both index and worktree for paths to match HEAD. Does not delete untracked files."""
    if not paths:
        return True, ""
    p = _run_git(
        cwd,
        ["restore", "--source=HEAD", "--staged", "--worktree", "--", *paths],
        timeout=120.0,
    )
    if p.returncode != 0:
        msg = (p.stderr or p.stdout or "").strip() or f"git restore failed ({p.returncode})"
        return False, msg
    return True, ""
