import { displayWidth, row, sliceGraphemes, wrapDisplay, type RenderRow, type RenderSpan } from "@kageko/tui-kit";

export interface ComposerOptions {
	readonly columns: number;
	readonly maxRows: number;
	readonly text: string;
	readonly cursorIndex: number;
	readonly placeholder?: string;
	readonly prompt?: string;
	readonly focused?: boolean;
}

export interface ComposerFrame {
	readonly lines: readonly RenderRow[];
	readonly cursorRow: number;
	readonly cursorColumn: number;
	readonly hiddenAbove: number;
}

/** Rounded composer box: border rows plus windowed content rows; cursor in box coordinates. */
export function composerLines(options: ComposerOptions): ComposerFrame {
	const columns = Math.max(8, options.columns);
	const prompt = options.prompt ?? "> ";
	const border = options.focused ? ("primary" as const) : ("surface" as const);
	const inner = Math.max(4, columns - 4);
	const ghost = !options.text && Boolean(options.placeholder);
	const wrapped = wrapWords(options.text ? `${prompt}${options.text}` : `${prompt}${options.placeholder ?? ""}`, inner);
	const content: { readonly spans: readonly RenderSpan[] }[] = wrapped.map((line, index) => {
		if (index === 0)
			return {
				spans: [
					{ text: prompt, tone: "primary" as const },
					{ text: line.slice(prompt.length), tone: ghost ? ("faint" as const) : ("default" as const) },
				],
			};
		return { spans: [{ text: line, tone: ghost ? ("faint" as const) : ("default" as const) }] };
	});
	const beforeWrapped = wrapWords(`${prompt}${sliceGraphemes(options.text, 0, options.cursorIndex)}`, inner);
	let cursorRow = beforeWrapped.length - 1;
	let cursorColumn = displayWidth(beforeWrapped.at(-1) ?? "");
	if (cursorColumn >= inner) {
		cursorRow += 1;
		cursorColumn = 0;
	}
	while (content.length <= cursorRow) content.push({ spans: [{ text: "", tone: "default" as const }] });
	const budget = Math.max(1, options.maxRows - 2);
	const start = Math.max(0, Math.min(content.length - budget, cursorRow - budget + 1));
	const hiddenAbove = start;
	const indicator =
		hiddenAbove > 0 && start < cursorRow
			? inner >= 16
				? `─── ↑ ${hiddenAbove} more ───`
				: `↑ ${hiddenAbove}`
			: undefined;
	const body = content.slice(start, start + budget).map((entry, index) => {
		const spans: readonly RenderSpan[] =
			index === 0 && indicator ? [{ text: indicator, tone: "faint" as const, dim: true }] : entry.spans;
		const used = spans.reduce((width, span) => width + displayWidth(String(span.text)), 0);
		return row({ text: "│ ", tone: border }, ...spans, {
			text: `${" ".repeat(Math.max(0, inner - used))} │`,
			tone: border,
		});
	});
	const bar = "─".repeat(Math.max(1, columns - 2));
	return {
		lines: [row({ text: `╭${bar}╮`, tone: border }), ...body, row({ text: `╰${bar}╯`, tone: border })],
		cursorRow: cursorRow - start + 1,
		cursorColumn,
		hiddenAbove,
	};
}

/** Word-aware wrap: breaks at spaces when possible, hard-wraps words longer than the width. */
function wrapWords(value: string, maximum: number): readonly string[] {
	const width = Math.max(1, maximum);
	const result: string[] = [];
	for (const sourceLine of value.split("\n")) {
		let line = "";
		for (const word of sourceLine.split(" ")) {
			const candidate = line ? `${line} ${word}` : word;
			if (displayWidth(candidate) <= width) {
				line = candidate;
				continue;
			}
			if (line) result.push(line);
			const pieces = wrapDisplay(word, width);
			result.push(...pieces.slice(0, -1));
			line = pieces.at(-1) ?? "";
		}
		result.push(line);
	}
	return result;
}
