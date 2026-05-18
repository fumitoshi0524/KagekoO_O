"""Storage path resolution for Kageko runtime data."""

from __future__ import annotations

from pathlib import Path

KAGEKO_DIR = ".kageko"


def resolve_storage_roots(project_root: Path) -> tuple[Path, list[Path]]:
    """Return (primary_root, fallback_roots) for a project directory."""
    resolved = project_root.resolve()
    primary = resolved / KAGEKO_DIR
    return primary, []


def resolve_write_path(project_root: Path, relative_path: str) -> Path:
    """Always write to the .kageko directory."""
    primary, _ = resolve_storage_roots(project_root)
    target = primary / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def iter_read_candidates(project_root: Path, relative_path: str):
    """Yield paths in priority order. Currently only .kageko."""
    primary, _ = resolve_storage_roots(project_root)
    yield primary / relative_path


def ensure_primary_root(project_root: Path) -> Path:
    """Create the .kageko directory if it doesn't exist."""
    primary, _ = resolve_storage_roots(project_root)
    primary.mkdir(parents=True, exist_ok=True)
    return primary
