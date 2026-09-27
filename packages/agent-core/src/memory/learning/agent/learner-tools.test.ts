import { describe, expect, it, vi } from "vitest";
import { createLearnerTools, type LearnerCapabilityProposal, type LearnerToolsDeps } from "./learner-tools.js";
import type { SessionEvent, SynthesizedSkill } from "../../types.js";
import type { Tool, ToolResult } from "../../../tools/types.js";

const VALID_INSTRUCTIONS =
	"Inspect the advertised tool schemas before choosing operations, preserve every returned identifier, " +
	"execute dependencies in order, and verify final postconditions with authoritative read-back.";
const VALID_DESCRIPTION = "Reuse a verified stateful workflow safely across tasks.";

function makeDeps(overrides: Partial<LearnerToolsDeps> = {}): LearnerToolsDeps {
	return {
		recordStore: {
			load: async () =>
				[
					{ type: "usage.updated", data: { promptTokens: 1 } },
					{ type: "user.prompt", data: { content: "do the task" } },
					{ type: "turn.end", data: { turnId: "turn-1" } },
				] as unknown as SessionEvent[],
		},
		inventory: () => [],
		errorPatterns: () => [{ title: "Recurring error from bash", tags: ["error-pattern", "bash"] }],
		submitSkillProposal: async () => ({ accepted: true, status: "pending" }),
		submitCapabilityProposal: async () => ({ accepted: true, status: "pending", name: "submitted" }),
		...overrides,
	};
}

function toolByName(tools: Tool[], name: string): Tool {
	const tool = tools.find((candidate) => candidate.name === name);
	if (!tool) throw new Error(`tool ${name} not found`);
	return tool;
}

describe("createLearnerTools", () => {
	it("exposes the five learner tools with builtin-compatible plain names", () => {
		const tools = createLearnerTools(makeDeps());
		expect(tools.map((tool) => tool.name)).toEqual([
			"read_recent_events",
			"inspect_inventory",
			"read_error_patterns",
			"propose_skill",
			"propose_capability",
		]);
	});

	it("removes disabled proposal products from the learner tool surface", () => {
		expect(createLearnerTools(makeDeps({ proposalKinds: [] })).map((tool) => tool.name)).toEqual([
			"read_recent_events",
			"inspect_inventory",
			"read_error_patterns",
		]);
		const toolOnly = createLearnerTools(makeDeps({ proposalKinds: ["tool"] }));
		expect(toolOnly.map((tool) => tool.name)).toEqual([
			"read_recent_events",
			"inspect_inventory",
			"read_error_patterns",
			"propose_capability",
		]);
		const parameters = toolByName(toolOnly, "propose_capability").parameters as {
			properties?: { proposedKind?: { enum?: string[] } };
		};
		expect(parameters.properties?.proposedKind?.enum).toEqual(["tool"]);
	});

	it("declares noAccess for read tools and learning-queue mutation for proposals", () => {
		const tools = createLearnerTools(makeDeps());
		for (const name of ["read_recent_events", "inspect_inventory", "read_error_patterns"]) {
			expect(toolByName(tools, name).resolveExecution?.({}).accesses).toEqual([{ kind: "none" }]);
		}
		for (const name of ["propose_skill", "propose_capability"]) {
			expect(toolByName(tools, name).resolveExecution?.({}).accesses).toEqual([
				{ kind: "durable_state", operation: "mutate", target: "learning_queue" },
			]);
		}
	});

	it("read_recent_events returns the trimmed evidence window", async () => {
		const tools = createLearnerTools(makeDeps());
		const result = await toolByName(tools, "read_recent_events").execute!({}, {});
		const events = result.output as SessionEvent[];
		expect(events.map((event) => event.type)).toEqual(["user.prompt", "turn.end"]);
	});

	it("inspect_inventory returns the current inventory", async () => {
		const inventory = [{ name: "read", description: "Read files", executable: true }];
		const tools = createLearnerTools(makeDeps({ inventory: () => inventory }));
		const result = await toolByName(tools, "inspect_inventory").execute!({}, {});
		expect(result.output).toEqual(inventory);
	});

	it("read_error_patterns returns the recorded patterns", async () => {
		const tools = createLearnerTools(makeDeps());
		const result = (await toolByName(tools, "read_error_patterns").execute!({}, {})) as ToolResult;
		expect(result.output).toEqual([{ title: "Recurring error from bash", tags: ["error-pattern", "bash"] }]);
	});

	it("propose_skill rejects a duplicate as a normal result without submitting", async () => {
		const submitSkillProposal = vi.fn();
		const tools = createLearnerTools(
			makeDeps({
				inventory: () => [{ name: "existing-workflow", description: "Already present.", executable: false }],
				submitSkillProposal,
			}),
		);
		const result = await toolByName(tools, "propose_skill").execute!(
			{ name: "existing-workflow", description: VALID_DESCRIPTION, instructions: VALID_INSTRUCTIONS },
			{},
		);
		expect(result.isError).not.toBe(true);
		expect(String(result.output)).toContain("rejected");
		expect(submitSkillProposal).not.toHaveBeenCalled();
	});

	it("propose_skill submits the sanitized skill once on acceptance", async () => {
		const submitSkillProposal = vi.fn().mockResolvedValue({ accepted: true, status: "pending" });
		const tools = createLearnerTools(makeDeps({ submitSkillProposal }));
		const result = await toolByName(tools, "propose_skill").execute!(
			{ name: "My Cool Skill", description: VALID_DESCRIPTION, instructions: VALID_INSTRUCTIONS },
			{},
		);
		expect(result.isError).not.toBe(true);
		expect(submitSkillProposal).toHaveBeenCalledOnce();
		const skill = submitSkillProposal.mock.calls[0]?.[0] as SynthesizedSkill;
		expect(skill).toEqual({ name: "my-cool-skill", description: VALID_DESCRIPTION, instructions: VALID_INSTRUCTIONS });
		expect(String(result.output)).toContain("pending");
	});

	it("propose_skill surfaces a sink rejection as a normal result", async () => {
		const tools = createLearnerTools(
			makeDeps({ submitSkillProposal: async () => ({ accepted: false, reason: "queue is full" }) }),
		);
		const result = await toolByName(tools, "propose_skill").execute!(
			{ name: "novel-skill", description: VALID_DESCRIPTION, instructions: VALID_INSTRUCTIONS },
			{},
		);
		expect(result.isError).not.toBe(true);
		expect(String(result.output)).toContain("queue is full");
	});

	it("propose_capability without an inline candidate forwards description/context/contracts only", async () => {
		const submitCapabilityProposal = vi.fn().mockResolvedValue({ accepted: true, status: "pending" });
		const tools = createLearnerTools(makeDeps({ submitCapabilityProposal }));
		const result = await toolByName(tools, "propose_capability").execute!(
			{
				description: "Create deterministic workflow definitions",
				context: "yaml workflows",
				proposedKind: "tool",
				requiredContracts: [
					{ name: "create_workflow", input_schema: { type: "object" } },
					{ name: "broken-entry" },
					"not-an-object",
				],
			},
			{},
		);
		expect(result.isError).not.toBe(true);
		expect(submitCapabilityProposal).toHaveBeenCalledOnce();
		const submitted = submitCapabilityProposal.mock.calls[0]?.[0] as LearnerCapabilityProposal;
		expect("candidate" in submitted).toBe(false);
		expect(submitted.description).toBe("Create deterministic workflow definitions");
		expect(submitted.context).toBe("yaml workflows");
		// input_schema alias normalized; malformed entries dropped.
		expect(submitted.requiredContracts).toEqual([{ name: "create_workflow", inputSchema: { type: "object" } }]);
	});

	it("propose_capability with an inline candidate validates then submits it", async () => {
		const submitCapabilityProposal = vi
			.fn()
			.mockResolvedValue({ accepted: true, status: "approved", name: "read-file" });
		const tools = createLearnerTools(makeDeps({ submitCapabilityProposal }));
		const result = await toolByName(tools, "propose_capability").execute!(
			{
				description: "Read a UTF-8 file from the workspace.",
				proposedKind: "tool",
				name: "Read File",
				parameters: { type: "object", properties: { file: { type: "string" } } },
				command: "node",
				args: ["{{__args_json}}"],
				code: "process.stdout.write('ok');",
			},
			{},
		);
		expect(result.isError).not.toBe(true);
		expect(submitCapabilityProposal).toHaveBeenCalledOnce();
		const submitted = submitCapabilityProposal.mock.calls[0]?.[0] as LearnerCapabilityProposal;
		expect(submitted.candidate?.name).toBe("read-file");
		expect(submitted.candidate?.kind).toBe("tool");
		expect(String(result.output)).toContain("approved");
	});

	it("propose_capability rejects an invalid inline candidate without submitting", async () => {
		const submitCapabilityProposal = vi.fn();
		const tools = createLearnerTools(makeDeps({ submitCapabilityProposal }));
		const result = await toolByName(tools, "propose_capability").execute!(
			{
				description: "Read a UTF-8 file from the workspace.",
				proposedKind: "tool",
				name: "read-file",
				parameters: { type: "object" },
				command: "node",
				args: ["--file"],
				code: "process.stdout.write('ok');",
			},
			{},
		);
		expect(result.isError).not.toBe(true);
		expect(String(result.output)).toContain("rejected");
		expect(submitCapabilityProposal).not.toHaveBeenCalled();
	});

	it("propose_capability rejects a missing description as a normal result", async () => {
		const tools = createLearnerTools(makeDeps());
		const result = await toolByName(tools, "propose_capability").execute!({}, {});
		expect(result.isError).not.toBe(true);
		expect(String(result.output)).toContain("description is required");
	});
});
