const ANSI_CSI = /\x1b\[[0-?]*[ -/]*[@-~]/g;
const ANSI_OSC = /\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)/g;
// Preserve CR/LF long enough to normalize them, and preserve tabs long enough
// to turn them into inert spaces below.
const CONTROLS = /[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f-\u009f]/g;

/** Removes terminal escape sequences before measuring or displaying foreign text. */
export function stripAnsi(value: string): string {
	return value.replace(ANSI_OSC, "").replace(ANSI_CSI, "");
}

/** Makes SDK/model/tool text safe to place in a terminal-owned frame. */
export function sanitizeTerminalText(value: unknown): string {
	const text = typeof value === "string" ? value : safeStringify(value);
	return terminalText(text);
}

/** Terminal-cell width for ordinary text, CJK and emoji grapheme clusters. */
export function displayWidth(value: string): number {
	return [...graphemes(terminalText(value))].reduce((width, grapheme) => width + graphemeWidth(grapheme), 0);
}

export function truncateDisplay(value: string, maximum: number, suffix = "…"): string {
	if (maximum <= 0) return "";
	const plain = terminalText(value);
	if (displayWidth(plain) <= maximum) return plain;
	const suffixWidth = displayWidth(suffix);
	if (suffixWidth >= maximum) return suffix;
	let output = "";
	let width = 0;
	for (const grapheme of graphemes(plain)) {
		const next = graphemeWidth(grapheme);
		if (width + next + suffixWidth > maximum) break;
		output += grapheme;
		width += next;
	}
	return `${output}${suffix}`;
}

/** Word-aware terminal wrapping with an unconditional progress guarantee. */
export function wrapDisplay(value: string, maximum: number): readonly string[] {
	if (maximum <= 0) return [""];
	const result: string[] = [];
	for (const sourceLine of terminalText(value).split("\n")) {
		if (!sourceLine) {
			result.push("");
			continue;
		}
		let line = "";
		let width = 0;
		for (const grapheme of graphemes(sourceLine)) {
			const next = graphemeWidth(grapheme);
			if (width > 0 && width + next > maximum) {
				result.push(line);
				line = "";
				width = 0;
			}
			// A two-cell glyph in a one-column terminal is represented once rather
			// than spinning forever trying to split a grapheme cluster.
			line += grapheme;
			width += next;
		}
		result.push(line);
	}
	return result.length ? result : [""];
}

export function graphemeCount(value: string): number {
	return [...graphemes(value)].length;
}

export function sliceGraphemes(value: string, start: number, end?: number): string {
	return [...graphemes(value)].slice(start, end).join("");
}

export function* graphemes(value: string): Iterable<string> {
	const Segmenter = Intl.Segmenter;
	if (Segmenter) {
		for (const item of new Segmenter(undefined, { granularity: "grapheme" }).segment(value)) yield item.segment;
		return;
	}
	yield* value;
}

function graphemeWidth(value: string): number {
	if (!value) return 0;
	if (value === "\n") return 0;
	if (value.includes("\u200d") || /\p{Extended_Pictographic}/u.test(value)) return 2;
	const code = value.codePointAt(0) ?? 0;
	// A decomposed cluster such as e + COMBINING ACUTE has the width of its
	// leading base character. Only a cluster that starts with a mark is zero.
	if (code === 0 || /^\p{Mark}/u.test(value)) return 0;
	return isWide(code) ? 2 : 1;
}

function terminalText(value: string): string {
	// Tabs are never emitted as controls: their terminal-dependent tab stops
	// would make a full-frame redraw and cursor placement non-deterministic.
	return stripAnsi(value)
		.replace(CONTROLS, "")
		.replaceAll("\t", "    ")
		.replaceAll("\r\n", "\n")
		.replaceAll("\r", "\n");
}

function safeStringify(value: unknown): string {
	try {
		return JSON.stringify(value) ?? String(value);
	} catch {
		return String(value);
	}
}

function isWide(code: number): boolean {
	return (
		code >= 0x1100 &&
		(code <= 0x115f ||
			code === 0x2329 ||
			code === 0x232a ||
			(code >= 0x2e80 && code <= 0xa4cf && code !== 0x303f) ||
			(code >= 0xac00 && code <= 0xd7a3) ||
			(code >= 0xf900 && code <= 0xfaff) ||
			(code >= 0xfe10 && code <= 0xfe19) ||
			(code >= 0xfe30 && code <= 0xfe6f) ||
			(code >= 0xff00 && code <= 0xff60) ||
			(code >= 0xffe0 && code <= 0xffe6) ||
			(code >= 0x20000 && code <= 0x3fffd))
	);
}
