import type { RenderRow, RenderSpan, Tone } from "./renderer.js";
import { row } from "./renderer.js";
import { sanitizeTerminalText, wrapDisplay } from "./width.js";
export interface MarkdownRenderOptions {
	readonly tone?: Tone;
	readonly headingTone?: Tone;
	readonly quoteTone?: Tone;
	readonly codeTone?: Tone;
}

/** Safe inline parser preserving typographic semantics as style runs. */
export function renderMarkdownInline(value: unknown): string {
	return inline(value)
		.map((span) => String(span.text))
		.join("");
}
export function renderMarkdownBlocks(
	text: unknown,
	columns: number,
	toneOrOptions: Tone | MarkdownRenderOptions = "default",
): readonly RenderRow[] {
	const options = typeof toneOrOptions === "string" ? { tone: toneOrOptions } : toneOrOptions;
	const base = options.tone ?? "default";
	const output: RenderRow[] = [];
	let fenced = false;
	for (const line of sanitizeTerminalText(text).split("\n")) {
		const fence = line.match(/^\s*(```|~~~)\s*([^\s]*)/);
		if (fence) {
			fenced = !fenced;
			output.push(row({ text: fenced ? `  ${fence[2] || "code"}` : "", tone: options.codeTone ?? "code", dim: true }));
			continue;
		}
		const prefix = fenced
			? "    "
			: (line.match(/^#{1,6}\s+(.*)$/)?.[0].replace(/^(#{1,6})\s+.*/, "$1 ") ?? line.match(/^>\s?/)?.[0] ?? "");
		const body = fenced
			? line
			: line
					.replace(/^#{1,6}\s+/, "")
					.replace(/^>\s?/, "")
					.replace(/^(\s*)[-*+]\s+/, "$1• ");
		const style = fenced
			? { tone: options.codeTone ?? ("code" as Tone), background: "surface" as Tone }
			: prefix.startsWith("#")
				? { tone: options.headingTone ?? ("accent" as Tone), bold: true }
				: prefix.startsWith(">")
					? { tone: options.quoteTone ?? ("muted" as Tone), italic: true }
					: { tone: base };
		const spans: RenderSpan[] = prefix ? [{ text: prefix.startsWith("#") ? "" : prefix, ...style }] : [];
		spans.push(...inline(body, style));
		output.push(...wrapSemanticRow(row(...spans), columns));
	}
	return output;
}
function inline(value: unknown, inherited: Partial<RenderSpan> = {}): RenderSpan[] {
	const text = sanitizeTerminalText(value);
	const spans: RenderSpan[] = [];
	let index = 0;
	const append = (textValue: string, style: Partial<RenderSpan> = inherited): void => {
		if (!textValue) return;
		const previous = spans.at(-1);
		if (previous && sameStyle(previous, style))
			spans[spans.length - 1] = { ...previous, text: `${previous.text}${textValue}` };
		else spans.push({ text: textValue, ...style });
	};
	while (index < text.length) {
		const emphasis = text.slice(index).match(/^(\*\*|__)(.+?)\1|^(\*|_)(.+?)\3/);
		if (emphasis) {
			append(emphasis[2] ?? emphasis[4]!, emphasis[2] ? { ...inherited, bold: true } : { ...inherited, italic: true });
			index += emphasis[0].length;
			continue;
		}
		const code = text.slice(index).match(/^(`+)(.+?)\1/);
		if (code) {
			append(code[2]!, { ...inherited, tone: "code", background: "surface" });
			index += code[0].length;
			continue;
		}
		const link = text.slice(index).match(/^\[([^\]]+)\]\(([^)]+)\)/);
		if (link) {
			append(`${link[1]} (${link[2]})`, { ...inherited, tone: "code", underline: true });
			index += link[0].length;
			continue;
		}
		const codePoint = text.codePointAt(index)!;
		const next = index + (codePoint > 0xffff ? 2 : 1);
		append(text.slice(index, next));
		index = next;
	}
	return spans;
}
function sameStyle(a: RenderSpan, b: Partial<RenderSpan>): boolean {
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
function wrapSemanticRow(source: RenderRow, columns: number): RenderRow[] {
	const text = source.spans.map((span) => String(span.text)).join("");
	const pieces = wrapDisplay(text, Math.max(1, columns));
	let offset = 0;
	return pieces.map((piece) => {
		let remaining = piece.length;
		const spans: RenderSpan[] = [];
		let position = offset;
		for (const original of source.spans) {
			const start = Math.max(0, position);
			const available = String(original.text).slice(start);
			if (remaining <= 0) break;
			const taken = available.slice(0, remaining);
			if (taken) spans.push({ ...original, text: taken });
			remaining -= taken.length;
			position = Math.max(0, position - String(original.text).length);
		}
		offset += piece.length;
		return row(...spans);
	});
}
