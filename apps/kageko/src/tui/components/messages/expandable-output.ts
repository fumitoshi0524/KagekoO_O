import { row, type RenderRow } from "@kageko/tui-kit";

export interface ExpandableOutputOptions {
	readonly expanded?: boolean;
	readonly previewLines?: number;
	readonly indent?: string;
	readonly tone?: "default" | "muted" | "faint" | "danger" | "code";
	readonly hint?: string;
}

/**
 * Render a stable preview of a potentially large output. The footer is part
 * of the block, so expanding it only changes the block's own rows and never
 * changes the surrounding header layout.
 */
export function renderExpandableOutput(
	lines: readonly string[],
	options: ExpandableOutputOptions = {},
): readonly RenderRow[] {
	const indent = options.indent ?? "    ";
	const visible = options.expanded ? lines : lines.slice(0, Math.max(0, options.previewLines ?? 5));
	const tone = options.tone ?? "muted";
	const output = visible.map((line) => row({ text: indent, tone: "muted" }, { text: line, tone }));
	if (!options.expanded && lines.length > visible.length) {
		const hint = options.hint ?? "ctrl+o to expand";
		output.push(
			row({
				text: `${indent}... ${lines.length - visible.length} more lines, ${hint}`,
				tone: "faint",
				dim: true,
			}),
		);
	}
	return output;
}
