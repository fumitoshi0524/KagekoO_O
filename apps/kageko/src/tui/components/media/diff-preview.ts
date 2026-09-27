import { row, sanitizeTerminalText, type RenderRow, type RenderSpan } from "@kageko/tui-kit";
import { renderExpandableOutput } from "../messages/expandable-output.js";

export type DiffLineKind = "context" | "add" | "delete";

export interface DiffLine {
	readonly kind: DiffLineKind;
	readonly lineNum: number;
	readonly code: string;
}

/** A small LCS diff, matching Kimi's edit preview semantics without ANSI strings. */
export function computeDiffLines(
	oldText: string,
	newText: string,
	oldStart = 1,
	newStart = 1,
	isIncomplete = false,
): DiffLine[] {
	const oldLines = oldText ? sanitizeTerminalText(oldText).split("\n") : [];
	const newLines = newText ? sanitizeTerminalText(newText).split("\n") : [];
	const dp = Array.from({ length: oldLines.length + 1 }, () => Array<number>(newLines.length + 1).fill(0));
	for (let i = 1; i <= oldLines.length; i += 1) {
		for (let j = 1; j <= newLines.length; j += 1) {
			dp[i]![j] =
				oldLines[i - 1] === newLines[j - 1] ? dp[i - 1]![j - 1]! + 1 : Math.max(dp[i - 1]![j]!, dp[i]![j - 1]!);
		}
	}
	const reversed: DiffLine[] = [];
	let i = oldLines.length;
	let j = newLines.length;
	while (i > 0 || j > 0) {
		if (i > 0 && j > 0 && oldLines[i - 1] === newLines[j - 1]) {
			reversed.push({ kind: "context", lineNum: newStart + j - 1, code: newLines[j - 1]! });
			i -= 1;
			j -= 1;
		} else if (j > 0 && (i === 0 || dp[i]![j - 1]! >= dp[i - 1]![j]!)) {
			reversed.push({ kind: "add", lineNum: newStart + j - 1, code: newLines[j - 1]! });
			j -= 1;
		} else {
			reversed.push({ kind: "delete", lineNum: oldStart + i - 1, code: oldLines[i - 1]! });
			i -= 1;
		}
	}
	const result = reversed.reverse();
	if (isIncomplete) {
		let last = result.length - 1;
		while (last >= 0 && result[last]!.kind === "delete") last -= 1;
		result.splice(last + 1);
	}
	return result;
}

export interface DiffPreviewOptions {
	readonly expanded?: boolean;
	readonly incomplete?: boolean;
	readonly path?: string;
	readonly maxLines?: number;
}

function diffSpans(line: DiffLine): readonly RenderSpan[] {
	const tone = line.kind === "add" ? "diffAdded" : line.kind === "delete" ? "diffRemoved" : "muted";
	const marker = line.kind === "add" ? "+ " : line.kind === "delete" ? "- " : "  ";
	return [
		{ text: String(line.lineNum).padStart(4, " ") + " ", tone: "diffGutter" },
		{ text: marker + line.code, tone, dim: line.kind === "context" },
	];
}

/** Render structured edits with line gutters, semantic colors, and a capped preview. */
export function renderDiffPreview(
	oldText: string,
	newText: string,
	options: DiffPreviewOptions = {},
): readonly RenderRow[] {
	const lines = computeDiffLines(oldText, newText, 1, 1, options.incomplete ?? false);
	const changed = lines.filter((line) => line.kind !== "context");
	const added = changed.filter((line) => line.kind === "add").length;
	const removed = changed.filter((line) => line.kind === "delete").length;
	const path = options.path ? ` ${options.path}` : "";
	const header: RenderSpan[] = [
		{ text: "    ", tone: "muted" },
		{ text: added ? `+${added} ` : "", tone: "diffAddedStrong", bold: true },
		{ text: removed ? `-${removed} ` : "", tone: "diffRemovedStrong", bold: true },
		{ text: path || "diff", tone: "strong", bold: true },
	];
	const body = lines.map(diffSpans);
	const maxLines = options.maxLines ?? 5;
	const visible = options.expanded ? body : body.slice(0, Math.max(0, maxLines));
	const output: RenderRow[] = [row(...header), ...visible.map((spans) => row(...spans))];
	if (!options.expanded && body.length > visible.length) {
		output.push(
			...renderExpandableOutput([`${body.length - visible.length} more changes hidden`], {
				expanded: false,
				previewLines: 1,
				indent: "    ",
				tone: "faint",
			}),
		);
	}
	return output;
}

/** Render a unified diff already returned by a tool. */
export function renderUnifiedDiffPreview(output: string, options: DiffPreviewOptions = {}): readonly RenderRow[] {
	const lines = sanitizeTerminalText(output).split("\n");
	const added = lines.filter((line) => line.startsWith("+") && !line.startsWith("+++"));
	const removed = lines.filter((line) => line.startsWith("-") && !line.startsWith("---"));
	const body = lines.map((line) => {
		const tone = line.startsWith("+")
			? "diffAdded"
			: line.startsWith("-")
				? "diffRemoved"
				: line.startsWith("@@")
					? "diffMeta"
					: "muted";
		return row({ text: "    ", tone: "muted" }, { text: line, tone, dim: tone === "muted" });
	});
	const visible = options.expanded ? body : body.slice(0, options.maxLines ?? 5);
	const header = row(
		{ text: "    ", tone: "muted" },
		{ text: added.length ? `+${added.length} ` : "", tone: "diffAddedStrong", bold: true },
		{ text: removed.length ? `-${removed.length} ` : "", tone: "diffRemovedStrong", bold: true },
		{ text: options.path ?? "diff", tone: "strong", bold: true },
	);
	return [
		header,
		...visible,
		...(body.length > visible.length && !options.expanded
			? [
					row({
						text: `    ... ${body.length - visible.length} more lines, ctrl+o to expand`,
						tone: "faint",
						dim: true,
					}),
				]
			: []),
	];
}
