import { describe, expect, it } from "vitest";
import { buildRuntimeSystemPrompt } from "./composition-root.js";

describe("buildRuntimeSystemPrompt", () => {
	it("directs the coordinator to use a declared worker for independent work", async () => {
		const prompt = await buildRuntimeSystemPrompt(
			{ list: () => [{ name: "agent" }, { name: "agent_swarm" }] },
			{ profileSystemPrompt: async () => "" } as never,
			new Map([
				[
					"release-review",
					{ id: "release-review", whenToUse: "Review a release change independently." } as never,
				],
			]),
		);

		expect(prompt).toContain("Do not make the coordinator re-discover independent evidence");
		expect(prompt).toContain("declared specialist profile (including a user-defined one)");
		expect(prompt).toContain("release-review: Review a release change independently.");
		expect(prompt).toContain("before carrying out dependent UI mutations");
	});
});
