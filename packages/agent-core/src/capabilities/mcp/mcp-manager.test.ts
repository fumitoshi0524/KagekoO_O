import { describe, expect, it } from "vitest";
import {
	DEFAULT_MCP_CALL_TIMEOUT_MS,
	DEFAULT_MCP_CONNECT_TIMEOUT_MS,
	McpManager,
} from "./mcp-manager.js";
import type { EnvironmentScrubber } from "../../ports/workspace.js";

const noopScrub: EnvironmentScrubber = () => ({});

describe("McpManager timeout options", () => {
	it("keeps the exported defaults when no timeouts are configured", () => {
		const manager = new McpManager({}, noopScrub);
		expect(manager.connectTimeoutMs).toBe(DEFAULT_MCP_CONNECT_TIMEOUT_MS);
		expect(manager.callTimeoutMs).toBe(DEFAULT_MCP_CALL_TIMEOUT_MS);
		expect(DEFAULT_MCP_CONNECT_TIMEOUT_MS).toBe(30_000);
		expect(DEFAULT_MCP_CALL_TIMEOUT_MS).toBe(30_000);
	});

	it("stores configured connect/call timeouts", () => {
		const manager = new McpManager({}, noopScrub, { connectTimeoutMs: 5_000, callTimeoutMs: 120_000 });
		expect(manager.connectTimeoutMs).toBe(5_000);
		expect(manager.callTimeoutMs).toBe(120_000);
	});

	it("connects an empty server set regardless of timeout configuration", async () => {
		const manager = new McpManager({}, noopScrub, { connectTimeoutMs: 1_000, callTimeoutMs: 1_000 });
		await manager.connectAll();
		expect(await manager.listTools()).toEqual([]);
		await manager.close();
	});
});
