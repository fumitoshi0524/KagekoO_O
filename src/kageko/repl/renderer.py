"""Markdown rendering using Rich's built-in components."""
from __future__ import annotations

from rich.console import Console
from rich.markdown import Markdown


def render_markdown(console: Console, text: str) -> None:
    """Render markdown text with Rich's Markdown renderer."""
    if not text or not text.strip():
        return
    md = Markdown(text, code_theme="monokai", hyperlinks=True)
    console.print(md)
