"""Filesystem sandbox — restricts file access to a configurable workspace root.

Set `workspace_root` at startup (e.g. from AgentEngine or CLI), then all file
tools call `resolve_path()` before any filesystem operation. Paths outside the
root are rejected with a clear error message.
"""

from __future__ import annotations

from pathlib import Path

_workspace_root: Path | None = None


def set_workspace_root(root: str | Path) -> None:
    """Set the global workspace root for the current session."""
    global _workspace_root
    _workspace_root = Path(root).resolve()
    if not _workspace_root.is_dir():
        _workspace_root.mkdir(parents=True, exist_ok=True)


def get_workspace_root() -> Path:
    """Return the current workspace root, defaulting to CWD."""
    if _workspace_root is not None:
        return _workspace_root
    return Path.cwd()


def resolve_path(user_path: str, *, must_exist: bool = False) -> Path:
    """Resolve a user-provided path and enforce it is within the workspace root.

    Returns the resolved absolute path on success.
    Raises `SandboxViolation` if the path escapes the workspace.
    """
    root = get_workspace_root()
    raw = Path(user_path)

    # Resolve relative to the workspace root if not already absolute
    if not raw.is_absolute():
        resolved = (root / raw).resolve()
    else:
        resolved = raw.resolve()

    # Check containment: resolved must be equal to root or inside it
    try:
        resolved.relative_to(root)
    except ValueError:
        raise SandboxViolation(
            f"Path '{user_path}' resolves to '{resolved}', "
            f"which is outside the workspace root '{root}'."
        )

    if must_exist and not resolved.exists():
        raise SandboxViolation(f"Path does not exist: {resolved}")

    return resolved


class SandboxViolation(PermissionError):
    """Raised when a file operation attempts to access a path outside the workspace."""
    pass
