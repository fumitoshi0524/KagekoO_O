import { type RenderRow, renderMarkdownBlocks, row, wrapDisplay, wrapRenderRows } from "@kageko/tui-kit";
import type { TranscriptRecord } from "../types.js";
import { renderSubagentCard } from "../components/messages/subagent-card.js";
import { renderToolCall } from "../components/messages/tool-call.js";

type TranscriptCache = Map<string, readonly RenderRow[]>;
type RecordCache = Map<string, readonly RenderRow[]>;
const transcriptCache = new WeakMap<readonly TranscriptRecord[], TranscriptCache>();
const recordCache = new WeakMap<TranscriptRecord, RecordCache>();
const recordPhysicalCache = new WeakMap<TranscriptRecord, RecordCache>();
const transcriptSeparator = row();

/** Product blocks, deliberately preserving record identity and tool structure. */
export function transcriptLines(
	records: readonly TranscriptRecord[],
	columns: number,
	spinnerFrame = "◐",
): readonly RenderRow[] {
	if (!records.length) return [];
	const spinnerKey = records.some((record) => record.kind === "thinking" && record.streaming) ? spinnerFrame : "";
	const cacheKey = `${columns}\u0000${spinnerKey}`;
	const cached = transcriptCache.get(records)?.get(cacheKey);
	if (cached) return cached;
	const content = Math.max(8, columns - 2);
	const output: RenderRow[] = [];
	for (const record of records) {
		if (output.length) output.push(row({ text: "" }));
		output.push(...cachedRecordRows(record, content, spinnerFrame));
	}
	let cache = transcriptCache.get(records);
	if (!cache) {
		cache = new Map();
		transcriptCache.set(records, cache);
	}
	cache.set(cacheKey, output);
	return output;
}

/** Materialize the whole transcript only for callers that explicitly need it. */
export function transcriptPhysicalLines(
	records: readonly TranscriptRecord[],
	columns: number,
	spinnerFrame = "◐",
): readonly RenderRow[] {
	return transcriptPhysicalSlice(records, columns, 0, Number.MAX_SAFE_INTEGER, spinnerFrame).lines;
}

export interface TranscriptPhysicalSlice {
	readonly lines: readonly RenderRow[];
	readonly totalRows: number;
}

/**
 * Return only the visible tail window without assembling a second copy of the
 * entire transcript. Unchanged records reuse their physical rows by identity,
 * so a streaming update only lays out the record that changed.
 */
export function transcriptPhysicalSlice(
	records: readonly TranscriptRecord[],
	columns: number,
	scrollOffset: number,
	visibleRows: number,
	spinnerFrame = "◐",
): TranscriptPhysicalSlice {
	if (!records.length) return { lines: [], totalRows: 0 };
	let totalRows = 0;
	let firstRenderedRecord = -1;
	for (let index = 0; index < records.length; index += 1) {
		const physical = cachedRecordPhysicalRows(records[index]!, columns, spinnerFrame);
		totalRows += physical.length;
		if (firstRenderedRecord < 0 && physical.length > 0) firstRenderedRecord = index;
	}
	if (firstRenderedRecord >= 0) totalRows += records.length - firstRenderedRecord - 1;
	const offset = Math.max(0, Math.trunc(scrollOffset));
	const visible = Math.max(0, Math.trunc(visibleRows));
	const end = Math.max(0, totalRows - offset);
	const start = Math.max(0, end - visible);
	if (end <= start) return { lines: [], totalRows };

	const chunks: RenderRow[][] = [];
	let cursor = totalRows;
	for (let index = records.length - 1; index >= 0; index -= 1) {
		const physical = cachedRecordPhysicalRows(records[index]!, columns, spinnerFrame);
		const recordStart = cursor - physical.length;
		const localStart = Math.max(0, start - recordStart);
		const localEnd = Math.min(physical.length, end - recordStart);
		if (localStart < localEnd) chunks.push(physical.slice(localStart, localEnd));
		cursor = recordStart;
		if (index > firstRenderedRecord) {
			cursor -= 1;
			if (cursor >= start && cursor < end) chunks.push([transcriptSeparator]);
		}
	}
	return { lines: chunks.reverse().flat(), totalRows };
}

/** Row count for viewport clamping that never materializes the whole view. */
export function transcriptPhysicalRowCount(
	records: readonly TranscriptRecord[],
	columns: number,
	spinnerFrame = "◐",
): number {
	let totalRows = 0;
	let firstRenderedRecord = -1;
	for (let index = 0; index < records.length; index += 1) {
		const physical = cachedRecordPhysicalRows(records[index]!, columns, spinnerFrame);
		totalRows += physical.length;
		if (firstRenderedRecord < 0 && physical.length > 0) firstRenderedRecord = index;
	}
	return firstRenderedRecord < 0 ? 0 : totalRows + records.length - firstRenderedRecord - 1;
}

function cachedRecordRows(record: TranscriptRecord, width: number, spinnerFrame: string): readonly RenderRow[] {
	const spinnerKey = record.kind === "thinking" && record.streaming ? spinnerFrame : "";
	const cacheKey = `${width}\u0000${spinnerKey}`;
	const cached = recordCache.get(record)?.get(cacheKey);
	if (cached) return cached;
	const rows = recordRows(record, width, spinnerFrame);
	let cache = recordCache.get(record);
	if (!cache) {
		cache = new Map();
		recordCache.set(record, cache);
	}
	cache.set(cacheKey, rows);
	return rows;
}

function cachedRecordPhysicalRows(
	record: TranscriptRecord,
	columns: number,
	spinnerFrame: string,
): readonly RenderRow[] {
	const spinnerKey = record.kind === "thinking" && record.streaming ? spinnerFrame : "";
	const cacheKey = `${columns}\u0000${spinnerKey}`;
	const cached = recordPhysicalCache.get(record)?.get(cacheKey);
	if (cached) return cached;
	const rows = wrapRenderRows(cachedRecordRows(record, Math.max(8, columns - 2), spinnerFrame), columns);
	let cache = recordPhysicalCache.get(record);
	if (!cache) {
		cache = new Map();
		recordPhysicalCache.set(record, cache);
	}
	cache.set(cacheKey, rows);
	return rows;
}

function recordRows(record: TranscriptRecord, width: number, spinnerFrame: string): RenderRow[] {
	if (record.kind === "user") return userRows(record.text, width);
	if (record.kind === "assistant") return assistantRows(record, width);
	if (record.kind === "thinking") return thinkingRows(record, width, spinnerFrame);
	if (record.kind === "tool" || record.kind === "tool-result")
		return [...renderToolCall(record, width, { spinnerFrame })];
	if (record.kind === "subagent") return [...renderSubagentCard(record, width)];
	return statusRows(record, width);
}

function userRows(text: string, width: number): RenderRow[] {
	return wrapDisplay(text || "…", Math.max(1, width - 2)).map((line, index) =>
		index === 0
			? row({ text: "✨ ", tone: "user", bold: true }, { text: line, tone: "user", bold: true })
			: row({ text: "  ", tone: "user" }, { text: line, tone: "user", bold: true }),
	);
}

function assistantRows(record: TranscriptRecord, width: number): RenderRow[] {
	return renderMarkdownBlocks(record.text || (record.streaming ? "…" : ""), Math.max(1, width - 2), {
		tone: "default",
		headingTone: "strong",
		quoteTone: "muted",
		codeTone: "code",
	}).map((entry, index) =>
		index === 0
			? row({ text: "● ", tone: "default" }, ...entry.spans)
			: row({ text: "  ", tone: "default" }, ...entry.spans),
	);
}

function thinkingRows(record: TranscriptRecord, width: number, spinnerFrame: string): RenderRow[] {
	if (record.streaming)
		return [
			row(
				{ text: `${spinnerFrame} `, tone: "primary" },
				{ text: "thinking...", tone: "muted", italic: true, dim: true },
			),
		];
	const wrapped = wrapDisplay(record.text || "Working", Math.max(1, width - 2));
	const visible = record.expanded ? wrapped : wrapped.slice(0, 2);
	const rows = visible.map((line) =>
		row({ text: "  ", tone: "muted" }, { text: line, tone: "muted", italic: true, dim: true }),
	);
	if (!record.expanded && wrapped.length > visible.length)
		rows.push(
			row({
				text: `  (... ${wrapped.length - visible.length} more lines, ctrl+o to expand)`,
				tone: "faint",
				dim: true,
			}),
		);
	return rows;
}

function statusRows(record: TranscriptRecord, width: number): RenderRow[] {
	const marker =
		record.kind === "error"
			? "✗"
			: record.kind === "warning"
				? "!"
				: record.kind === "process"
					? "$"
					: record.kind === "subagent"
						? "+"
						: "·";
	const tone =
		record.kind === "error"
			? ("danger" as const)
			: record.kind === "warning"
				? ("warning" as const)
				: record.kind === "status"
					? ("success" as const)
					: record.kind === "process"
						? ("shell" as const)
						: ("muted" as const);
	return wrapDisplay(record.text || "…", Math.max(1, width - 2)).map((line, index) =>
		index === 0
			? row(
					{ text: `${marker} `, tone, bold: record.kind === "error" || record.kind === "warning" },
					{ text: line, tone },
					...(record.detail ? [{ text: `  ${record.detail}`, tone: "faint" as const, dim: true }] : []),
				)
			: row({ text: "  ", tone }, { text: line, tone }),
	);
}
