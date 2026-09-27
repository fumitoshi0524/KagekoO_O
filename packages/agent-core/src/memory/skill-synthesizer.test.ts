import * as fs from "node:fs/promises";
import * as os from "node:os";
import * as path from "node:path";
import { describe, expect, it, vi } from "vitest";
import { parseSkillFromFile } from "../capabilities/skills/skill-loader.js";
import { SkillSynthesizer } from "./skill-synthesizer.js";
import type { SessionEvent } from "./types.js";

describe("SkillSynthesizer", () => {
	it("asks the resident learner for a transferable and production-safe workflow", async () => {
		const chat = vi.fn().mockResolvedValue({
			content: [
				"name: stateful-tool-workflow",
				"description: Coordinate stateful tool workflows with safe verification and recovery.",
				"---",
				"Inspect the advertised schema or contract. Preserve returned identifiers and follow dependency order. Recover from errors without repeating successful side effects, then verify final state and postconditions.",
			].join("\n"),
			toolCalls: [],
			finishReason: "stop",
			usage: { promptTokens: 1, completionTokens: 1 },
		});
		const synthesizer = new SkillSynthesizer({
			cwd: "C:\\fixture",
			autoSkillDir: "C:\\fixture\\skills",
			llm: { chat } as never,
		});

		const result = await synthesizer.synthesize([
			{ type: "user.prompt", data: { content: "Coordinate several dependent tools." } } as SessionEvent,
		]);

		expect(result?.name).toBe("stateful-tool-workflow");
		const prompt = chat.mock.calls[0]?.[0].messages[0].content as string;
		expect(prompt).toContain("Generalize across the observed tasks, tools, providers, and entity names");
		expect(prompt).toContain("inspect the advertised tool schemas or contracts");
		expect(prompt).toContain("preserve every returned identifier, URI, or handle");
		expect(prompt).toContain("dependency order");
		expect(prompt).toContain("rejected operations and errors");
		expect(prompt).toContain("verify the final state or postconditions");
	});

	it("persists and reloads the completed-turn watermark for resumed learners", async () => {
		const root = await fs.mkdtemp(path.join(os.tmpdir(), "kageko-skill-watermark-"));
		try {
			const synthesizer = new SkillSynthesizer({ cwd: root, autoSkillDir: root });
			const file = await synthesizer.writeSkill({
				name: "durable-workflow",
				description: "Reuse a durable workflow after enough additional completed turns.",
				instructions:
					"Inspect the contract, preserve identifiers, follow dependency order, recover bounded errors, and verify final postconditions.",
				learnedThroughTurns: 7,
			});
			const loaded = await parseSkillFromFile(file, "auto");
			expect(loaded.metadata.learnedThroughTurns).toBe(7);
		} finally {
			await fs.rm(root, { recursive: true, force: true });
		}
	});
});
