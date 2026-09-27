import { describe, expect, it } from "vitest";
import { waitForLearningBounded } from "./composition-root.js";

describe("waitForLearningBounded", () => {
	it("resolves as soon as the drain settles within the window", async () => {
		const started = Date.now();
		await waitForLearningBounded(new Promise<void>((resolve) => setTimeout(resolve, 5)), 5_000);
		expect(Date.now() - started).toBeLessThan(1_000);
	});

	it("resolves without the drain once the window elapses", async () => {
		const started = Date.now();
		// A never-settling drain models a 300s resident learner run; the bounded
		// wait must still release interactive listers promptly.
		await waitForLearningBounded(new Promise<void>(() => {}), 20);
		expect(Date.now() - started).toBeLessThan(1_000);
	});

	it("propagates a drain rejection that lands inside the window", async () => {
		await expect(waitForLearningBounded(Promise.reject(new Error("drain failed")), 5_000)).rejects.toThrow(
			"drain failed",
		);
	});
});
