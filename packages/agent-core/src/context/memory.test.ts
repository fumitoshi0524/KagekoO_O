import { describe, expect, it } from "vitest";
import {
	ContextMemory,
	DEFAULT_COMPACTION_INPUT_RATIO,
	DEFAULT_COMPACTION_MIN_HISTORY_EVENTS,
	DEFAULT_COMPACTION_TARGET_RATIO,
	DEFAULT_COMPACT_THRESHOLD,
} from "./memory.js";

describe("ContextMemory compaction options", () => {
	it("keeps the exported defaults when no options are passed", () => {
		const memory = new ContextMemory();
		expect(memory.compactThreshold).toBe(DEFAULT_COMPACT_THRESHOLD);
		expect(memory.compactionTargetRatio).toBe(DEFAULT_COMPACTION_TARGET_RATIO);
		expect(memory.compactionInputRatio).toBe(DEFAULT_COMPACTION_INPUT_RATIO);
		expect(memory.minHistoryEvents).toBe(DEFAULT_COMPACTION_MIN_HISTORY_EVENTS);
		expect(DEFAULT_COMPACT_THRESHOLD).toBe(0.8);
		expect(DEFAULT_COMPACTION_TARGET_RATIO).toBe(0.5);
		expect(DEFAULT_COMPACTION_INPUT_RATIO).toBe(0.6);
		expect(DEFAULT_COMPACTION_MIN_HISTORY_EVENTS).toBe(4);
	});

	it("honors a configured threshold in the budget", () => {
		const memory = new ContextMemory({ maxContextSize: 1000, compactThreshold: 0.5 });
		expect(memory.budget().threshold).toBe(500);
	});

	it("gates automatic compaction on the configured minimum history length", async () => {
		// 3 events over the threshold: below the default minimum of 4.
		const memory = new ContextMemory({ maxContextSize: 100, compactThreshold: 0.1 });
		memory.appendUser("x".repeat(200));
		memory.appendAssistant("y".repeat(200));
		memory.appendUser("z".repeat(200));
		const skipped = await memory.maybeCompact();
		expect(skipped.outcome).toBe("skipped");
		expect(skipped.reason).toBe("below_threshold");

		const eager = new ContextMemory({ maxContextSize: 100, compactThreshold: 0.1, minHistoryEvents: 2 });
		eager.appendUser("x".repeat(200));
		eager.appendAssistant("y".repeat(200));
		eager.appendUser("z".repeat(200));
		const compacted = await eager.maybeCompact();
		expect(compacted.outcome).toBe("compacted");
	});
});
