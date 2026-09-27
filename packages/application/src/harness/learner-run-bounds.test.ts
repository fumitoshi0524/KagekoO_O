import { describe, expect, it } from "vitest";
import { learnerRunBoundsFromRoute } from "./composition-root.js";

describe("learnerRunBoundsFromRoute", () => {
	it("returns no overrides when the learner route is absent", () => {
		expect(learnerRunBoundsFromRoute(undefined)).toEqual({});
	});

	it("returns no overrides for a route-only learner config, preserving runner defaults", () => {
		expect(learnerRunBoundsFromRoute({ provider: "openai", modelName: "gpt-5" })).toEqual({});
	});

	it("maps configured run parameters onto runner options, renaming runTimeoutMs to timeoutMs", () => {
		expect(
			learnerRunBoundsFromRoute({
				provider: "openai",
				modelName: "gpt-5",
				maxSteps: 10,
				runTimeoutMs: 120_000,
				maxQueuedRuns: 2,
			}),
		).toEqual({ maxSteps: 10, timeoutMs: 120_000, maxQueuedRuns: 2 });
	});

	it("carries only the configured parameters", () => {
		expect(learnerRunBoundsFromRoute({ runTimeoutMs: 600_000 })).toEqual({ timeoutMs: 600_000 });
	});
});
