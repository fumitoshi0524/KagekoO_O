import { displayWidth, row, truncateDisplay, type RenderRow, type RenderSpan } from "@kageko/tui-kit";

export interface WelcomeInfo {
	readonly cwd: string;
	readonly sessionId?: string;
	readonly model?: string;
	readonly thinking?: string;
}

const LOGO = ["╭───────╮", "│ ●   ● │", "╰───────╯"] as const;

/** Full-width rounded welcome box; degrades logo-first, then to a compact header. */
export function welcomeLines(info: WelcomeInfo, columns: number): readonly RenderRow[] {
	if (columns < 40) {
		return [
			row({ text: " KAGEKO", tone: "primary", bold: true }),
			row({ text: ` ${truncateDisplay(info.cwd, Math.max(1, columns - 2))}`, tone: "muted" }),
			row({
				text: truncateDisplay(` session ${info.sessionId?.slice(0, 8) ?? "new"}`, Math.max(1, columns - 2)),
				tone: "muted",
				dim: true,
			}),
		];
	}
	const inner = Math.max(4, columns - 2);
	const withLogo = columns >= 60;
	const prefixWidth = withLogo ? 12 : 1;
	const textWidth = Math.max(4, inner - prefixWidth);
	const model =
		info.model === undefined ? undefined : `${info.model}${info.thinking ? ` · thinking: ${info.thinking}` : ""}`;
	const texts: readonly (readonly RenderSpan[])[] = [
		[{ text: "Welcome to Kageko!", tone: "strong", bold: true }],
		[
			{ text: "Directory: ", tone: "muted" },
			{ text: truncateDisplay(info.cwd, Math.max(1, textWidth - 11)), tone: "muted" },
		],
		[
			{ text: "Session: ", tone: "muted" },
			{ text: info.sessionId?.slice(0, 8) ?? "new", tone: "muted" },
		],
		...(model === undefined
			? []
			: [
					[
						{ text: "Model: ", tone: "muted" },
						{ text: truncateDisplay(model, Math.max(1, textWidth - 7)), tone: "muted" },
					] as const,
				]),
	];
	const bar = "─".repeat(inner);
	const lines: RenderRow[] = [row({ text: `╭${bar}╮`, tone: "primary" })];
	for (let index = 0; index < texts.length; index += 1) {
		const prefix: RenderSpan = withLogo
			? { text: ` ${LOGO[index] ?? " ".repeat(9)}  `, tone: "primary" }
			: { text: " ", tone: "default" };
		const spans: readonly RenderSpan[] = [prefix, ...texts[index]!];
		const used = spans.reduce((width, span) => width + displayWidth(String(span.text)), 0);
		lines.push(
			row({ text: "│", tone: "primary" }, ...spans, {
				text: `${" ".repeat(Math.max(0, inner - used))}│`,
				tone: "primary",
			}),
		);
	}
	lines.push(row({ text: `╰${bar}╯`, tone: "primary" }));
	return lines;
}
