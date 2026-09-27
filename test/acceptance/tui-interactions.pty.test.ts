import { spawn } from "node:child_process";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { describe, expect, it } from "vitest";

const runner = path.join(import.meta.dirname, "tui-interactions.pty.runner.mjs");

describe.skipIf(process.platform !== "win32")("interactive TUI journeys through a real Windows PTY", () => {
	it.each([
		["core", "core session, theme, memory, goal, cron and capability journeys"],
		["management", "aliases, activity, learner, trust, auth and settings panel journeys"],
		["lifecycle", "session lifecycle, timeline, compact, help and embedded-shell journeys"],
		["learning", "real proposal review plus generated tool, MCP and skill quality journeys"],
		["advanced", "plan, model, setup and plugin option journeys"],
		["graph", "worker profile fields, choices, tools, routing and deletion"],
		["matrix", "all setup menu entries and API-key routes without live OAuth requests"],
		["routing", "every model target/action shape and every built-in graph reset"],
		["catalog", "every help command entry and every provider credential entry"],
		["questions", "live question choices through model tool calls"],
		["approvals", "one-time, session and denied shell approvals"],
		["activities", "live activity-task output, cancellation, stop and history actions"],
		["mouse", "mouse input remains ignored while keyboard navigation works"],
	])(
		"executes %s interactions: %s",
		async (batch) => {
			const fixtureHome = await mkdtemp(path.join(tmpdir(), "kageko-tui-interactions-"));
			try {
				const result = await runRunner(fixtureHome, batch);
				expect(result.code, `${result.signal ?? "no-signal"}\n${result.output}`).toBe(0);
				expect(result.output).toContain(`PASS: ${batch} interactive TUI journeys completed`);
			} finally {
				// Windows releases the PTY child's cwd handle asynchronously after its
				// owner exits. Cleanup remains mandatory, but tolerates that short handoff.
				await new Promise((resolve) => setTimeout(resolve, 750));
				await rm(fixtureHome, { recursive: true, force: true, maxRetries: 30, retryDelay: 250 });
			}
		},
		2_400_000,
	);
});

function runRunner(
	fixtureHome: string,
	batch: string,
): Promise<{ code: number; signal: NodeJS.Signals | null; output: string }> {
	return new Promise((resolve, reject) => {
		const child = spawn(process.execPath, [runner, batch], {
			cwd: path.resolve(import.meta.dirname, "../.."),
			windowsHide: true,
			env: {
				...process.env,
				KAGEKO_PTY_HOME: fixtureHome,
				// Keep the parent runner safe too; it may be replaced by a wrapper
				// that starts an OAuth-capable child before its local env is built.
				KAGEKO_DISABLE_EXTERNAL_BROWSER: "1",
			},
		});
		let output = "";
		const timeout = setTimeout(() => child.kill(), batch === "approvals" ? 2_370_000 : 1_170_000);
		child.stdout.setEncoding("utf8");
		child.stderr.setEncoding("utf8");
		child.stdout.on("data", (chunk: string) => {
			output += chunk;
		});
		child.stderr.on("data", (chunk: string) => {
			output += chunk;
		});
		child.once("error", (error) => {
			clearTimeout(timeout);
			reject(error);
		});
		child.once("close", (code, signal) => {
			clearTimeout(timeout);
			resolve({ code: code ?? -1, signal, output });
		});
	});
}
