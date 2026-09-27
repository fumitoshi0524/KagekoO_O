import { describe, expect, it } from "vitest";
import { wrapRenderRows } from "@kageko/tui-kit";
import type { TranscriptRecord } from "../src/tui/types.js";
import {
	transcriptLines,
	transcriptPhysicalRowCount,
	transcriptPhysicalSlice,
} from "../src/tui/views/transcript-view.js";

function userRecord(id: string, text: string): TranscriptRecord {
	return { id, kind: "user", text };
}

describe("transcript physical window", () => {
	it("matches full transcript wrapping at the tail and at scrolled offsets", () => {
		const records = Array.from({ length: 18 }, (_, index) =>
			userRecord(`user-${index}`, `record ${index}: ${"wrapped text ".repeat((index % 4) + 1)}`),
		);
		const columns = 19;
		const complete = wrapRenderRows(transcriptLines(records, columns), columns);

		expect(transcriptPhysicalRowCount(records, columns)).toBe(complete.length);
		for (const offset of [0, 1, 4, 13, complete.length - 1, complete.length]) {
			const visibleRows = 7;
			const end = Math.max(0, complete.length - offset);
			const start = Math.max(0, end - visibleRows);
			expect(transcriptPhysicalSlice(records, columns, offset, visibleRows).lines).toEqual(complete.slice(start, end));
		}
	});

	it("reuses rendered rows for unchanged records after a streaming update", () => {
		const records = [userRecord("first", "unchanged first record"), userRecord("last", "streaming")];
		const columns = 24;
		const initialTotal = transcriptPhysicalRowCount(records, columns);
		const initialFirstRow = transcriptPhysicalSlice(records, columns, initialTotal - 1, 1).lines[0];
		const updated = [records[0]!, { ...records[1]!, text: "streaming response grew" }];
		const updatedTotal = transcriptPhysicalRowCount(updated, columns);
		const updatedFirstRow = transcriptPhysicalSlice(updated, columns, updatedTotal - 1, 1).lines[0];

		expect(updatedFirstRow).toBe(initialFirstRow);
	});
});
