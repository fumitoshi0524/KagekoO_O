import { spawn } from "node:child_process";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { describe, expect, it } from "vitest";

const runner = path.join(import.meta.dirname, "tui-routes.pty.runner.mjs");

describe("public TUI route-entry smoke through a real PTY", () => {
	it("opens every canonical route in an isolated PTY owner process", async () => {
		const home = await mkdtemp(path.join(tmpdir(), "kageko-tui-routes-"));
		try {
			const result = await runRunner(home);
			expect(result.code, `${result.signal ?? "no-signal"}\n${result.output}`).toBe(0);
			expect(result.output).toContain(
				"PASS: 30 public + 1 hidden canonical TUI routes are unique; 7 aliases are disjoint (smoke only)",
			);
		} finally {
			// WinPTY can release its inherited cwd handle shortly after the owner
			// process closes.  The route smoke must not turn a fully successful UI run
			// into an EBUSY failure during that handoff.
			await new Promise((resolve) => setTimeout(resolve, 750));
			await rm(home, { recursive: true, force: true, maxRetries: 30, retryDelay: 250 });
		}
	}, 210_000);
});

function runRunner(home: string): Promise<{ code: number; signal: NodeJS.Signals | null; output: string }> {
	return new Promise((resolve, reject) => {
		const child = spawn(process.execPath, [runner], {
			cwd: path.resolve(import.meta.dirname, "../.."),
			windowsHide: true,
			env: { ...process.env, KAGEKO_PTY_HOME: home },
		});
		let output = "";
		const timeout = setTimeout(() => child.kill(), 195_000);
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
