import { row, truncateDisplay, type RenderRow } from "@kageko/tui-kit";
import type { QueuedPrompt } from "../types.js";
export function queueLines(queue: readonly QueuedPrompt[]): readonly RenderRow[] {
	const visible = queue.slice(0, 3);
	const rows = visible.map((item, index) =>
		row(
			{ text: "  Queue", tone: "muted", dim: true },
			{ text: ` ${index + 1}`, tone: "accent", bold: true },
			{
				text: item.text.startsWith("!") ? "  shell " : "  prompt ",
				tone: item.text.startsWith("!") ? "warning" : "muted",
			},
			{ text: truncateDisplay(item.text.replace(/^!/, ""), 58), tone: "default" },
			{ text: `  ${item.state}`, tone: item.state === "failed" ? ("danger" as const) : ("accent" as const) },
		),
	);
	return queue.length > visible.length
		? [...rows, row({ text: `  … +${queue.length - visible.length}`, tone: "muted", dim: true })]
		: rows;
}
