import { describe, expect, it } from "vitest";
import { TurnFlow, DEFAULT_TOOL_RESULT_BUDGET } from "./turn-runner.js";
import { DEFAULT_TOOL_CONCURRENCY } from "./tool-scheduler.js";
import type { AgentLlm, RegistryLike, ToolExecution } from "./turn-runner.js";
import type { ChatResponse } from "../ports/llm.js";

function sleep(ms: number): Promise<void> {
	return new Promise((resolve) => setTimeout(resolve, ms));
}

/** Fake LLM that emits `callCount` parallel tool calls on the first step, then ends the turn. */
function fakeLlm(callCount: number): AgentLlm {
	let step = 0;
	return {
		chat: async (): Promise<ChatResponse> => {
			step += 1;
			if (step === 1) {
				return {
					content: "",
					finishReason: "tool_calls",
					usage: { promptTokens: 0, completionTokens: 0 },
					toolCalls: Array.from({ length: callCount }, (_, i) => ({
						id: `call-${i}`,
						name: "slow",
						arguments: { n: i },
					})),
				};
			}
			return { content: "done", finishReason: "stop", usage: { promptTokens: 0, completionTokens: 0 }, toolCalls: [] };
		},
	};
}

function concurrencyProbeRegistry(probe: { active: number; maxActive: number }): RegistryLike {
	return {
		asFunctions: () => [
			{ type: "function", function: { name: "slow", description: "slow tool", parameters: { type: "object" } } },
		],
		validateArgs: () => {},
		resolveExecution: (): ToolExecution => ({
			accesses: [],
			execute: async () => {
				probe.active += 1;
				probe.maxActive = Math.max(probe.maxActive, probe.active);
				await sleep(25);
				probe.active -= 1;
				return { output: "ok" };
			},
		}),
	};
}

describe("TurnFlow toolConcurrency", () => {
	it("limits in-flight tool executions to the configured concurrency", async () => {
		const probe = { active: 0, maxActive: 0 };
		const flow = new TurnFlow({ toolConcurrency: 2 });
		const result = await flow.run({
			llm: fakeLlm(6),
			registry: concurrencyProbeRegistry(probe),
			messages: [{ role: "user", content: "hi" }],
		});
		expect(result.stopReason).not.toBe("error");
		expect(probe.maxActive).toBe(2);
	});

	it("keeps the ToolScheduler built-in default when no concurrency is configured", async () => {
		const probe = { active: 0, maxActive: 0 };
		const flow = new TurnFlow();
		await flow.run({
			llm: fakeLlm(6),
			registry: concurrencyProbeRegistry(probe),
			messages: [{ role: "user", content: "hi" }],
		});
		// Six non-conflicting calls all fit under the default of 8.
		expect(DEFAULT_TOOL_CONCURRENCY).toBe(8);
		expect(probe.maxActive).toBe(6);
	});

	it("keeps the built-in tool result budget as the exported default", () => {
		expect(DEFAULT_TOOL_RESULT_BUDGET).toBe(100_000);
	});
});

function repeatedToolLlm(repetitions: number): AgentLlm {
	let calls = 0;
	return {
		chat: async (): Promise<ChatResponse> => {
			calls += 1;
			if (calls <= repetitions) {
				return {
					content: "",
					finishReason: "tool_calls",
					usage: { promptTokens: 1, completionTokens: 0 },
					toolCalls: [{ id: `same-${calls}`, name: "same", arguments: { target: "x" } }],
				};
			}
			return { content: "done", finishReason: "stop", usage: { promptTokens: 1, completionTokens: 0 }, toolCalls: [] };
		},
	};
}

/** Fake LLM that reissues the same tool with different arguments on every step. */
function variedArgsToolLlm(repetitions: number): AgentLlm {
	let calls = 0;
	return {
		chat: async (): Promise<ChatResponse> => {
			calls += 1;
			if (calls <= repetitions) {
				return {
					content: "",
					finishReason: "tool_calls",
					usage: { promptTokens: 1, completionTokens: 0 },
					toolCalls: [
						{ id: `open-${calls}`, name: "same", arguments: { session: `session-${calls}`, ignoreErrors: calls % 2 === 0 } },
					],
				};
			}
			return { content: "done", finishReason: "stop", usage: { promptTokens: 1, completionTokens: 0 }, toolCalls: [] };
		},
	};
}

function singleToolRegistry(execute: () => Promise<{ output: string; isError?: boolean }>, accesses: ToolExecution["accesses"] = []): RegistryLike {
	return {
		asFunctions: () => [{ type: "function", function: { name: "same", description: "", parameters: { type: "object" } } }],
		validateArgs: () => {},
		resolveExecution: () => ({ accesses, execute }),
	};
}

function idempotencySession() {
	const entries = new Map<string, { state: "pending" | "completed"; result?: { output: string } }>();
	return {
		sessionId: "session-1",
		entries,
		idempotencyStore: {
			async reserve(key: string) {
				const existing = entries.get(key);
				if (existing?.state === "completed") return { state: "completed" as const, result: existing.result };
				if (existing) return { state: "pending" as const };
				entries.set(key, { state: "pending" });
				return { state: "new" as const };
			},
			async complete(key: string, result: { output: string }) {
				entries.set(key, { state: "completed", result });
			},
			async release(key: string) {
				if (entries.get(key)?.state === "pending") entries.delete(key);
			},
		},
	};
}

function toolResultOutputs(events: Array<{ type: string; data: unknown }>): string[] {
	return events
		.filter((event) => event.type === "tool.result")
		.map((event) => String((event.data as { result?: { output?: string } }).result?.output ?? ""));
}

describe("TurnFlow circuit breaker", () => {
	it("persists a budget-exhausted checkpoint instead of reporting completion", async () => {
		const events: string[] = [];
		const result = await new TurnFlow({ maxSteps: 10 }).run({
			llm: repeatedToolLlm(5),
			registry: singleToolRegistry(async () => ({ output: "changed" })),
			messages: [{ role: "user", content: "work" }],
			maxTokens: 1,
			onEvent: (event) => events.push(event.type),
		});
		expect(result.stopReason).toBe("budget_exhausted");
		expect(events).toContain("turn.checkpointed");
	});

	it("stops and checkpoints identical observations as stalled", async () => {
		const events: string[] = [];
		const result = await new TurnFlow({ maxSteps: 10, maxRepeatedToolCalls: 10, maxNoProgressSteps: 2 }).run({
			llm: repeatedToolLlm(5),
			registry: singleToolRegistry(async () => ({ output: "unchanged" })),
			messages: [{ role: "user", content: "work" }],
			onEvent: (event) => events.push(event.type),
		});
		expect(result.stopReason).toBe("stalled");
		expect(events).toContain("turn.checkpointed");
	});

	it("stops a successful call loop whose varied-argument calls return the same observation", async () => {
		// Production loop: every `agent-browser open` permutation exits 0 with the
		// same TLS interstitial. No exact (tool, args, output) repetition and no
		// failure ever occurs, so only the output-class streak can catch it.
		const events: string[] = [];
		const result = await new TurnFlow({ maxSteps: 10, maxRepeatedToolCalls: 100, maxNoProgressSteps: 3 }).run({
			llm: variedArgsToolLlm(10),
			registry: singleToolRegistry(async () => ({ output: "This site cannot provide a secure connection (TLS interstitial)" })),
			messages: [{ role: "user", content: "open the page" }],
			onEvent: (event) => events.push(event.type),
		});
		expect(result.stopReason).toBe("stalled");
		expect(events).toContain("turn.checkpointed");
	});

	it("treats observations that differ only in volatile details as the same class", async () => {
		let executions = 0;
		const result = await new TurnFlow({ maxSteps: 10, maxRepeatedToolCalls: 100, maxNoProgressSteps: 3 }).run({
			llm: variedArgsToolLlm(10),
			registry: singleToolRegistry(async () => ({ output: `Still loading (poll ${++executions}, 0 bytes received)` })),
			messages: [{ role: "user", content: "open the page" }],
		});
		expect(result.stopReason).toBe("stalled");
	});

	it("keeps running when each successful observation genuinely differs", async () => {
		let executions = 0;
		const pages = ["alpha page", "beta page", "gamma page", "delta page"];
		const result = await new TurnFlow({ maxSteps: 10, maxRepeatedToolCalls: 100, maxNoProgressSteps: 3 }).run({
			llm: variedArgsToolLlm(4),
			registry: singleToolRegistry(async () => ({ output: pages[executions++] ?? "omega page" })),
			messages: [{ role: "user", content: "open the page" }],
		});
		expect(result.stopReason).toBe("end_turn");
	});

	it("force-stops an arg-varied failure loop that never repeats a signature", async () => {
		// Production loop: 15 slightly different `agent-browser download` argv,
		// each failing with the same error class.
		const events: string[] = [];
		const result = await new TurnFlow({ maxSteps: 10, maxRepeatedToolCalls: 100, maxToolFailureLoop: 4 }).run({
			llm: variedArgsToolLlm(10),
			registry: singleToolRegistry(async () => ({
				output: "Downloaded file not found at expected path",
				isError: true,
			})),
			messages: [{ role: "user", content: "download the report" }],
			onEvent: (event) => events.push(event.type),
		});
		expect(result.stopReason).toBe("stalled");
		expect(events).toContain("turn.checkpointed");
	});

	it("does not repeat a completed mutating operation after recovery", async () => {
		let executions = 0;
		const session = idempotencySession();
		const registry = singleToolRegistry(async () => ({ output: `write-${++executions}` }), [
			{ kind: "file", operation: "write", path: "/workspace/out" },
		]);
		await new TurnFlow().run({ llm: repeatedToolLlm(1), registry, messages: [{ role: "user", content: "write" }], session });
		const events: Array<{ type: string; data: unknown }> = [];
		await new TurnFlow().run({
			llm: repeatedToolLlm(1),
			registry,
			messages: [{ role: "user", content: "resume" }],
			session,
			onEvent: (event) => events.push({ type: event.type, data: event.data }),
		});
		expect(executions).toBe(1);
		expect(toolResultOutputs(events).some((output) => output.includes("Idempotent replay") && output.includes("write-1"))).toBe(true);
	});

	it("releases a failed mutating operation so a later attempt re-executes", async () => {
		let executions = 0;
		const session = idempotencySession();
		const registry = singleToolRegistry(
			async () => {
				executions += 1;
				return executions === 1
					? { output: "merge conflict: push rejected", isError: true }
					: { output: `write-${executions}` };
			},
			[{ kind: "file", operation: "write", path: "/workspace/out" }],
		);
		// A mutating tool is never auto-retried, so the first run fails once.
		await new TurnFlow({ maxToolRetries: 2 }).run({
			llm: repeatedToolLlm(1),
			registry,
			messages: [{ role: "user", content: "write" }],
			session,
		});
		expect(session.entries.size).toBe(0);
		await new TurnFlow().run({ llm: repeatedToolLlm(1), registry, messages: [{ role: "user", content: "retry" }], session });
		expect(executions).toBe(2);
	});

	it("keeps a pending reservation when the mutating operation's outcome is uncertain", async () => {
		let executions = 0;
		const session = idempotencySession();
		const registry = singleToolRegistry(
			async () => {
				executions += 1;
				if (executions === 1) {
					const error = new Error("Tool execution exceeded 50ms");
					error.name = "AbortError";
					throw error;
				}
				return { output: `write-${executions}` };
			},
			[{ kind: "file", operation: "write", path: "/workspace/out" }],
		);
		await new TurnFlow({ maxToolExecutionMs: 50 }).run({
			llm: repeatedToolLlm(1),
			registry,
			messages: [{ role: "user", content: "write" }],
			session,
		});
		const events: Array<{ type: string; data: unknown }> = [];
		await new TurnFlow().run({
			llm: repeatedToolLlm(1),
			registry,
			messages: [{ role: "user", content: "retry" }],
			session,
			onEvent: (event) => events.push({ type: event.type, data: event.data }),
		});
		// The timed-out first attempt may have taken effect: the identical call
		// is asked to verify rather than silently re-executing.
		expect(executions).toBe(1);
		expect(toolResultOutputs(events).some((output) => output.includes("never recorded"))).toBe(true);
	});

	it("retries a transient read-only tool failure with a bounded backoff", async () => {
		let executions = 0;
		const result = await new TurnFlow({ maxToolRetries: 1 }).run({
			llm: repeatedToolLlm(1),
			registry: singleToolRegistry(async () => {
				executions += 1;
				return executions === 1 ? { output: "503 service unavailable", isError: true } : { output: "recovered" };
			}),
			messages: [{ role: "user", content: "read" }],
		});
		expect(executions).toBe(2);
		expect(result.stopReason).toBe("end_turn");
	});

	it("emits tool.retrying with attempt and delay before a transient read-only retry", async () => {
		let executions = 0;
		const events: Array<{ type: string; data: Record<string, unknown> }> = [];
		await new TurnFlow({ maxToolRetries: 2 }).run({
			llm: repeatedToolLlm(1),
			registry: singleToolRegistry(async () => {
				executions += 1;
				return executions === 1 ? { output: "503 service unavailable", isError: true } : { output: "recovered" };
			}),
			messages: [{ role: "user", content: "read" }],
			onEvent: (event) => events.push({ type: event.type, data: event.data as Record<string, unknown> }),
		});
		const retrying = events.filter((event) => event.type === "tool.retrying");
		expect(retrying).toHaveLength(1);
		expect(retrying[0]!.data).toMatchObject({
			toolName: "same",
			attempt: 1,
			maxAttempts: 3,
			reason: "503 service unavailable",
		});
		expect(typeof retrying[0]!.data["delayMs"]).toBe("number");
	});

	it("counts near-identical calls toward the same repeated-call streak", async () => {
		const volatileArgsLlm: AgentLlm = (() => {
			let calls = 0;
			const variants = [
				{ target: "x", timeout: 1_000, nested: { requestId: "a", note: "n" } },
				{ target: "  x  ", timeout: 2_000, nested: { requestId: "b", note: "n" } },
			];
			return {
				chat: async (): Promise<ChatResponse> => {
					calls += 1;
					if (calls <= variants.length) {
						return {
							content: "",
							finishReason: "tool_calls",
							usage: { promptTokens: 1, completionTokens: 0 },
							toolCalls: [{ id: `same-${calls}`, name: "same", arguments: variants[calls - 1]! }],
						};
					}
					return { content: "done", finishReason: "stop", usage: { promptTokens: 1, completionTokens: 0 }, toolCalls: [] };
				},
			};
		})();
		let executions = 0;
		const result = await new TurnFlow({ maxSteps: 10, maxRepeatedToolCalls: 2, maxNoProgressSteps: 100 }).run({
			llm: volatileArgsLlm,
			registry: singleToolRegistry(async () => ({ output: `changed-${++executions}` })),
			messages: [{ role: "user", content: "work" }],
		});
		expect(result.stopReason).toBe("stalled");
		expect(executions).toBe(2);
	});

	it("never auto-retries a declared mutating tool failure", async () => {
		let executions = 0;
		await new TurnFlow({ maxToolRetries: 3 }).run({
			llm: repeatedToolLlm(1),
			registry: singleToolRegistry(
				async () => ({ output: `503 service unavailable (${++executions})`, isError: true }),
				[
					{
						kind: "network",
						operation: "send",
						target: "https://api.example.test/operations",
						method: "POST",
						credentialed: true,
						sendsContent: true,
					},
				],
			),
			messages: [{ role: "user", content: "send" }],
		});
		expect(executions).toBe(1);
	});
});
