import { describe, expect, it } from "vitest";
import { createSkillTool } from "./skill-loader.js";

describe("createSkillTool", () => {
	it("advertises a Skill as instruction loading rather than direct execution", () => {
		const tool = createSkillTool({ name: "artifact-workflow", description: "Use for artifact delivery workflows." });
		expect(tool.name).toBe("skill_artifact-workflow");
		expect(tool.description).toContain("invoke before task operations");
		expect(tool.description).toContain("returns instructions rather than performing the task");
		expect(tool.description).toContain("Use for artifact delivery workflows.");
	});
});
