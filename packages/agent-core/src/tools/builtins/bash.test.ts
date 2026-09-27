import { describe, expect, it } from "vitest";
import { BASH_DEFAULT_TIMEOUT_MS, BASH_MAX_TIMEOUT_MS, bashTool, createBashTool } from "./bash.js";
import type { Tool, ToolContext } from "../types.js";

interface Captured {
	timeoutMs?: number;
}

type BashTool = Tool<{ command: string; background?: boolean; timeout?: number }>;

function timeoutDescription(tool: BashTool): string {
	const params = tool.parameters as { properties: { timeout: { description: string } } };
	return params.properties.timeout.description;
}

function fakeContext(captured: Captured): ToolContext {
	const tracked = {
		taskId: "task-1",
		wait: async (timeoutMs: number) => {
			captured.timeoutMs = timeoutMs;
			return { exitCode: 0, timedOut: false, error: undefined };
		},
		kill: async () => {},
		stdout: { text: () => "", truncated: () => false },
		stderr: { text: () => "", truncated: () => false },
	};
	return {
		kaos: {
			cwd: process.cwd(),
			env: {},
			shellInvocation: (command: string) => ({ command: "sh", args: ["-c", command] }),
		},
		tracker: {
			spawnDurable: async () => tracked,
		},
	} as unknown as ToolContext;
}

describe("bashTool timeouts", () => {
	it("keeps the exported defaults on the shared instance", () => {
		expect(BASH_DEFAULT_TIMEOUT_MS).toBe(60_000);
		expect(BASH_MAX_TIMEOUT_MS).toBe(300_000);
		expect(timeoutDescription(bashTool)).toContain("default 60000, max 300000");
	});

	it("applies the default timeout when a call does not request one", async () => {
		const captured: Captured = {};
		await bashTool.execute!({ command: "true" }, fakeContext(captured));
		expect(captured.timeoutMs).toBe(60_000);
	});

	it("clamps a requested timeout to the max", async () => {
		const captured: Captured = {};
		await bashTool.execute!({ command: "true", timeout: 999_999 }, fakeContext(captured));
		expect(captured.timeoutMs).toBe(300_000);
	});

	it("honors configured timeouts in a constructed tool", async () => {
		const tool = createBashTool({ defaultTimeoutMs: 5_000, maxTimeoutMs: 9_000 });
		expect(timeoutDescription(tool)).toContain("default 5000, max 9000");
		const captured: Captured = {};
		await tool.execute!({ command: "true" }, fakeContext(captured));
		expect(captured.timeoutMs).toBe(5_000);
		await tool.execute!({ command: "true", timeout: 60_000 }, fakeContext(captured));
		expect(captured.timeoutMs).toBe(9_000);
	});
});
