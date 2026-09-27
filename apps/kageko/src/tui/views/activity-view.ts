import { row, type RenderRow } from "@kageko/tui-kit";
import type { ActivityRecord } from "../types.js";

export const ACTIVITY_TIPS = [
	"Tip: /help lists every command",
	"Tip: Alt+Enter adds a newline to your prompt",
	"Tip: ctrl+o expands the latest tool output or thought",
	"Tip: ! prefix runs a shell command in the background",
	"Tip: /sessions switches between past sessions",
] as const;

export interface ActivityOptions {
	readonly spinnerFrame?: string;
	readonly tipIndex?: number;
}

export function activityLines(
	activities: readonly ActivityRecord[],
	options: ActivityOptions = {},
): readonly RenderRow[] {
	const item = activities.find((entry) => entry.state === "running") ?? activities.at(-1);
	if (!item)
		return [row({ text: "● Ready", tone: "success" }, { text: "  Type a request or /help", tone: "faint", dim: true })];
	if (item.state === "running") {
		const tip = ACTIVITY_TIPS[(options.tipIndex ?? 0) % ACTIVITY_TIPS.length]!;
		return [
			row(
				{ text: `${options.spinnerFrame ?? "◐"} `, tone: "primary" },
				{ text: item.label, tone: "default", bold: true },
				...(item.detail ? [{ text: `  ${item.detail}`, tone: "muted" as const, dim: true }] : []),
			),
			row({ text: tip, tone: "faint", dim: true }),
		];
	}
	const tone =
		item.state === "failed"
			? ("danger" as const)
			: item.state === "success"
				? ("success" as const)
				: ("muted" as const);
	const marker = item.state === "failed" ? "✗" : item.state === "success" ? "✓" : "●";
	return [
		row(
			{ text: `${marker} `, tone },
			{ text: item.label, tone: "default" },
			...(item.detail ? [{ text: `  ${item.detail}`, tone: "muted" as const, dim: true }] : []),
		),
	];
}
