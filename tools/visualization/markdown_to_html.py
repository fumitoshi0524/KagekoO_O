"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Convert Markdown text to HTML."""
    try:
        data = json.loads(payload)
        markdown = str(data.get("markdown", ""))
    except (json.JSONDecodeError, TypeError):
        markdown = payload

    if not markdown.strip():
        return "error: no markdown provided"

    try:
        import markdown as md_lib
        html = md_lib.markdown(markdown, extensions=["tables", "fenced_code", "codehilite"])
    except ImportError:
        html = _simple_markdown_to_html(markdown)

    return html


def _simple_markdown_to_html(text: str) -> str:
    """Basic markdown to HTML conversion without external deps."""
    import re

    # Code blocks (triple backtick)
    def code_block_replacer(m):
        lang = m.group(1) or ""
        code = m.group(2)
        return f'<pre><code class="{lang}">{_escape_html(code)}</code></pre>'
    text = re.sub(r'```(\w*)\n(.*?)```', code_block_replacer, text, flags=re.DOTALL)

    # Inline code
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)

    # Bold and italic
    text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)

    # Images (before links)
    text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'<img src="\2" alt="\1">', text)

    # Links
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)

    # Headers
    text = re.sub(r'^#### (.+)$', r'<h4>\1</h4>', text, flags=re.MULTILINE)
    text = re.sub(r'^### (.+)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.+)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
    text = re.sub(r'^# (.+)$', r'<h1>\1</h1>', text, flags=re.MULTILINE)

    # Horizontal rule
    text = re.sub(r'^---$', '<hr>', text, flags=re.MULTILINE)

    # Unordered lists
    text = re.sub(r'^(\s*)[-*] (.+)$', r'\1<li>\2</li>', text, flags=re.MULTILINE)
    text = re.sub(r'(<li>.*</li>\n?)+', r'<ul>\g<0></ul>', text)

    # Paragraphs (consecutive non-empty lines)
    paragraphs = text.split('\n\n')
    result = []
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        if p.startswith('<') and not p.startswith('<li'):
            result.append(p)
        else:
            result.append(f'<p>{p.replace(chr(10), "<br>")}</p>')
    return '\n'.join(result)


def _escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


TOOL_SPEC = {
    "name": "markdown_to_html",
    "description": "Convert Markdown text to HTML with support for headers, links, images, code blocks, bold/italic, and lists.",
    "category": "visualization",
    "domain": "technology",
    "risk_level": "read",
    "schema": {
        "type": "object",
        "properties": {
            "markdown": {
                "type": "string",
                "description": "The Markdown text to convert to HTML."
            }
        },
        "required": ["markdown"]
    }
}
