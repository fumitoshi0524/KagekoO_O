"""Unified project storage path resolver.

Priority:
1) .kageko
2) .clawcode
3) .claude
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


STORAGE_PRIORITY = (".kageko", ".clawcode", ".claude")


@dataclass(frozen=True)
class StorageRoots:
    project_root: Path
    primary_root: Path
    fallback_roots: tuple[Path, ...]

    @property
    def all_roots(self) -> tuple[Path, ...]:
        return (self.primary_root, *self.fallback_roots)


def resolve_storage_roots(project_root: str | Path) -> StorageRoots:
    base = Path(project_root).expanduser().resolve()
    primary = base / STORAGE_PRIORITY[0]
    fallbacks = tuple(base / name for name in STORAGE_PRIORITY[1:])
    return StorageRoots(project_root=base, primary_root=primary, fallback_roots=fallbacks)


def ensure_primary_root(project_root: str | Path) -> Path:
    roots = resolve_storage_roots(project_root)
    roots.primary_root.mkdir(parents=True, exist_ok=True)
    return roots.primary_root


def resolve_write_path(project_root: str | Path, relative_path: str | Path) -> Path:
    roots = resolve_storage_roots(project_root)
    out = roots.primary_root / Path(relative_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    return out


def iter_read_candidates(project_root: str | Path, relative_path: str | Path) -> Iterator[Path]:
    roots = resolve_storage_roots(project_root)
    rel = Path(relative_path)
    for root in roots.all_roots:
        yield root / rel


def resolve_existing_read_path(
    project_root: str | Path,
    relative_path: str | Path,
) -> Path | None:
    for cand in iter_read_candidates(project_root, relative_path):
        if cand.exists():
            return cand
    return None
