import { row, sanitizeTerminalText, wrapDisplay, type RenderRow } from "@kageko/tui-kit";
import type { TranscriptRecord } from "../../types.js";
import { renderExpandableOutput } from "./expandable-output.js";

export function renderSubagentCard(record: TranscriptRecord, width: number): readonly RenderRow[] {
	const state = record.state ?? (record.streaming ? "running" : "success");
	const marker = state === "failed" ? "✗" : state === "success" ? "✓" : record.streaming ? "◐" : "+";
	const tone = state === "failed" ? "danger" : state === "success" ? "success" : "primary";
	const title = record.text || "Subagent";
	const detail = sanitizeTerminalText(record.detail ?? record.tool?.output ?? "");
	const lines = detail ? wrapDisplay(detail, Math.max(8, width - 8)) : [];
	const output: RenderRow[] = [
		row(
			{ text: `${marker} `, tone, bold: true },
			{ text: "Subagent ", tone: "muted" },
			{ text: title, tone: "primary", bold: true },
			{ text: ` · ${state}`, tone: "faint", dim: true },
		),
	];
	if (lines.length)
		output.push(
			...renderExpandableOutput(lines, { expanded: record.expanded, indent: "    ", tone: "muted", previewLines: 4 }),
		);
	return output;
}
