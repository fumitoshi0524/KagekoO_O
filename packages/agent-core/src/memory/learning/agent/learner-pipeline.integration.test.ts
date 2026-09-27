import * as fs from "node:fs/promises";
import * as os from "node:os";
import * as path from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";
import { LearnerAgentBridge } from "./learner-bridge.js";
import { LearnerAgentRunner } from "./learner-agent.js";
import { SkillLearner } from "../learners/skill.js";
import { CapabilityGapLearner } from "../learners/capability-gap.js";
import { LearningProcessor } from "../processor.js";
import { LearningBus } from "../bus.js";
import { LearningTriage } from "../triage.js";
import { LearningTriggers } from "./triggers.js";
import { CapabilitySynthesizer } from "../../capability-synthesizer.js";
import { PermissionManager } from "../../../permissions/index.js";
import type { AgentLlm } from "../../../turn/turn-runner.js";
import type { ChatResponse } from "../../../ports/llm.js";
import type { LearningEvent } from "../event.js";
import type { SessionEvent } from "../../types.js";

const USAGE = { promptTokens: 1, completionTokens: 1 };
const GAP_DESCRIPTION = "Create normalized workflow definitions as one reusable local tool";

const tempDirs: string[] = [];
afterEach(async () => {
	await Promise.all(tempDirs.splice(0).map((dir) => fs.rm(dir, { recursive: true, force: true })));
});

async function tempDir(): Promise<string> {
	const dir = await fs.mkdtemp(path.join(os.tmpdir(), "kageko-learner-pipeline-"));
	tempDirs.push(dir);
	return dir;
}

/**
 * Scripted provider: the learner conversation (carrying the five learner
 * tools) answers with a description-only propose_capability call, then ends;
 * the capability synthesizer (no tools) answers with the manifest JSON. This
 * mirrors the benchmark scripted-provider mocks.
 */
function scriptedLlm(): { llm: AgentLlm; requests: Array<{ tools: string[]; userText: string }> } {
	const requests: Array<{ tools: string[]; userText: string }> = [];
	const llm: AgentLlm = {
		chat: async (options) => {
			const tools = (options.tools ?? []).map((tool) => tool.function.name);
			const latestUser = [...options.messages].reverse().find((message) => message.role === "user");
			requests.push({
				tools,
				userText: typeof latestUser?.content === "string" ? latestUser.content : "",
			});
			if (tools.includes("propose_capability")) {
				const hasToolResult = options.messages.some((message) => message.role === "tool");
				if (!hasToolResult) {
					return {
						content: "",
						toolCalls: [
							{
								id: "learner-call-1",
								name: "propose_capability",
								arguments: { description: GAP_DESCRIPTION, proposedKind: "tool" },
							},
						],
						finishReason: "tool_calls",
						usage: USAGE,
					} satisfies ChatResponse;
				}
				return { content: "Proposal submitted.", toolCalls: [], finishReason: "stop", usage: USAGE };
			}
			// The resident capability synthesizer path (no tools offered).
			return {
				content: JSON.stringify({
					manifest: {
						kind: "tool",
						name: "create-workflow",
						description: "Create and configure normalized workflow definitions programmatically.",
						parameters: {
							type: "object",
							properties: { nodes: { type: "array" } },
							required: ["nodes"],
						},
						command: "node",
						args: ["{{__args_json}}"],
					},
					code: "const { nodes } = JSON.parse(process.argv[2]); process.stdout.write(JSON.stringify({ nodes }));",
				}),
				toolCalls: [],
				finishReason: "stop",
				usage: USAGE,
			};
		},
	};
	return { llm, requests };
}

describe("learner pipeline integration (capability_gap → agent run → pending queue)", () => {
	it("produces a pending entry with the exact legacy shape, isolated from the main journal", async () => {
		const root = await tempDir();
		const { llm, requests } = scriptedLlm();

		const mainJournalEvents: SessionEvent[] = [
			{ type: "user.prompt", data: { content: "Please make workflow generation reusable." } },
			{ type: "tool.call", data: { call: { id: "c1", name: "bash", arguments: { command: "ls" } } } },
			{ type: "turn.end", data: { turnId: "turn-1" } },
		] as unknown as SessionEvent[];
		// The main journal is read-only evidence for the learner; its append
		// channel must never see learner-run events.
		const mainJournalAppend = vi.fn();
		const journal = {
			load: async () => mainJournalEvents,
			append: mainJournalAppend,
		};

		const bus = new LearningBus({ learningDir: path.join(root, "learning") });
		const processor = new LearningProcessor({
			bus,
			triage: new LearningTriage({}),
			pendingDir: path.join(root, "learning"),
		});
		const capabilitySynthesizer = new CapabilitySynthesizer({
			cwd: root,
			autoToolsDir: path.join(root, "tools", "auto"),
			autoMcpDir: path.join(root, "mcp", "auto"),
			llm,
		});
		const bridge = new LearnerAgentBridge({
			processor,
			skillLearner: new SkillLearner({ recordStore: journal }),
			capabilityGapLearner: new CapabilityGapLearner({ synthesizer: capabilitySynthesizer }),
			capabilitySynthesizer,
			triggers: new LearningTriggers({ recordStore: journal }),
			recordStore: journal,
			capabilityInventory: () => [],
			autoApproveSkills: false,
			autoApproveCapabilities: false,
		});
		const runner = new LearnerAgentRunner({
			llm,
			kaos: undefined as never,
			tracker: {} as never,
			permission: new PermissionManager({ profile: "unrestricted", interaction: "unattended", kagekoDir: root }),
			learnerToolsDeps: {
				recordStore: journal,
				inventory: () => [],
				errorPatterns: () => [],
			},
			sinks: bridge,
		});
		bridge.attachRunner(runner);

		const event: LearningEvent = {
			id: "gap-event-1",
			source: "capability_gap",
			timestamp: Date.now(),
			payload: {
				description: GAP_DESCRIPTION,
				proposedKind: "tool",
				evidence: {
					scope: "workflow",
					futureTasks: ["Build a webhook workflow", "Build a multi-step data pipeline"],
					alternativesChecked: ["No existing session capability constructs workflow JSON"],
				},
			},
		} as unknown as LearningEvent;

		const output = await bridge.handle(event, {
			action: "pending",
			target: "capability_gap",
			reason: "missing capability needs design",
		});
		// Success flows through the sink; handle itself has nothing to add.
		expect(output).toBeUndefined();

		const pending = await processor.listPending();
		expect(pending).toHaveLength(1);
		const entry = pending[0]!;
		expect(entry.event.id).toBe("gap-event-1");
		expect(entry.decision).toEqual({
			action: "pending",
			target: "capability_gap",
			reason: "learner-agent proposal",
		});
		const entryOutput = entry.output as Record<string, unknown>;
		expect(entryOutput).toMatchObject({
			kind: "tool",
			name: "create-workflow",
			description: "Create and configure normalized workflow definitions programmatically.",
			parameters: { type: "object", properties: { nodes: { type: "array" } }, required: ["nodes"] },
			command: "node",
			args: ["{{__args_json}}"],
			fingerprint: `tool:${GAP_DESCRIPTION}`,
			status: "pending",
		});
		expect(typeof entryOutput["code"]).toBe("string");

		// The learner made its own conversation (system prompt + trigger + tool
		// calls) plus the synthesizer call; none of it touched the main journal.
		const learnerRequests = requests.filter((request) => request.tools.includes("propose_capability"));
		expect(learnerRequests.length).toBeGreaterThanOrEqual(2);
		expect(learnerRequests[0]?.userText).toContain("Learning trigger: capability_gap");
		expect(mainJournalAppend).not.toHaveBeenCalled();

		await bus.close();
	});

	it("keeps the failed audit shape with the provider error when synthesis is overloaded", async () => {
		const root = await tempDir();
		const { llm: baseLlm } = scriptedLlm();
		// Overload only the synthesis call; the learner conversation succeeds.
		const llm: AgentLlm = {
			chat: async (options) => {
				if ((options.tools ?? []).length === 0) {
					throw new Error("503: our servers are currently overloaded. Please try again later.");
				}
				return baseLlm.chat(options);
			},
		};
		const journal = { load: async () => [] as SessionEvent[], append: vi.fn() };
		const bus = new LearningBus({ learningDir: path.join(root, "learning") });
		const processor = new LearningProcessor({
			bus,
			triage: new LearningTriage({}),
			pendingDir: path.join(root, "learning"),
		});
		const capabilitySynthesizer = new CapabilitySynthesizer({
			cwd: root,
			autoToolsDir: path.join(root, "tools", "auto"),
			autoMcpDir: path.join(root, "mcp", "auto"),
			llm,
		});
		const bridge = new LearnerAgentBridge({
			processor,
			skillLearner: new SkillLearner({ recordStore: journal }),
			capabilityGapLearner: new CapabilityGapLearner({ synthesizer: capabilitySynthesizer }),
			capabilitySynthesizer,
			triggers: new LearningTriggers({ recordStore: journal }),
			recordStore: journal,
			capabilityInventory: () => [],
			autoApproveSkills: false,
			autoApproveCapabilities: false,
		});
		const runner = new LearnerAgentRunner({
			llm,
			kaos: undefined as never,
			tracker: {} as never,
			permission: new PermissionManager({ profile: "unrestricted", interaction: "unattended", kagekoDir: root }),
			learnerToolsDeps: { recordStore: journal, inventory: () => [], errorPatterns: () => [] },
			sinks: bridge,
		});
		bridge.attachRunner(runner);

		const event: LearningEvent = {
			id: "gap-event-overload",
			source: "capability_gap",
			timestamp: Date.now(),
			payload: {
				description: GAP_DESCRIPTION,
				proposedKind: "tool",
				evidence: {
					scope: "workflow",
					futureTasks: ["Build a webhook workflow", "Build a multi-step data pipeline"],
					alternativesChecked: ["No existing session capability constructs workflow JSON"],
				},
			},
		} as unknown as LearningEvent;

		const output = (await bridge.handle(event, {
			action: "pending",
			target: "capability_gap",
			reason: "missing capability needs design",
		})) as Record<string, unknown>;
		expect(output).toMatchObject({ kind: "none", status: "failed" });
		expect(String(output["failure"])).toContain("overloaded");
		expect(journal.append).not.toHaveBeenCalled();
		await bus.close();
	});
});
