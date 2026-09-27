import { afterEach, describe, expect, it, vi } from "vitest";
import { PermissionManager } from "../permissions/permission-manager.js";
import { classifySensitivePath } from "./sensitive-path.js";
import { createBashTool } from "../tools/builtins/bash.js";
import { fetchUrlTool } from "../tools/builtins/fetch-url.js";
import type { ToolExecution } from "../tools/types.js";

const builtinRead: ToolExecution = {
	accesses: [{ kind: "file", operation: "read", path: ".kageko/auth.json" }],
	provenance: { kind: "builtin", ownerId: "kageko", registrationId: "read" },
};

describe("security boundaries", () => {
	afterEach(() => vi.unstubAllGlobals());
	it("treats local credential and configuration stores as sensitive", () => {
		for (const target of [".kageko/auth.json", ".kageko/mcp-tokens.json", ".kageko/config.json", ".codex/auth.json"]) {
			expect(classifySensitivePath(target).sensitive, target).toBe(true);
		}
	});

	it("does not automatically approve reading a credential store", async () => {
		const permission = new PermissionManager({ cwd: process.cwd(), kagekoDir: process.cwd() });
		const decision = await permission.authorize("read", { path: ".kageko/auth.json" }, { execution: builtinRead });
		expect(decision.approved).toBe(false);
		expect(decision.reason).toContain("sensitive");
	});

	it("denies unresolved approvals in unattended mode", async () => {
		const permission = new PermissionManager({
			cwd: process.cwd(),
			kagekoDir: process.cwd(),
			interaction: "unattended",
		});
		const decision = await permission.authorize(
			"write",
			{ path: "test.txt" },
			{
				execution: { accesses: [{ kind: "file", operation: "write", path: "test.txt" }] },
			},
		);
		expect(decision.approved).toBe(false);
		expect(decision.reason).toContain("unattended");
	});

	it("keeps generated capability paths protected in unrestricted mode", async () => {
		const permission = new PermissionManager({
			cwd: process.cwd(),
			kagekoDir: process.cwd(),
			profile: "unrestricted",
		});
		const target = ".kageko/tools/auto/demo/tool.cjs";
		const decision = await permission.authorize(
			"write",
			{ path: target },
			{
				execution: { accesses: [{ kind: "file", operation: "write", path: target }] },
			},
		);
		expect(decision.approved).toBe(false);
		expect(decision.reason).toContain("learner-managed");
	});

	it("keeps catastrophic shell commands blocked in unrestricted mode", async () => {
		const permission = new PermissionManager({
			cwd: process.cwd(),
			kagekoDir: process.cwd(),
			profile: "unrestricted",
		});
		const decision = await permission.authorize(
			"bash",
			{ command: "rm -rf /" },
			{
				execution: { accesses: [{ kind: "all" }] },
			},
		);
		expect(decision.approved).toBe(false);
		expect(decision.reason).toContain("hardline");
	});

	it("reuses a session approval only for the exact shell command", async () => {
		const approvalHandler = vi.fn().mockResolvedValue({ approved: true, record: true });
		const permission = new PermissionManager({
			cwd: process.cwd(),
			kagekoDir: process.cwd(),
			approvalHandler,
		});
		const bash = createBashTool();
		const authorize = (command: string) => {
			const args = { command };
			const { accesses, approvalRule, matchesRule, commandAnalysis } = bash.resolveExecution!(args);
			return permission.authorize("bash", args, {
				execution: { accesses, approvalRule, matchesRule, commandAnalysis },
			});
		};
		expect((await authorize("node -e \"console.log('review')\"")).approved).toBe(true);
		expect((await authorize("node -e \"console.log('review')\"")).reason).toBe("previously approved this session");
		expect(approvalHandler).toHaveBeenCalledTimes(1);
		await authorize("node -e \"console.log('different')\"");
		expect(approvalHandler).toHaveBeenCalledTimes(2);
	});

	it("rejects private and non-global IP literals before opening a network connection", async () => {
		for (const url of [
			"http://127.0.0.1/",
			"http://192.0.2.1/",
			"http://198.18.0.1/",
			"http://198.51.100.1/",
			"http://203.0.113.1/",
			"http://240.0.0.1/",
			"http://[::1]/",
			"http://[::ffff:127.0.0.1]/",
			"http://[fe90::1]/",
			"http://[ff02::1]/",
		]) {
			const result = await fetchUrlTool.execute!({ url }, {});
			expect(result.isError, url).toBe(true);
			expect(result.output, url).toContain("private/reserved");
		}
	});

	it("rejects a redirect from a public URL to a local address", async () => {
		const fetch = vi.fn().mockResolvedValue(
			new Response(null, { status: 302, headers: { location: "http://127.0.0.1/private" } }),
		);
		vi.stubGlobal("fetch", fetch);
		const result = await fetchUrlTool.execute!({ url: "https://8.8.8.8/start" }, {});
		expect(result.isError).toBe(true);
		expect(result.output).toContain("private/reserved");
		expect(fetch).toHaveBeenCalledTimes(1);
	});
});
