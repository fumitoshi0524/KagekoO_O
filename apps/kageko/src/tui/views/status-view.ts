import { displayWidth, row, truncateDisplay, type RenderRow, type RenderSpan } from "@kageko/tui-kit";

export interface FooterInfo {
	readonly atTail: boolean;
	readonly queued: number;
	readonly cwd: string;
	readonly model?: string;
	readonly contextUsed?: number;
	readonly contextLength?: number;
	readonly thinking?: string;
	/** Active permission policy, read from permission.defaultProfile. */
	readonly permissionProfile?: "manual" | "workspace" | "unrestricted";
	/** Active interaction policy, read from interaction.defaultMode. */
	readonly interactionMode?: "interactive" | "unattended";
	readonly contextPercent?: number;
	readonly contextUsedSource?: "authoritative" | "catalog" | "configured" | "estimated" | "unknown";
	readonly contextLimitSource?: "authoritative" | "catalog" | "configured" | "estimated" | "unknown";
	/** Pending learning proposals; shown as a badge so discovery skips /learn. */
	readonly learningPending?: number;
	readonly transientHint?: string;
}

export function footerLines(overlay: string, info: FooterInfo, columns: number): readonly RenderRow[] {
	if (overlay !== "none")
		return [
			row(
				{ text: overlay === "shell" ? " F2" : " Esc", tone: "primary", bold: true },
				{ text: overlay === "shell" ? " return to TUI" : " close · PgUp/PgDn scroll", tone: "faint" },
			),
		];
	const context = formatContext(info);
	if (columns < 60)
		return [
			row(
				{ text: " ready", tone: "success" },
				{ text: `  q:${info.queued}`, tone: "primary" },
				...(info.learningPending ? [{ text: `  learn: ${info.learningPending}`, tone: "warning" as const }] : []),
				{ text: `  ${context}`, tone: "faint" },
			),
		];
	const badge: RenderSpan[] = info.permissionProfile
		? [
				{
					text: ` perm:${info.permissionProfile}`,
					tone: info.permissionProfile === "manual" ? ("primary" as const) : ("warning" as const),
					bold: true,
				},
				...(info.interactionMode === "unattended"
					? [{ text: " unattended", tone: "warning" as const, bold: true }]
					: []),
			]
		: [];
	const learningBadge: RenderSpan[] = info.learningPending
		? [{ text: ` learn: ${info.learningPending}`, tone: "warning" as const, bold: true }]
		: [];
	const model =
		info.model === undefined ? undefined : ` ${info.model}${info.thinking ? ` · thinking: ${info.thinking}` : ""}`;
	const fixed =
		badge.reduce((width, span) => width + displayWidth(String(span.text)), 0) +
		learningBadge.reduce((width, span) => width + displayWidth(String(span.text)), 0) +
		(model === undefined ? 0 : displayWidth(model)) +
		displayWidth(context) +
		4;
	const cwd = truncateDisplay(shortenCwd(info.cwd), Math.max(4, columns - fixed));
	const left: RenderSpan[] = [
		...badge,
		...learningBadge,
		...(model === undefined ? [] : [{ text: model, tone: "muted" as const }]),
		{ text: `  ${cwd}`, tone: "faint" },
	];
	const leftWidth = left.reduce((width, span) => width + displayWidth(String(span.text)), 0);
	const gap = Math.max(1, columns - leftWidth - displayWidth(context) - 1);
	const line1 = row(...left, { text: `${" ".repeat(gap)}${context} `, tone: "faint" });
	const line2 = info.transientHint
		? row({ text: ` ${info.transientHint}`, tone: "faint" })
		: row(
				{ text: " Enter", tone: "primary", bold: true },
				{ text: " send · ", tone: "faint" },
				{ text: "Alt+Enter", tone: "primary", bold: true },
				{ text: " newline · ", tone: "faint" },
				{ text: "F2", tone: "primary", bold: true },
				{ text: " shell · ", tone: "faint" },
				{ text: "/help", tone: "primary", bold: true },
				{ text: " · ready", tone: "faint" },
			);
	return [line1, line2];
}

function formatContext(info: FooterInfo): string {
	if (typeof info.contextPercent === "number" && Number.isFinite(info.contextPercent))
		return `context: ${info.contextPercent.toFixed(1)}%`;
	const used = formatTokenCount(info.contextUsed, info.contextUsedSource);
	const limit = formatTokenCount(info.contextLength, info.contextLimitSource);
	return `${info.contextUsedSource === "estimated" ? "ctx est." : "ctx"} ${used}/${limit}`;
}

export function formatTokenCount(
	value: number | undefined,
	source: FooterInfo["contextUsedSource"] = undefined,
): string {
	if (source === "unknown") return "?";
	if (typeof value !== "number" || !Number.isFinite(value)) return "?";
	const rounded = Math.max(0, Math.round(value));
	const compact =
		rounded >= 1_000_000
			? `${trimDecimal(rounded / 1_000_000)}M`
			: rounded >= 1_000
				? `${trimDecimal(rounded / 1_000)}K`
				: rounded.toLocaleString();
	return source === "estimated" ? `~${compact}` : compact;
}

function trimDecimal(value: number): string {
	return value >= 100 ? Math.round(value).toString() : value.toFixed(1).replace(/\.0$/, "");
}

/** Keeps the last three path segments under an ellipsis. */
export function shortenCwd(cwd: string): string {
	const parts = cwd.split(/[\\/]/).filter(Boolean);
	return parts.length <= 3 ? cwd : `…/${parts.slice(-3).join("/")}`;
}
