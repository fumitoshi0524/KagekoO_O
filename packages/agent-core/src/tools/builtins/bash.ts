import { allAccess, literalApprovalRule, matchesRuleSubject } from "../accesses.js";
import type { Tool, ToolContext } from "../types.js";
import { analyzeCommand } from "../../security/command-analysis/index.js";

const OUTPUT_CAP = 1024 * 1024; // 1 MiB

export const BASH_DEFAULT_TIMEOUT_MS = 60_000;
export const BASH_MAX_TIMEOUT_MS = 300_000; // kimi-code foreground max: 5 minutes

export interface BashToolOptions {
	/** Timeout applied when a call does not request one. */
	defaultTimeoutMs?: number;
	/** Upper bound applied to any requested timeout. */
	maxTimeoutMs?: number;
}

export function createBashTool({
	defaultTimeoutMs = BASH_DEFAULT_TIMEOUT_MS,
	maxTimeoutMs = BASH_MAX_TIMEOUT_MS,
}: BashToolOptions = {}): Tool<{ command: string; background?: boolean; timeout?: number }> {
	return {
		name: "bash",
		description:
			"Run a shell command. Use with care; destructive commands require confirmation. Set background=true to run it as a background task.",
		parameters: {
			type: "object",
			properties: {
				command: { type: "string", description: "Shell command to run" },
				background: { type: "boolean", description: "Run as a background task and return a task_id" },
				timeout: {
					type: "number",
					description: `Maximum milliseconds to wait for the command (default ${defaultTimeoutMs}, max ${maxTimeoutMs})`,
				},
			},
			required: ["command"],
		},
		resolveExecution({ command }: { command: string; background?: boolean; timeout?: number }, context?: ToolContext) {
			const kaos = context?.kaos;
			const analysis = analyzeCommand(command, {
				dialect: kaos?.shellDialect ?? (process.platform === "win32" ? "powershell" : "bash"),
				shellExecutable: kaos?.shellExecutable,
				cwd: kaos?.cwd ?? process.cwd(),
			});
			return {
				accesses: analysis.accesses.length ? analysis.accesses : allAccess(),
				approvalRule: literalApprovalRule("bash", command),
				matchesRule: (ruleArgs) => matchesRuleSubject(ruleArgs, command),
				execute: this.execute,
				commandAnalysis: analysis,
			};
		},
		async execute(
			{ command, background, timeout }: { command: string; background?: boolean; timeout?: number },
			{ kaos, tracker }: ToolContext,
		) {
			if (!kaos) return { output: "Shell workspace is not available.", isError: true };
			if (!tracker) return { output: "Process tracker is not available.", isError: true };
			const timeoutMs =
				Number.isFinite(timeout) && timeout! > 0 ? Math.min(timeout!, maxTimeoutMs) : defaultTimeoutMs;

			const invocation = kaos.shellInvocation(command);

			const tracked = await tracker.spawnDurable(invocation.command, invocation.args, {
				cwd: kaos.cwd,
				env: kaos.env,
				command,
				background,
			});

			if (background) {
				return {
					output: `Started background task ${tracked.taskId}: ${command}`,
					task_id: tracked.taskId,
				};
			}

			const { exitCode, error, timedOut } = await tracked.wait(timeoutMs);
			if (timedOut) {
				await tracked.kill({ reason: "Foreground shell command timed out", status: "timed_out" });
			}
			const stdout = tracked.stdout.text();
			const stderr = tracked.stderr.text();

			const parts = [stdout, stderr ? `stderr:\n${stderr}` : ""].filter(Boolean);
			if (tracked.stdout.truncated() || tracked.stderr.truncated()) {
				parts.push(`\n[output truncated at ${OUTPUT_CAP} bytes]`);
			}
			if (timedOut) {
				parts.push("\n[command timed out and was terminated]");
			}
			if (error) {
				parts.push(`\n[spawn error: ${error}]`);
			}

			return {
				output: parts.join("\n"),
				isError: timedOut || (exitCode ?? 0) !== 0,
			};
		},
	};
}

export const bashTool: Tool<{ command: string; background?: boolean; timeout?: number }> = createBashTool();
