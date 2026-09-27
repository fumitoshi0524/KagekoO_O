import { describe, expect, it, vi } from "vitest";
import { ErrorPatternLearner } from "./error-pattern.js";

const event = (toolName: string, output: string) =>
	({
		id: `${toolName}-${output}`,
		source: "tool_result",
		timestamp: 1,
		payload: { toolName, result: { output } },
	}) as never;

describe("ErrorPatternLearner", () => {
	it("keeps repeated errors as knowledge without repeatedly waking the resident learner", async () => {
		const onNewPattern = vi.fn();
		const knowledgeStore = { add: vi.fn(async (input) => ({ id: "entry", ...input })) };
		const learner = new ErrorPatternLearner({ knowledgeStore: knowledgeStore as never, onNewPattern });

		await learner.handle(event("bash", "stale browser reference"), { action: "learn" } as never);
		await learner.handle(event("bash", "stale browser reference"), { action: "learn" } as never);

		expect(knowledgeStore.add).toHaveBeenCalledTimes(2);
		expect(onNewPattern).toHaveBeenCalledTimes(1);
	});

	it("notifies the observer once for each distinct error pattern", async () => {
		const onNewPattern = vi.fn();
		const knowledgeStore = { add: vi.fn(async (input) => ({ id: "entry", ...input })) };
		const learner = new ErrorPatternLearner({ knowledgeStore: knowledgeStore as never, onNewPattern });

		await learner.handle(event("bash", "first failure"), { action: "learn" } as never);
		await learner.handle(event("bash", "second failure"), { action: "learn" } as never);

		expect(knowledgeStore.add).toHaveBeenCalledTimes(2);
		expect(onNewPattern).toHaveBeenCalledTimes(2);
	});
});
