import { renderMarkdownBlocks, row, sanitizeTerminalText, type RenderRow } from "@kageko/tui-kit";
import type { TranscriptRecord } from "../../types.js";
import { renderExpandableOutput } from "./expandable-output.js";

export interface PlanBoxOptions {
	readonly expanded?: boolean;
	readonly status?: string;
	readonly maxLines?: number;
}

/** Width-aware plan card. The border is semantic output, not a terminal escape sequence. */
export function renderPlanBox(plan: string, width: number, options: PlanBoxOptions = {}): readonly RenderRow[] {
	const safeWidth = Math.max(12, width);
	const innerWidth = Math.max(8, safeWidth - 6);
	const markdown = renderMarkdownBlocks(sanitizeTerminalText(plan).trim() || "Drafting plan…", innerWidth, {
		tone: "default",
		headingTone: "strong",
		quoteTone: "muted",
		codeTone: "code",
	});
	const limit = options.maxLines ?? 8;
	const content = options.expanded ? markdown : markdown.slice(0, limit);
	const title = ` plan${options.status ? ` · ${options.status}` : ""} `;
	const horizontal = "─".repeat(Math.max(2, safeWidth - title.length - 4));
	const output: RenderRow[] = [
		row(
			{ text: "  ┌", tone: "accent" },
			{ text: title, tone: "accent", bold: true },
			{ text: horizontal, tone: "accent" },
			{ text: "┐", tone: "accent" },
		),
	];
	for (const contentRow of content) {
		output.push(row({ text: "  │ ", tone: "accent" }, ...contentRow.spans, { text: " │", tone: "accent" }));
	}
	if (!options.expanded && markdown.length > content.length) {
		output.push(
			...renderExpandableOutput([`${markdown.length - content.length} more plan lines`], {
				indent: "  │ ",
				tone: "faint",
			}),
		);
	}
	output.push(row({ text: `  └${"─".repeat(Math.max(2, safeWidth - 4))}┘`, tone: "accent" }));
	return output;
}

export function renderPlanRecord(record: TranscriptRecord, width: number): readonly RenderRow[] {
	return renderPlanBox(record.tool?.output ?? record.detail ?? record.text, width, {
		expanded: record.expanded,
		status: record.state === "running" ? "drafting" : record.state,
	});
}
