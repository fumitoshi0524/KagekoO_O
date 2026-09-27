import { row, sanitizeTerminalText, type RenderRow, type RenderSpan } from "@kageko/tui-kit";

const EXT_LANG_MAP: Readonly<Record<string, string>> = {
	ts: "typescript",
	tsx: "typescript",
	js: "javascript",
	jsx: "javascript",
	py: "python",
	rb: "ruby",
	rs: "rust",
	go: "go",
	java: "java",
	sh: "bash",
	bash: "bash",
	zsh: "bash",
	json: "json",
	yaml: "yaml",
	yml: "yaml",
	toml: "toml",
	md: "markdown",
	css: "css",
	html: "html",
	sql: "sql",
	c: "c",
	cpp: "cpp",
	h: "c",
	hpp: "cpp",
};

export function langFromPath(filePath: string): string | undefined {
	const extension = filePath.split(/[\\/]/).pop()?.split(".").pop()?.toLowerCase();
	return extension ? (EXT_LANG_MAP[extension] ?? extension) : undefined;
}

/** Safe fallback API matching Kimi's helper; ANSI is intentionally never returned. */
export function highlightLines(code: string, _language?: string): string[] {
	return sanitizeTerminalText(code).split("\n");
}

function tokenSpans(line: string, language?: string): RenderSpan[] {
	const spans: RenderSpan[] = [];
	const pattern =
		/(\/\/.*|#.*|\/\*.*?\*\/|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`|\b(?:const|let|var|function|return|if|else|for|while|class|interface|type|import|from|export|async|await|new|throw|try|catch|def|fn|pub|use|select|from|where|insert|update)\b|\b\d+(?:\.\d+)?\b)/g;
	let cursor = 0;
	for (const match of line.matchAll(pattern)) {
		const index = match.index ?? cursor;
		if (index > cursor) spans.push({ text: line.slice(cursor, index), tone: "code" });
		const token = match[0];
		const tone = /^(\/\/|#|\/\*)/.test(token)
			? "muted"
			: /^("|'|`)/.test(token)
				? "success"
				: /^\d/.test(token)
					? "warning"
					: "primary";
		spans.push({ text: token, tone, bold: tone === "primary", italic: tone === "muted" });
		cursor = index + token.length;
	}
	if (cursor < line.length || spans.length === 0) spans.push({ text: line.slice(cursor), tone: "code" });
	void language;
	return spans;
}

export function renderCodePreview(
	code: string,
	width: number,
	options: { readonly language?: string; readonly expanded?: boolean; readonly maxLines?: number } = {},
): readonly RenderRow[] {
	const lines = highlightLines(code, options.language);
	const visible = options.expanded ? lines : lines.slice(0, options.maxLines ?? 5);
	const output = visible.map((line) => row({ text: "    ", tone: "muted" }, ...tokenSpans(line, options.language)));
	if (!options.expanded && lines.length > visible.length) {
		output.push(
			row({ text: `    ... ${lines.length - visible.length} more lines, ctrl+o to expand`, tone: "faint", dim: true }),
		);
	}
	void width;
	return output;
}
