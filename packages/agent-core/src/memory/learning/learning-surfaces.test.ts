import { describe, expect, it, vi } from "vitest";
import { reviewPendingTool } from "../../tools/builtins/review-pending.js";
import { generateSkillTool } from "../../tools/builtins/memory/generate-skill.js";
import { assessCapabilityValue } from "./capability-value-policy.js";
import { CapabilityGapLearner } from "./learners/capability-gap.js";

describe("resident learning surfaces", () => {
	it("makes review_pending a strongly consistent view of resident work", async () => {
		const order: string[] = [];
		const result = await reviewPendingTool.execute!({ action: "list" }, {
			session: {
				learningBus: { flush: async () => void order.push("bus") },
				learningProcessor: {
					flush: async () => void order.push("processor"),
					listPending: async () => {
						order.push("list");
						return [];
					},
				},
			},
		} as never);

		expect(order).toEqual(["bus", "processor", "list"]);
		expect(result.output).toBe("No pending learning outputs.");
	});

	it("hot-loads a directly generated skill for same-session use", async () => {
		const register = vi.fn();
		const loaded = {
			name: "workflow-check",
			description: "Verify a completed workflow",
			path: "C:\\fixture\\SKILL.md",
			dir: "C:\\fixture",
			content: "Inspect and verify the final state.",
			source: "auto",
			metadata: { type: "prompt" },
		};
		const result = await generateSkillTool.execute!({ name: "workflow-check" }, {
			session: {
				recordStore: { load: async () => [{ type: "turn.end", data: { result: {} } }] },
				memory: {
					generateSkill: async () => ({
						name: loaded.name,
						description: loaded.description,
						instructions: loaded.content,
						filePath: loaded.path,
					}),
				},
				skills: { registerSkill: async () => loaded },
				registry: { register },
			},
		} as never);

		expect(result.isError).not.toBe(true);
		expect(register).toHaveBeenCalledOnce();
		expect(register.mock.calls[0]?.[0].name).toBe("skill_workflow-check");
	});

	it("does not let the agent blindly approve an executable capability", async () => {
		const approvePending = vi.fn();
		const result = await reviewPendingTool.execute!({ action: "approve", id: "gap-1" }, {
			session: {
				learningBus: { flush: async () => {} },
				learningProcessor: {
					flush: async () => {},
					listPending: async () => [
						{
							event: { id: "gap-1" },
							decision: { action: "pending", target: "capability_gap" },
							output: { kind: "tool", name: "create_workflow" },
						},
					],
					approvePending,
				},
			},
		} as never);

		expect(result.isError).toBe(true);
		expect(result.output).toContain("external validation/user approval surface");
		expect(approvePending).not.toHaveBeenCalled();
	});

	it("does not treat a prompt skill as satisfying an executable gap", () => {
		const decision = assessCapabilityValue(
			"Create deterministic workflow definitions",
			{
				scope: "workflow",
				futureTasks: ["Create a daily workflow definition", "Create a monthly workflow definition"],
				alternativesChecked: ["Checked all loaded capabilities"],
			},
			[
				{
					name: "workflow-definitions",
					description: "Create deterministic workflow definitions",
					executable: false,
				},
			],
		);

		expect(decision.accepted).toBe(true);
	});

	it("keeps a bounded pending audit record when synthesis is rejected", async () => {
		const learner = new CapabilityGapLearner({
			synthesizer: {
				synthesize: async () => {
					throw new Error("manifest kind mcp does not match required kind tool");
				},
			} as never,
		});

		const output = await learner.handle({
			id: "gap-1",
			source: "capability_gap",
			timestamp: 1,
			payload: { description: "Create one local workflow", proposedKind: "tool" },
		} as never);

		expect(output?.kind).toBe("none");
		expect(output?.status).toBe("failed");
		expect(output?.failure).toContain("manifest kind mcp");
	});

	it("keeps a pending audit record when synthesis declines with kind none", async () => {
		const learner = new CapabilityGapLearner({
			synthesizer: { synthesize: async () => undefined } as never,
		});

		const output = await learner.handle({
			id: "gap-none",
			source: "capability_gap",
			timestamp: 1,
			payload: { description: "Create a reusable stateful service", proposedKind: "mcp" },
		} as never);

		expect(output?.kind).toBe("none");
		expect(output?.status).toBe("failed");
		expect(output?.failure).toContain("no safe reusable capability");
	});

	it("forwards structured required contracts from the event payload to the synthesizer", async () => {
		const synthesize = vi.fn().mockResolvedValue(undefined);
		const learner = new CapabilityGapLearner({ synthesizer: { synthesize } as never });
		const requiredContracts = [
			{ name: "exact_tool", inputSchema: { type: "object", properties: { value: { type: "string" } } } },
		];

		await learner.handle({
			id: "gap-contracts",
			source: "capability_gap",
			timestamp: 1,
			payload: { description: "Provide exact_tool.", proposedKind: "tool", requiredContracts },
		} as never);

		expect(synthesize).toHaveBeenCalledOnce();
		expect(synthesize.mock.calls[0]?.[0].requiredContracts).toEqual(requiredContracts);
	});

	it("suppresses semantically overlapping capability requests in one session", async () => {
		const synthesize = vi.fn().mockResolvedValue({
			manifest: {
				kind: "tool",
				name: "create-workflow",
				description: "Create deterministic local workflow definitions",
				parameters: { type: "object", properties: {} },
				command: "node",
				args: [],
			},
			code: "process.stdout.write('{}')",
		});
		const learner = new CapabilityGapLearner({ synthesizer: { synthesize } as never });
		const first = {
			id: "gap-1",
			source: "capability_gap",
			timestamp: 1,
			payload: {
				description: "Create deterministic local create_workflow definitions with nodes and connections",
				proposedKind: "tool",
			},
		};
		const duplicate = {
			...first,
			id: "gap-2",
			payload: {
				description: "Provide an offline implementation of create_workflow for structured graph specifications",
				proposedKind: "mcp",
			},
		};

		expect(await learner.handle(first as never)).toBeDefined();
		expect(await learner.handle(duplicate as never)).toBeUndefined();
		expect(synthesize).toHaveBeenCalledTimes(1);
	});
});
