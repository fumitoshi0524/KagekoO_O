import { describe, expect, it } from "vitest";
import type { PermissionManagerLike } from "../types.js";
import { createPolicyChain } from "./index.js";
import { ManagedCapabilityPathDenyPolicy, isManagedCapabilityPath } from "./managed-capability-path.js";

const permission = {
	profile: "unrestricted",
	interaction: "interactive",
	cwd: "C:\\work\\demo",
	denyList: [],
	allowList: [],
	askList: [],
	history: new Map(),
	historyKey: () => "",
} satisfies PermissionManagerLike;

describe("ManagedCapabilityPathDenyPolicy", () => {
	const policy = new ManagedCapabilityPathDenyPolicy(permission);

	it("denies direct generated Tool, MCP, and skill writes in every permission profile", () => {
		for (const target of [
			".kageko/tools/auto/example/manifest.json",
			"C:\\work\\demo\\.kageko\\mcp\\auto\\server\\server.cjs",
			".kageko/skills/auto/release/SKILL.md",
		]) {
			const result = policy.evaluate({
				toolName: "write",
				args: { path: target },
				profile: "unrestricted",
				interaction: "interactive",
				execution: { accesses: [{ kind: "file", operation: "write", path: target }] },
			});
			expect(result?.kind).toBe("deny");
		}
	});

	it("denies shell commands that address a learner-managed directory", () => {
		const result = policy.evaluate({
			toolName: "bash",
			args: { command: "node build.mjs > .kageko/tools/auto/demo/tool.cjs" },
			profile: "workspace",
			interaction: "unattended",
			execution: { accesses: [{ kind: "all" }] },
		});
		expect(result?.kind).toBe("deny");
	});

	it("allows reads and ordinary project writes", () => {
		for (const [operation, target] of [
			["read", ".kageko/tools/auto/example/manifest.json"],
			["write", "src/tool.cjs"],
		] as const) {
			const result = policy.evaluate({
				toolName: operation === "read" ? "read" : "write",
				args: { path: target },
				profile: "workspace",
				interaction: "interactive",
				execution: { accesses: [{ kind: "file", operation, path: target }] },
			});
			expect(result).toBeUndefined();
		}
	});

	it("matches only the exact learner-owned layout", () => {
		expect(isManagedCapabilityPath("C:\\repo\\.kageko\\tools\\auto\\x")).toBe(true);
		expect(isManagedCapabilityPath("C:\\repo\\docs\\.kageko-tools\\auto\\x")).toBe(false);
		expect(isManagedCapabilityPath("C:\\repo\\.kageko\\tools\\manual\\x")).toBe(false);
	});

	it("runs before configured allow and unrestricted approval", async () => {
		const permissive = {
			...permission,
			allowList: ["write"],
		} satisfies PermissionManagerLike;
		const context = {
			toolName: "write",
			args: { path: ".kageko/tools/auto/demo/tool.cjs" },
			profile: "unrestricted" as const,
			interaction: "interactive" as const,
			execution: {
				accesses: [{ kind: "file" as const, operation: "write" as const, path: ".kageko/tools/auto/demo/tool.cjs" }],
			},
		};
		let decision;
		for (const candidate of createPolicyChain({ permission: permissive })) {
			decision = await candidate.evaluate(context);
			if (decision) break;
		}
		expect(decision?.kind).toBe("deny");
		expect(decision && "message" in decision ? decision.message : "").toContain("learner-managed");
	});
});
