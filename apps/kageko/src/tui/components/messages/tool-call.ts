import {
	row,
	sanitizeTerminalText,
	truncateDisplay,
	wrapDisplay,
	type RenderRow,
	type RenderSpan,
} from "@kageko/tui-kit";
import type { TranscriptRecord } from "../../types.js";
import { renderCodePreview, langFromPath } from "../media/code-highlight.js";
import { renderDiffPreview, renderUnifiedDiffPreview } from "../media/diff-preview.js";
import { renderExpandableOutput } from "./expandable-output.js";
import { renderPlanBox } from "./plan-box.js";
import { renderSubagentCard } from "./subagent-card.js";

type RichTool = NonNullable<TranscriptRecord["tool"]> & {
	readonly path?: string;
	readonly filePath?: string;
	readonly language?: string;
	readonly oldText?: string;
	readonly newText?: string;
};

export interface ToolCallRenderOptions {
	readonly spinnerFrame?: string;
	readonly previewLines?: number;
}

function keyArgument(raw: string | undefined): string {
	if (!raw) return "";
	try {
		const parsed: unknown = JSON.parse(raw);
		if (typeof parsed !== "object" || parsed === null) return raw;
		const preferred = ["path", "file_path", "command", "description", "query", "pattern"];
		const object = parsed as Record<string, unknown>;
		for (const key of preferred) if (typeof object[key] === "string") return object[key] as string;
		const first = Object.values(object).find((value) => typeof value === "string");
		return typeof first === "string" ? first : raw;
	} catch {
		return raw;
	}
}

function summaryChip(state: TranscriptRecord["state"], output: string | undefined): string {
	if ((state !== "success" && state !== "failed") || !output) return "";
	const lines = output.split("\n");
	const added = lines.filter((line) => line.startsWith("+") && !line.startsWith("++")).length;
	const removed = lines.filter((line) => line.startsWith("-") && !line.startsWith("--")).length;
	return added + removed > 0 ? ` · +${added} −${removed}` : ` · ${lines.length} lines`;
}

function presentation(tool: RichTool, output: string): RichTool["presentation"] {
	if (tool.presentation) return tool.presentation;
	const value = `${tool.name}\n${output}`.toLowerCase();
	if (value.includes("diff") || output.includes("@@") || (output.includes("+") && output.includes("-"))) return "diff";
	if (value.includes("plan")) return "plan";
	if (value.includes("subagent") || value.includes("agent")) return "subagent";
	if (value.includes("code") || output.includes("```")) return "code";
	return "text";
}

function header(record: TranscriptRecord, tool: RichTool, width: number, spinnerFrame: string): RenderRow {
	const failed = record.state === "failed";
	const bullet: RenderSpan = failed
		? { text: "✗ ", tone: "danger", bold: true }
		: record.state === "success"
			? { text: "● ", tone: "success" }
			: record.streaming
				? { text: `${spinnerFrame} `, tone: "primary" }
				: { text: "● ", tone: "default" };
	const verb = record.streaming ? "Calling " : "Using ";
	const spans: RenderSpan[] = [bullet, { text: verb, tone: "muted" }, { text: tool.name, tone: "primary", bold: true }];
	const arg = keyArgument(tool.arguments) || tool.progress || "";
	if (arg)
		spans.push({
			text: ` (${truncateDisplay(arg, Math.max(8, width - tool.name.length - verb.length - 8))})`,
			tone: "muted",
			dim: true,
		});
	const chip = summaryChip(record.state, tool.output);
	if (chip) spans.push({ text: chip, tone: "faint", dim: true });
	return row(...spans);
}

export function renderToolCall(
	record: TranscriptRecord,
	width: number,
	options: ToolCallRenderOptions = {},
): readonly RenderRow[] {
	const tool = (record.tool ?? { callId: record.id, name: record.text, arguments: record.detail }) as RichTool;
	const spinnerFrame = options.spinnerFrame ?? "◐";
	const output = sanitizeTerminalText(
		tool.error || tool.output || tool.progress || (record.expanded ? record.detail : ""),
	);
	const mode = presentation(tool, output);
	const rows: RenderRow[] = [header(record, tool, width, spinnerFrame)];
	if (!output && record.streaming) return rows;
	if (mode === "plan")
		return [
			...rows,
			...renderPlanBox(output || record.text, width, {
				expanded: record.expanded,
				status: record.state === "running" ? "drafting" : record.state,
			}),
		];
	if (mode === "subagent")
		return [
			...rows,
			...renderSubagentCard({ ...record, text: tool.name, detail: output, tool }, Math.max(8, width - 2)),
		];
	if (mode === "diff") {
		const oldText = tool.oldText;
		const newText = tool.newText;
		if (oldText !== undefined || newText !== undefined)
			return [
				...rows,
				...renderDiffPreview(oldText ?? "", newText ?? "", {
					path: tool.path ?? tool.filePath,
					expanded: record.expanded,
					incomplete: record.streaming,
				}),
			];
		return [
			...rows,
			...renderUnifiedDiffPreview(output, {
				path: tool.path ?? tool.filePath,
				expanded: record.expanded,
				maxLines: options.previewLines ?? 5,
			}),
		];
	}
	if (mode === "code") {
		const fenced = output.match(/^```(?:([^\n]*))\n([\s\S]*?)\n```$/);
		const code = fenced?.[2] ?? output;
		const language = tool.language ?? fenced?.[1] ?? langFromPath(tool.path ?? tool.filePath ?? "");
		return [
			...rows,
			...renderCodePreview(code, width, { language, expanded: record.expanded, maxLines: options.previewLines ?? 5 }),
		];
	}
	const lines = wrapDisplay(output, Math.max(8, width - 4));
	return [
		...rows,
		...renderExpandableOutput(lines, {
			expanded: record.expanded,
			previewLines: options.previewLines ?? 5,
			tone: record.state === "failed" ? "danger" : "muted",
		}),
	];
}
