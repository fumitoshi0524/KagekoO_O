import * as os from "node:os";
import * as path from "node:path";
import * as fs from "node:fs/promises";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import {
	DEFAULT_MAX_CONCURRENT_SUBAGENTS,
	DEFAULT_SUBAGENT_TIMEOUT_MS,
	SubagentHost,
	type SubagentChildSession,
	type SubagentHostSession,
} from "./subagent-host.js";
import { ToolRegistry } from "../tools/registry.js";
import type { AgentLlm } from "../turn/turn-runner.js";
import type { ChatOptions, ChatResponse } from "../ports/llm.js";

let cwd: string;

beforeEach(async () => {
	cwd = await fs.mkdtemp(path.join(os.tmpdir(), "kageko-subagent-host-"));
});

afterEach(async () => {
	await fs.rm(cwd, { recursive: true, force: true });
});

/** An LLM whose chat never resolves until the caller aborts it. */
function hangingLlm(): AgentLlm {
	return {
		chat: (options: ChatOptions): Promise<ChatResponse> =>
			new Promise((_, reject) => {
				const signal = options.signal;
				if (signal?.aborted) {
					reject(signal.reason ?? new Error("aborted"));
					return;
				}
				signal?.addEventListener("abort", () => reject(signal.reason ?? new Error("aborted")), { once: true });
			}),
	};
}

function fakeSession(): SubagentHostSession {
	return {
		cwd,
		registry: new ToolRegistry(),
		llm: hangingLlm(),
		kaos: { cwd } as unknown as SubagentHostSession["kaos"],
		tracker: {
			fork: () => ({ stopAll: async () => {} }),
			stopAll: async () => {},
		} as unknown as NonNullable<SubagentHostSession["tracker"]>,
		cron: { stopAll: async () => {} },
		plugins: {} as SubagentHostSession["plugins"],
		skills: { list: () => [] } as unknown as SubagentHostSession["skills"],
	};
}

function fakeChildSession(options: Parameters<SubagentHost["createChildSession"]>[0]): SubagentChildSession {
	return {
		...options,
		goalStore: {},
		todoStore: { todos: [] },
		isClosed: () => false,
		runTurn: (fn) => fn(),
		close: async () => {},
	} as SubagentChildSession;
}

describe("SubagentHost bounds", () => {
	it("keeps the exported concurrency default when maxConcurrent is not configured", () => {
		const host = new SubagentHost({ session: fakeSession(), createChildSession: fakeChildSession });
		expect(host.maxConcurrent).toBe(DEFAULT_MAX_CONCURRENT_SUBAGENTS);
		expect(DEFAULT_MAX_CONCURRENT_SUBAGENTS).toBe(4);
	});

	it("honors a configured maxConcurrent", () => {
		const host = new SubagentHost({ session: fakeSession(), createChildSession: fakeChildSession, maxConcurrent: 2 });
		expect(host.maxConcurrent).toBe(2);
		expect(host.semaphore.max).toBe(2);
	});

	it("honors a profile timeoutMs when the call does not set one", async () => {
		const host = new SubagentHost({ session: fakeSession(), createChildSession: fakeChildSession });
		await expect(host.run({ prompt: "work", profile: { timeoutMs: 50 } })).rejects.toMatchObject({
			name: "SubagentTimeoutError",
		});
	});

	it("keeps the 30-minute default when neither call nor profile sets a timeout", () => {
		expect(SubagentHost.DEFAULT_TIMEOUT_MS).toBe(DEFAULT_SUBAGENT_TIMEOUT_MS);
		expect(DEFAULT_SUBAGENT_TIMEOUT_MS).toBe(1_800_000);
	});

	it("a per-call timeoutMs still wins over the profile timeout", async () => {
		const host = new SubagentHost({ session: fakeSession(), createChildSession: fakeChildSession });
		const started = Date.now();
		// The profile allows an hour; the call bounds the run to 50ms.
		await expect(host.run({ prompt: "work", profile: { timeoutMs: 3_600_000 }, timeoutMs: 50 })).rejects.toMatchObject({
			name: "SubagentTimeoutError",
		});
		expect(Date.now() - started).toBeLessThan(10_000);
	});
});
