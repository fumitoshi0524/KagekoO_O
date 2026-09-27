import { describe, expect, it, vi } from "vitest";
import {
	DEFAULT_LEARNER_MAX_QUEUED_RUNS,
	DEFAULT_LEARNER_MAX_STEPS,
	DEFAULT_LEARNER_TIMEOUT_MS,
	LearnerAgentRunner,
	buildTriggerPrompt,
	LEARNER_SYSTEM_PROMPT,
	type LearnerTrigger,
} from "./learner-agent.js";
import { PermissionManager } from "../../../permissions/index.js";
import type { AgentLlm } from "../../../turn/turn-runner.js";
import type { ChatOptions, ChatResponse } from "../../../ports/llm.js";
import type { LearningEvent } from "../event.js";

const USAGE = { promptTokens: 1, completionTokens: 1 };

function textResponse(content: string): ChatResponse {
	return { content, toolCalls: [], finishReason: "stop", usage: USAGE };
}

function toolCallResponse(name: string, args: Record<string, unknown>, id = "call-1"): ChatResponse {
	return { content: "", toolCalls: [{ id, name, arguments: args }], finishReason: "tool_calls", usage: USAGE };
}

function capabilityGapEvent(): LearningEvent {
	return {
		id: "gap-1",
		source: "capability_gap",
		timestamp: 1,
		payload: {
			description: "Create normalized workflow definitions as one reusable local tool",
			proposedKind: "tool",
			evidence: {
				scope: "workflow",
				futureTasks: ["Build a webhook workflow", "Build a data pipeline"],
				alternativesChecked: ["No existing capability builds workflows"],
			},
		},
	} as unknown as LearningEvent;
}

function makeRunner(
	chat: (options: ChatOptions) => Promise<ChatResponse>,
	overrides: Partial<ConstructorParameters<typeof LearnerAgentRunner>[0]> = {},
) {
	const requests: ChatOptions[] = [];
	const llm: AgentLlm = {
		chat: async (options) => {
			requests.push(options);
			return chat(options);
		},
	};
	const sinks = {
		submitSkillProposal: vi.fn(
			async (
				_skill: unknown,
				_trigger: unknown,
				_run?: unknown,
			): Promise<{ accepted: boolean; status?: "pending" | "approved"; reason?: string }> => ({
				accepted: true,
				status: "pending",
			}),
		),
		submitCapabilityProposal: vi.fn(
			async (
				_input: unknown,
				_trigger: unknown,
				_run?: unknown,
			): Promise<{ accepted: boolean; status?: "pending" | "approved"; reason?: string }> => ({
				accepted: true,
				status: "pending",
			}),
		),
	};
	const runner = new LearnerAgentRunner({
		llm,
		kaos: undefined as never,
		tracker: {} as never,
		permission: new PermissionManager({
			profile: "unrestricted",
			interaction: "unattended",
			kagekoDir: process.cwd(),
		}),
		learnerToolsDeps: {
			recordStore: { load: async () => [] },
			inventory: () => [],
			errorPatterns: () => [],
		},
		sinks,
		...overrides,
	});
	return { runner, sinks, requests };
}

describe("LearnerAgentRunner", () => {
	it("uses defaults that leave room for a grounded synthesis", () => {
		expect(DEFAULT_LEARNER_MAX_STEPS).toBe(6);
		expect(DEFAULT_LEARNER_TIMEOUT_MS).toBe(300_000);
		expect(DEFAULT_LEARNER_MAX_QUEUED_RUNS).toBe(4);
	});

	it("runs a declined turn as a normal outcome", async () => {
		const { runner, requests } = makeRunner(async () => textResponse("No durable artifact justified."));
		const result = await runner.run({ kind: "capability_gap", event: capabilityGapEvent() });
		expect(result).toEqual({ proposals: 0, declined: true });
		// The dedicated registry exposes exactly the five learner tools.
		expect(requests[0]?.tools?.map((tool) => tool.function.name)).toEqual([
			"read_recent_events",
			"inspect_inventory",
			"read_error_patterns",
			"propose_skill",
			"propose_capability",
		]);
		// The learner system prompt leads the conversation.
		expect(requests[0]?.messages[0]).toEqual({ role: "system", content: LEARNER_SYSTEM_PROMPT });
	});

	it("counts accepted proposals and forwards the trigger to the sinks", async () => {
		const { runner, sinks } = makeRunner(async (options) => {
			const hasToolResult = options.messages.some((message) => message.role === "tool");
			if (!hasToolResult) {
				return toolCallResponse("propose_capability", {
					description: "Create normalized workflow definitions as one reusable local tool",
					proposedKind: "tool",
				});
			}
			return textResponse("Proposed.");
		});
		const trigger: LearnerTrigger = { kind: "capability_gap", event: capabilityGapEvent() };
		const result = await runner.run(trigger);
		expect(result).toEqual({ proposals: 1, declined: false });
		expect(sinks.submitCapabilityProposal).toHaveBeenCalledOnce();
		expect(sinks.submitCapabilityProposal.mock.calls[0]?.[1]).toEqual(trigger);
	});

	it("does not count sink rejections as proposals", async () => {
		const { runner, sinks } = makeRunner(async (options) => {
			const hasToolResult = options.messages.some((message) => message.role === "tool");
			if (!hasToolResult) return toolCallResponse("propose_skill", { name: "x", description: "d", instructions: "i" });
			return textResponse("Understood.");
		});
		sinks.submitSkillProposal.mockResolvedValue({ accepted: false, reason: "duplicate" });
		const result = await runner.run({ kind: "skill_review", event: capabilityGapEvent() });
		expect(result).toEqual({ proposals: 0, declined: true });
	});

	it("reports an LLM failure without throwing", async () => {
		const { runner } = makeRunner(async () => {
			throw new Error("503: our servers are currently overloaded");
		});
		const result = await runner.run({ kind: "capability_gap", event: capabilityGapEvent() });
		expect(result.declined).toBe(false);
		expect(result.failure).toContain("overloaded");
	});

	it("serializes runs behind the queue", async () => {
		const order: string[] = [];
		let releaseFirst!: () => void;
		const firstGate = new Promise<void>((resolve) => {
			releaseFirst = resolve;
		});
		let call = 0;
		const { runner } = makeRunner(async () => {
			call += 1;
			if (call === 1) {
				order.push("first:start");
				await firstGate;
				order.push("first:end");
			} else {
				order.push("second:start");
			}
			return textResponse("done");
		});
		const first = runner.run({ kind: "capability_gap", event: capabilityGapEvent() });
		const second = runner.run({ kind: "skill_review", event: capabilityGapEvent() });
		// Let both runs reach the queue before releasing the first.
		await new Promise((resolve) => setTimeout(resolve, 10));
		releaseFirst();
		const results = await Promise.all([first, second]);
		expect(order).toEqual(["first:start", "first:end", "second:start"]);
		expect(results.every((result) => result.declined)).toBe(true);
	});

	it("drops triggers beyond the queue cap with a diagnostic", async () => {
		const onDiagnostic = vi.fn();
		let release!: () => void;
		const gate = new Promise<void>((resolve) => {
			release = resolve;
		});
		const { runner } = makeRunner(
			async () => {
				await gate;
				return textResponse("done");
			},
			{ maxQueuedRuns: 1, onDiagnostic },
		);
		const first = runner.run({ kind: "capability_gap", event: capabilityGapEvent() });
		const dropped = await runner.run({ kind: "capability_gap", event: capabilityGapEvent() });
		expect(dropped.failure).toContain("queue is full");
		expect(dropped.declined).toBe(false);
		expect(onDiagnostic).toHaveBeenCalledOnce();
		release();
		await first;
	});

	it("bounds a run by the configured timeout", async () => {
		const { runner } = makeRunner(
			(options) =>
				new Promise<ChatResponse>((_resolve, reject) => {
					options.signal?.addEventListener("abort", () => reject(options.signal?.reason ?? new Error("aborted")));
				}),
			{ timeoutMs: 50 },
		);
		const result = await runner.run({ kind: "capability_gap", event: capabilityGapEvent() });
		expect(result.failure).toContain("timed out");
	});

	it("drives the run lifecycle hooks with a token", async () => {
		const onRunStart = vi.fn(() => "run-node-1");
		const onRunEnd = vi.fn();
		const { runner } = makeRunner(async () => textResponse("declined"), { onRunStart, onRunEnd });
		await runner.run({ kind: "skill_review", event: capabilityGapEvent() });
		expect(onRunStart).toHaveBeenCalledOnce();
		expect(onRunEnd).toHaveBeenCalledWith("run-node-1", "completed", expect.stringContaining("skill_review"));
	});

	it("reports hook failures as diagnostics without failing the run", async () => {
		const onDiagnostic = vi.fn();
		const { runner } = makeRunner(async () => textResponse("declined"), {
			onRunStart: () => {
				throw new Error("graph unavailable");
			},
			onDiagnostic,
		});
		const result = await runner.run({ kind: "skill_review", event: capabilityGapEvent() });
		expect(result.declined).toBe(true);
		expect(onDiagnostic).toHaveBeenCalled();
	});

	it("close() aborts the in-flight run, cancels queued runs, and declines later runs fast", async () => {
		const { runner } = makeRunner(
			(options) =>
				new Promise<ChatResponse>((_resolve, reject) => {
					options.signal?.addEventListener("abort", () => reject(options.signal?.reason ?? new Error("aborted")));
				}),
			{ timeoutMs: 60_000 },
		);
		const first = runner.run({ kind: "capability_gap", event: capabilityGapEvent() });
		// Let the first run reach its chat call before queueing the second.
		await new Promise((resolve) => setTimeout(resolve, 10));
		const second = runner.run({ kind: "skill_review", event: capabilityGapEvent() });
		runner.close();
		const [firstResult, secondResult] = await Promise.all([first, second]);
		expect(firstResult).toEqual({ proposals: 0, declined: false, cancelled: true });
		expect(secondResult).toEqual({ proposals: 0, declined: false, cancelled: true });
		expect(await runner.run({ kind: "skill_review", event: capabilityGapEvent() })).toEqual({
			proposals: 0,
			declined: false,
			cancelled: true,
		});
	});

	it("marks the run context stale once the run ends", async () => {
		let captured: { isCurrent(): boolean } | undefined;
		const { runner, sinks } = makeRunner(async (options) => {
			const hasToolResult = options.messages.some((message) => message.role === "tool");
			if (!hasToolResult) {
				return toolCallResponse("propose_skill", {
					name: "stateful-workflows",
					description: "Reuse a verified stateful workflow safely across tasks.",
					instructions:
						"Inspect the advertised tool schemas before choosing operations, preserve every returned identifier, " +
						"execute dependencies in order, and verify final postconditions with authoritative read-back.",
				});
			}
			return textResponse("done");
		});
		sinks.submitSkillProposal.mockImplementation(async (_skill, _trigger, run) => {
			captured = run as { isCurrent(): boolean };
			expect(captured.isCurrent()).toBe(true);
			return { accepted: false, reason: "duplicate" };
		});
		await runner.run({ kind: "skill_review", event: capabilityGapEvent() });
		expect(captured?.isCurrent()).toBe(false);
	});
});

describe("buildTriggerPrompt", () => {
	it("assembles kind, payload JSON, and instructions in code", () => {
		const prompt = buildTriggerPrompt({ kind: "capability_gap", event: capabilityGapEvent() });
		expect(prompt).toContain("Learning trigger: capability_gap");
		expect(prompt).toContain("Create normalized workflow definitions");
		expect(prompt).toContain("propose_capability");
	});

	it("omits the raw payload for error_pattern triggers", () => {
		const event = {
			id: "evt-err",
			source: "tool_result",
			timestamp: 1,
			payload: { toolName: "bash", result: "SECRET_OUTPUT_MARKER" },
		} as unknown as LearningEvent;
		const prompt = buildTriggerPrompt({ kind: "error_pattern", event });
		expect(prompt).not.toContain("SECRET_OUTPUT_MARKER");
		expect(prompt).not.toContain("Trigger event payload");
		expect(prompt).toContain("read_error_patterns");
	});

	it("caps the serialized trigger payload", () => {
		const event = {
			id: "evt-big",
			source: "capability_gap",
			timestamp: 1,
			payload: { description: `START${"x".repeat(100_000)}END_MARKER` },
		} as unknown as LearningEvent;
		const prompt = buildTriggerPrompt({ kind: "capability_gap", event });
		expect(prompt).toContain("START");
		expect(prompt).not.toContain("END_MARKER");
		expect(prompt.length).toBeLessThan(8 * 1024);
	});
});
