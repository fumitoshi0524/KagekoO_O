import { access, mkdtemp, rm, writeFile } from "node:fs/promises";
import { constants } from "node:fs";
import { spawn } from "node:child_process";
import { tmpdir } from "node:os";
import path from "node:path";
import { afterEach, describe, expect, it } from "vitest";

const root = path.resolve(import.meta.dirname, "../..");
const cli = path.join(root, "apps", "kageko", "dist", "main.mjs");
const homes: string[] = [];

afterEach(async () => {
	while (homes.length) await rm(homes.pop()!, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 });
});

describe("installed CLI contract", () => {
	it("runs the documented prompt subcommand as a complete headless turn", async () => {
		const home = await isolatedHome();
		const result = await run(home, [
			"prompt",
			"Exercise the production prompt command.",
			"--provider",
			"faux",
			"--model",
			"faux",
			"--permission",
			"unrestricted",
			"--interaction",
			"unattended",
			"--output",
			"stream-json",
		]);
		expect(result.code, result.stderr).toBe(0);
		const events = result.stdout
			.trim()
			.split("\n")
			.map((line) => JSON.parse(line) as { event?: { type?: string } });
		expect(events.some((entry) => entry.event?.type === "turn.started")).toBe(true);
		expect(events.some((entry) => entry.event?.type === "turn.end")).toBe(true);
	}, 120_000);

	it("is self-describing and rejects malformed public commands without source access", async () => {
		await access(cli, constants.R_OK | constants.X_OK);
		const home = await isolatedHome();
		const version = await run(home, ["--version"]);
		expect(version.code).toBe(0);
		expect(version.stdout).toMatch(/^kageko\s+\S+/i);
		for (const command of [
			"session",
			"config",
			"auth",
			"plugin",
			"task",
			"cron",
			"capability",
			"memory",
			"learning",
			"goal",
			"skill",
			"mcp",
			"trust",
			"setup",
		]) {
			const help = await run(home, [command, "--help"]);
			expect(help.code, help.stderr).toBe(0);
			expect(`${help.stdout}\n${help.stderr}`).toMatch(new RegExp(`kageko ${command}\\b`, "i"));
		}
		const rejected = await run(home, ["session", "delete", "not-a-session"]);
		expect(rejected.code).not.toBe(0);
		expect(`${rejected.stdout}\n${rejected.stderr}`).toMatch(/--yes|unknown|session/i);
	}, 120_000);

	it("persists a user-created session and explicit memory across two installed processes", async () => {
		const home = await isolatedHome();
		const created = await run(home, ["session", "create"]);
		expect(created.code, created.stderr).toBe(0);
		const sessionId = (JSON.parse(created.stdout) as { sessionId: string }).sessionId;
		expect(sessionId).toMatch(/^[0-9a-f-]{36}$/i);
		const remembered = await run(home, [
			"memory",
			"remember",
			"--session",
			sessionId,
			"A release needs passing tests and two approvals.",
		]);
		expect(remembered.code, remembered.stderr).toBe(0);
		const recalled = await run(home, ["memory", "recall", "--session", sessionId, "release approvals"]);
		expect(recalled.code, recalled.stderr).toBe(0);
		expect(recalled.stdout).toContain("passing tests and two approvals");
	}, 120_000);

	it("changes MCP configuration only with explicit workspace-trust consent", async () => {
		const home = await isolatedHome();
		const created = await run(home, ["session", "create", "--json"]);
		expect(created.code, created.stderr).toBe(0);
		const sessionId = (JSON.parse(created.stdout) as { sessionId: string }).sessionId;
		const server = path.join(home, "contract-mcp.cjs");
		await writeFile(server, mcpServerCode(), "utf8");
		const config = JSON.stringify({ command: process.execPath, args: [server] });

		const rejectedAdd = await run(home, ["mcp", "add", "contract", config, "--session", sessionId]);
		expect(rejectedAdd.code).not.toBe(0);
		expect(rejectedAdd.stderr).toMatch(/--trust-workspace/i);
		const beforeAdd = await run(home, ["config", "get", "--json"]);
		expect(
			(JSON.parse(beforeAdd.stdout) as { mcp?: { servers?: Record<string, unknown> } }).mcp?.servers?.["contract"],
		).toBe(undefined);

		const added = await run(home, [
			"mcp",
			"add",
			"contract",
			config,
			"--session",
			sessionId,
			"--trust-workspace",
		]);
		expect(added.code, added.stderr).toBe(0);
		const listed = await run(home, ["mcp", "list", "--session", sessionId, "--json"]);
		expect(listed.code, listed.stderr).toBe(0);
		expect(JSON.parse(listed.stdout)).toEqual(expect.arrayContaining([expect.objectContaining({ id: "contract" })]));

		const rejectedRemove = await run(home, ["mcp", "remove", "contract", "--session", sessionId, "--yes"]);
		expect(rejectedRemove.code).not.toBe(0);
		expect(rejectedRemove.stderr).toMatch(/--trust-workspace/i);
		const stillListed = await run(home, ["mcp", "list", "--session", sessionId, "--json"]);
		expect(JSON.parse(stillListed.stdout)).toEqual(
			expect.arrayContaining([expect.objectContaining({ id: "contract" })]),
		);

		const removed = await run(home, [
			"mcp",
			"remove",
			"contract",
			"--session",
			sessionId,
			"--yes",
			"--trust-workspace",
		]);
		expect(removed.code, removed.stderr).toBe(0);
		const afterRemove = await run(home, ["mcp", "list", "--session", sessionId, "--json"]);
		expect(JSON.parse(afterRemove.stdout)).not.toEqual(
			expect.arrayContaining([expect.objectContaining({ id: "contract" })]),
		);
	}, 120_000);

	it("keeps every public subcommand non-interactive when stdin is closed", async () => {
		const home = await isolatedHome();
		const created = await run(home, ["session", "create", "--json"]);
		expect(created.code, created.stderr).toBe(0);
		const sessionId = (JSON.parse(created.stdout) as { sessionId: string }).sessionId;

		// This is intentionally the installed executable, with an ignored stdin and
		// a per-process deadline.  It catches accidental prompts and TUI fallthroughs
		// that parser/unit tests cannot observe.
		const invocations: ReadonlyArray<readonly string[]> = [
			["session", "list", "--json"],
			["session", "resume", sessionId, "--json"],
			["session", "fork", sessionId, "--json"],
			["session", "compact", sessionId],
			["config", "get", "--json"],
			["config", "path", "project"],
			["config", "path", "user"],
			["auth", "status", "non-interactive-provider"],
			["auth", "login", "non-interactive-provider"],
			["plugin", "install"],
			["plugin", "uninstall", "missing-plugin"],
			["task", "list", "--session", sessionId, "--all", "--json"],
			["task", "output", "missing-task", "--session", sessionId],
			["task", "stop", "missing-task", "--session", sessionId],
			["cron", "list", "--session", sessionId, "--json"],
			["cron", "create", "--session", sessionId],
			["cron", "delete", "missing-cron", "--session", sessionId],
			...[undefined, "plugin", "skill", "mcp", "tool"].map(
				(kind) => ["capability", "list", "--session", sessionId, ...(kind ? ["--kind", kind] : []), "--json"] as const,
			),
			["memory", "status", "--session", sessionId, "--json"],
			["memory", "query", "--session", sessionId],
			["memory", "remember", "--session", sessionId],
			["memory", "recall", "--session", sessionId],
			["memory", "index", "--session", sessionId],
			["learning", "pending", "--session", sessionId, "--json"],
			["learning", "approve", "missing-event", "--session", sessionId],
			["learning", "reject", "missing-event", "--session", sessionId],
			["goal", "status", "--session", sessionId, "--json"],
			["goal", "create", "--session", sessionId],
			["goal", "pause", "--session", sessionId],
			["goal", "resume", "--session", sessionId],
			["goal", "complete", "--session", sessionId],
			["skill", "list", "--session", sessionId, "--json"],
			["skill", "reload", "--session", sessionId],
			["skill", "remove", "missing-skill"],
			["mcp", "list", "--session", sessionId, "--json"],
			["mcp", "add", "missing-config", "{}", "--session", sessionId],
			["mcp", "remove", "missing-mcp", "--session", sessionId],
			["mcp", "auth", "missing-mcp"],
			["trust", "status", "--json"],
			["trust", "grant"],
			["trust", "revoke"],
			["setup"],
		];

		for (const args of invocations) {
			const result = await run(home, args, 8_000);
			expect(result.timedOut, `hung: kageko ${args.join(" ")}\n${result.stdout}\n${result.stderr}`).toBe(false);
			if (args[0] === "setup") {
				expect(result.code).not.toBe(0);
				expect(result.stderr).toMatch(/interactive terminal/i);
			}
		}
	}, 180_000);

	it("refuses every destructive command unless confirmation is explicit", async () => {
		const home = await isolatedHome();
		const created = await run(home, ["session", "create", "--json"]);
		const sessionId = (JSON.parse(created.stdout) as { sessionId: string }).sessionId;
		for (const args of [
			["session", "delete", sessionId],
			["plugin", "uninstall", "missing-plugin"],
			["cron", "delete", "missing-cron", "--session", sessionId],
			["learning", "reject", "missing-event", "--session", sessionId],
			["skill", "remove", "missing-skill"],
			["mcp", "remove", "missing-mcp", "--session", sessionId],
			["auth", "remove", "missing-provider"],
			["trust", "revoke"],
		] as const) {
			const result = await run(home, args);
			expect(result.code, `unexpected success: kageko ${args.join(" ")}`).not.toBe(0);
			expect(`${result.stdout}\n${result.stderr}`).toMatch(/--yes|refus|usage/i);
		}
		const resumed = await run(home, ["session", "resume", sessionId, "--json"]);
		expect(resumed.code, resumed.stderr).toBe(0);
	}, 120_000);
});

async function isolatedHome(): Promise<string> {
	const home = await mkdtemp(path.join(tmpdir(), "kageko-acceptance-"));
	homes.push(home);
	return home;
}

function mcpServerCode(): string {
	return [
		"const readline = require('node:readline');",
		"readline.createInterface({ input: process.stdin }).on('line', (line) => {",
		"  const request = JSON.parse(line);",
		"  if (request.id === undefined) return;",
		"  const result = request.method === 'initialize'",
		"    ? { protocolVersion: '2025-06-18', capabilities: { tools: {} }, serverInfo: { name: 'contract', version: '1.0.0' } }",
		"    : request.method === 'tools/list' ? { tools: [] } : { content: [{ type: 'text', text: 'ok' }] };",
		"  process.stdout.write(JSON.stringify({ jsonrpc: '2.0', id: request.id, result }) + '\\n');",
		"});",
	].join("\n");
}

async function run(
	cwd: string,
	args: readonly string[],
	timeoutMs = 20_000,
): Promise<{ code: number; stdout: string; stderr: string; timedOut: boolean }> {
	return new Promise((resolve, reject) => {
		const child = spawn(process.execPath, [cli, ...args], {
			cwd,
			env: {
				...process.env,
				KAGEKO_HOME: cwd,
				KAGEKO_MODEL_PROVIDER: "faux",
				KAGEKO_MODEL_NAME: "faux",
				KAGEKO_MAX_CONTEXT_SIZE: "32768",
				KAGEKO_LOG_LEVEL: "off",
			},
			stdio: ["ignore", "pipe", "pipe"],
			windowsHide: true,
		});
		let stdout = "";
		let stderr = "";
		let timedOut = false;
		const timeout = setTimeout(() => {
			timedOut = true;
			child.kill();
		}, timeoutMs);
		child.stdout.setEncoding("utf8");
		child.stderr.setEncoding("utf8");
		child.stdout.on("data", (data: string) => {
			stdout += data;
		});
		child.stderr.on("data", (data: string) => {
			stderr += data;
		});
		child.once("error", (error) => {
			clearTimeout(timeout);
			reject(error);
		});
		child.once("close", (code) => {
			clearTimeout(timeout);
			resolve({ code: timedOut ? -1 : (code ?? -1), stdout, stderr, timedOut });
		});
	});
}
