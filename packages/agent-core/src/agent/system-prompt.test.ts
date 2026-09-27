import { describe, expect, it } from "vitest";
import { buildCapabilityUseInstructions } from "./system-prompt.js";

describe("buildCapabilityUseInstructions", () => {
	it("requires observable-state planning, returned-value propagation, and changed recovery", () => {
		const prompt = buildCapabilityUseInstructions(["create_file", "create_draft"]).join("\n");
		expect(prompt).toContain("observable state");
		expect(prompt).toContain("reuse an operation");
		expect(prompt).toContain("returned by successful tools");
		expect(prompt).toContain("Never repeat an identical failed call");
	});

	it("draws the capability-gap boundary only when the tool is available", () => {
		const ordinary = buildCapabilityUseInstructions(["create_file"]).join("\n");
		expect(ordinary).not.toContain("Use need_capability");

		const learning = buildCapabilityUseInstructions(["create_file", "need_capability"]).join("\n");
		expect(learning).toContain("inspecting every relevant available tool schema");
		expect(learning).toContain("one failed mapping");
		expect(learning).toContain("is not a capability gap");
	});

	it("advertises learned Skill selection only when generated Skills are loaded", () => {
		expect(buildCapabilityUseInstructions(["create_file"]).join("\n")).not.toContain("skill_* tools");
		expect(buildCapabilityUseInstructions(["skill_artifact_workflow"]).join("\n")).toContain(
			"single best-matching skill",
		);
	});
});
