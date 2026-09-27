import type { TerminalPort } from "./terminal.js";
import { backgroundCode, canvasCode, foregroundCode, resolveTheme, type ResolvedTheme, type Tone } from "./theme.js";
import { displayWidth, graphemes, sanitizeTerminalText } from "./width.js";

export type { Tone } from "./theme.js";
export interface RenderStyle {
	readonly tone?: Tone;
	readonly background?: Tone;
	readonly bold?: boolean;
	readonly dim?: boolean;
	readonly italic?: boolean;
	readonly underline?: boolean;
	readonly strikethrough?: boolean;
}
/** Trusted styling plus text that is sanitized at the boundary. Never accept ANSI in a span. */
export interface RenderSpan extends RenderStyle {
	readonly text: unknown;
}
export interface RenderRow {
	readonly spans: readonly RenderSpan[];
}
/** Compatibility shape; new views should use RenderRow for mixed semantic styling. */
export interface RenderLine extends RenderStyle {
	readonly text: unknown;
}
export interface RenderFrame {
	readonly lines: readonly (string | RenderLine | RenderRow)[];
	readonly cursor?: { readonly row: number; readonly column: number };
}

export function row(...spans: readonly RenderSpan[]): RenderRow {
	return { spans };
}
export function plainRow(text: unknown, style: RenderStyle = {}): RenderRow {
	return { spans: [{ text, ...style }] };
}
export function renderRowText(value: RenderRow | RenderLine | string): string {
	return typeof value === "string"
		? sanitizeTerminalText(value)
		: "spans" in value
			? value.spans.map((span) => sanitizeTerminalText(span.text)).join("")
			: sanitizeTerminalText(value.text);
}

const ANIMATION_INTERVAL_MS = 120;

/** Full-screen in-place renderer; terminal ownership stays with TerminalController. */
export class Renderer {
	private stopped = false;
	private previousLines: string[] = [];
	private previousColumns = 0;
	private previousRows = 0;
	private previousCursor: RenderFrame["cursor"];
	private animationTimer: ReturnType<typeof setInterval> | undefined;
	private animationCallback: (() => void) | undefined;
	constructor(
		private readonly output: TerminalPort,
		private readonly size: () => { readonly columns: number; readonly rows: number },
		private theme: ResolvedTheme = resolveTheme(),
	) {}
	setTheme(theme: ResolvedTheme): void {
		this.theme = theme;
		this.previousLines = [];
		this.previousColumns = 0;
		this.previousRows = 0;
		this.previousCursor = undefined;
	}
	render(frame: RenderFrame): void {
		if (this.stopped) return;
		const { columns, rows } = this.size();
		const lines = wrapRenderRows(frame.lines, columns)
			.slice(0, rows)
			.map((entry) => paint(entry, this.theme));
		const sizeChanged = this.previousColumns !== columns || this.previousRows !== rows;
		const full = this.previousLines.length === 0 || sizeChanged;
		const cursorChanged =
			this.previousCursor?.row !== frame.cursor?.row || this.previousCursor?.column !== frame.cursor?.column;
		let control = `\x1b[?2026h${canvasCode(this.theme)}`;
		if (full) {
			control += "\x1b[H\x1b[2J";
			for (let index = 0; index < lines.length; index += 1) {
				if (index > 0) control += "\r\n";
				control += lines[index]!;
			}
		} else {
			const maxLines = Math.max(this.previousLines.length, lines.length);
			let changed = false;
			for (let index = 0; index < maxLines; index += 1) {
				const next = lines[index] ?? "";
				if (next === (this.previousLines[index] ?? "")) continue;
				changed = true;
				control += `\x1b[${index + 1};1H\x1b[2K${next}`;
			}
			if (!changed && !cursorChanged) return;
		}
		if (frame.cursor) {
			control += "\x1b[?25h";
			control += `\x1b[${Math.min(rows, Math.max(1, frame.cursor.row + 1))};${Math.min(columns, Math.max(1, frame.cursor.column + 1))}H`;
		} else {
			control += "\x1b[?25l";
			control += `\x1b[${Math.min(rows, Math.max(1, lines.length + 1))};1H`;
		}
		control += "\x1b[?2026l";
		this.output.write(control);
		this.previousLines = [...lines];
		this.previousColumns = columns;
		this.previousRows = rows;
		this.previousCursor = frame.cursor ? { ...frame.cursor } : undefined;
	}
	/** ~120ms repaint tick for spinners. Re-entrant: starting twice keeps one timer. */
	startAnimation(callback: () => void): void {
		this.animationCallback = callback;
		if (this.animationTimer || this.stopped) return;
		const timer = setInterval(() => {
			if (this.stopped) return;
			try {
				this.animationCallback?.();
			} catch {
				this.stopAnimation();
			}
		}, ANIMATION_INTERVAL_MS);
		timer.unref?.();
		this.animationTimer = timer;
	}
	stopAnimation(): void {
		if (this.animationTimer) clearInterval(this.animationTimer);
		this.animationTimer = undefined;
		this.animationCallback = undefined;
	}
	clear(): void {
		if (this.stopped) return;
		this.output.write(`${canvasCode(this.theme)}\x1b[H\x1b[2J`);
		this.previousLines = [];
		this.previousColumns = 0;
		this.previousRows = 0;
		this.previousCursor = undefined;
	}
	stop(): void {
		this.stopAnimation();
		this.previousLines = [];
		this.previousColumns = 0;
		this.previousRows = 0;
		this.previousCursor = undefined;
		this.stopped = true;
	}
}
function normalize(source: string | RenderLine | RenderRow): RenderRow {
	return typeof source === "string" ? plainRow(source) : "spans" in source ? source : plainRow(source.text, source);
}
/** Materializes trusted styled rows to physical terminal rows without losing style boundaries. */
export function wrapRenderRows(
	sources: readonly (string | RenderLine | RenderRow)[],
	columns: number,
): readonly RenderRow[] {
	return sources.flatMap((source) => wrapRow(normalize(source), Math.max(1, columns)));
}
function wrapRow(source: RenderRow, width: number): readonly RenderRow[] {
	const output: RenderRow[] = [];
	let current: RenderSpan[] = [];
	let used = 0;
	const add = (style: RenderSpan, text: string) => {
		const last = current.at(-1);
		if (last && sameStyle(last, style)) current[current.length - 1] = { ...last, text: `${last.text}${text}` };
		else current.push({ ...style, text });
	};
	const push = () => {
		output.push({ spans: current });
		current = [];
		used = 0;
	};
	for (const sourceSpan of source.spans) {
		const pieces = sanitizeTerminalText(sourceSpan.text).split("\n");
		for (let pieceIndex = 0; pieceIndex < pieces.length; pieceIndex += 1) {
			for (const grapheme of graphemes(pieces[pieceIndex] ?? "")) {
				const glyph = displayWidth(grapheme) > width ? "?" : grapheme;
				const glyphWidth = displayWidth(glyph);
				if (used && used + glyphWidth > width) push();
				add(sourceSpan, glyph);
				used += glyphWidth;
				if (used === width) push();
			}
			if (pieceIndex < pieces.length - 1) push();
		}
	}
	if (current.length || !output.length) push();
	return output;
}
function sameStyle(a: RenderSpan, b: RenderSpan): boolean {
	return (
		a.tone === b.tone &&
		a.background === b.background &&
		a.bold === b.bold &&
		a.dim === b.dim &&
		a.italic === b.italic &&
		a.underline === b.underline &&
		a.strikethrough === b.strikethrough
	);
}
function paint(entry: RenderRow, theme: ResolvedTheme): string {
	return entry.spans
		.map((span) => `${style(span, theme)}${sanitizeTerminalText(span.text)}\x1b[0m${canvasCode(theme)}`)
		.join("");
}
function style(span: RenderStyle, theme: ResolvedTheme): string {
	return `${foregroundCode(theme, span.tone ?? "default")}${span.background ? backgroundCode(theme, span.background) : ""}${span.bold ? "\x1b[1m" : ""}${span.dim ? "\x1b[2m" : ""}${span.italic ? "\x1b[3m" : ""}${span.underline ? "\x1b[4m" : ""}${span.strikethrough ? "\x1b[9m" : ""}`;
}
