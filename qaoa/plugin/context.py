from __future__ import annotations

from pathlib import Path

from ..utils.text import sanitize_text as _sanitize_text


def _read_text_limited(path: Path, *, max_chars: int) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""
    text = _sanitize_text(text)
    if len(text) > max_chars:
        return text[:max_chars] + "\n... (truncated)"
    return text


def _iter_context_files(working_dir: Path, entry: str) -> list[Path]:
    """Resolve a single `context_paths` entry to a list of files."""
    raw = entry.strip()
    if not raw:
        return []

    # Absolute path support (rare, but helpful).
    p = Path(raw)
    if not p.is_absolute():
        p = working_dir / raw

    if p.is_file():
        return [p]

    if p.is_dir():
        out: list[Path] = []
        for child in sorted(p.rglob("*")):
            if child.is_file() and child.suffix.lower() in {".md", ".txt"}:
                out.append(child)
        return out

    return []


def load_context_paths_content(
    *,
    working_dir: str | Path,
    context_paths: list[str],
    max_files: int = 20,
    max_chars_total: int = 50000,
    max_chars_per_file: int = 15000,
) -> str:
    """Load the content of files referenced by `settings.context_paths`.

    Returns:
        A markdown string that can be appended to the system prompt.
    """

    working_dir = Path(working_dir)
    remaining = max_chars_total
    files_loaded = 0

    sections: list[str] = []
    for entry in context_paths:
        for file_path in _iter_context_files(working_dir, entry):
            if files_loaded >= max_files or remaining <= 0:
                break
            if not file_path.exists() or not file_path.is_file():
                continue

            content = _read_text_limited(
                file_path, max_chars=min(max_chars_per_file, remaining)
            )
            if not content.strip():
                continue

            rel = str(file_path.relative_to(working_dir)) if file_path.is_relative_to(working_dir) else str(file_path)
            sections.append(f"### {rel}\n\n{content}\n")

            remaining -= len(content)
            files_loaded += 1

        if files_loaded >= max_files or remaining <= 0:
            break

    if not sections:
        return ""
    return "\n".join(sections)
