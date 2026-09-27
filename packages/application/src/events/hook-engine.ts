import { spawn, type ChildProcess } from "node:child_process";
import * as path from "node:path";
import * as fs from "node:fs/promises";
import { scrubEnvironment } from "@kageko/kaos";
import { validateEnv } from "@kageko/agent-core";

const HOOK_OUTPUT_CAP = 64 * 1024;
const KAGEKO_ARGS_MAX_BYTES = 32 * 1024;

export type HookEventName =
	| "PreToolUse"
	| "PostToolUse"
	| "PostToolUseFailure"
	| "PermissionRequest"
	| "PermissionResult"
	| "UserPromptSubmit"
	| "Stop"
	| "StopFailure"
	| "Interrupt"
	| "SessionStart"
	| "SessionEnd"
	| "SubagentStart"
	| "SubagentStop"
	| "PreCompact"
	| "PostCompact"
	| "Notification"
	| (string & {});

export interface HookDefinition {
	event: string;
	command: string;
	matcher?: Record<string, unknown>;
	timeout?: number;
	cwd?: string;
	env?: Record<string, string>;
	allowSensitiveEnv?: boolean;
}

export interface HookResult {
	action?: "allow" | "block" | string;
	reason?: string;
	message?: string;
	stdout?: string;
	stderr?: string;
	exitCode?: number | null;
	error?: string;
	timedOut?: boolean;
	[key: string]: unknown;
}

export interface HookTriggerOptions {
	signal?: AbortSignal;
}

export interface HookEngineOptions {
	cwd?: string;
	tracker?: ProcessTrackerLike;
}

export interface ProcessTrackerLike {
	spawnDurable(command: string, args: string[], options: Record<string, unknown>): Promise<TrackedProcessLike>;
}

export interface TrackedProcessLike {
	proc: ChildProcess | null;
	stdout?: { text(): string };
	stderr?: { text(): string };
	wait(timeout: number): Promise<{ exitCode: number | null; timedOut?: boolean } | null>;
	kill(options: { reason: string }): Promise<unknown> | unknown;
}

interface CollectedOutput {
	stdout: string;
	stderr: string;
	exitCode: number | null;
	timedOut?: boolean;
	error?: string;
}

/**
 * Hook engine: runs external commands in response to session/loop events.
 *
 * Supported event types (mirroring kimi-code):
 *   PreToolUse, PostToolUse, PostToolUseFailure, PermissionRequest, PermissionResult,
 *   UserPromptSubmit, Stop, StopFailure, Interrupt, SessionStart, SessionEnd,
 *   SubagentStart, SubagentStop, PreCompact, PostCompact, Notification
 *
 * Commands receive `KAGEKO_EVENT` and `KAGEKO_ARGS` in their environment.
 * If stdout is valid JSON, it is returned as-is; otherwise a default allow
 * envelope is used. The first `action: "block"` result wins in triggerBlock.
 */
export class HookEngine {
	readonly hooks: HookDefinition[];
	readonly cwd: string;
	readonly tracker?: ProcessTrackerLike;

	constructor(hooks: HookDefinition[] = [], { cwd, tracker }: HookEngineOptions = {}) {
		this.hooks = hooks;
		this.cwd = cwd ?? process.cwd();
		this.tracker = tracker;
	}

	async trigger(
		event: string,
		args: Record<string, unknown> = {},
		{ signal }: HookTriggerOptions = {},
	): Promise<HookResult[]> {
		const matches = this.hooks.filter((h) => h.event === event && this._match(h.matcher, args));
		if (matches.length === 0) return [];
		return Promise.all(matches.map((h) => this._run(h, args, { signal })));
	}

	async triggerBlock(
		event: string,
		args: Record<string, unknown> = {},
		{ signal }: HookTriggerOptions = {},
	): Promise<HookResult | undefined> {
		const results = await this.trigger(event, args, { signal });
		return results.find((r) => r?.action === "block");
	}

	async fireAndForgetTrigger(
		event: string,
		args: Record<string, unknown> = {},
		{ signal }: HookTriggerOptions = {},
	): Promise<HookResult[]> {
		this.trigger(event, args, { signal }).catch(() => {});
		return [];
	}

	private _match(matcher: Record<string, unknown> | undefined, args: Record<string, unknown>): boolean {
		if (!matcher || typeof matcher !== "object") return true;
		for (const [key, value] of Object.entries(matcher)) {
			if (args[key] !== value) return false;
		}
		return true;
	}

	private async _run(
		hook: HookDefinition,
		args: Record<string, unknown>,
		{ signal }: HookTriggerOptions = {},
	): Promise<HookResult> {
		if (signal?.aborted) {
			return { action: "allow", error: "hook aborted before start" };
		}
		const command = hook.command;
		const argv = parseHookCommand(command);
		if (!argv) {
			return { action: "allow", error: `Unsafe hook command rejected: ${command}` };
		}
		if (!validateEnv(hook.env)) {
			return { action: "allow", error: `Hook env contains unsafe variables` };
		}
		const cwd = hook.cwd ? path.resolve(this.cwd, hook.cwd) : this.cwd;
		if (!isInsideWorkspace(cwd, this.cwd)) {
			return { action: "allow", error: `Hook cwd outside workspace: ${hook.cwd}` };
		}
		let commandPath = argv[0]!;
		if (path.isAbsolute(commandPath) || commandPath.includes("/") || commandPath.includes("\\")) {
			commandPath = path.resolve(cwd, commandPath);
			if (!isInsideWorkspace(commandPath, this.cwd)) {
				return { action: "allow", error: `Hook command path outside workspace: ${argv[0]}` };
			}
		}
		const realCommand = await fs.realpath(commandPath).catch(() => commandPath);
		if (isUnsafeShell(realCommand)) {
			return { action: "allow", error: `Hook command is a shell interpreter: ${argv[0]}` };
		}
		const env = scrubEnvironment(
			{
				...process.env,
				KAGEKO_EVENT: hook.event,
				KAGEKO_ARGS: safeStringifyForEnv(args),
				...(hook.env ?? {}),
			},
			{ allowSensitive: hook.allowSensitiveEnv === true },
		);
		const timeout = Math.max(0, Number.isFinite(hook.timeout) ? hook.timeout! : 30000);

		let tracked: TrackedProcessLike | undefined;
		let proc: ChildProcess | null = null;
		const onAbort = () => {
			try {
				if (tracked) {
					tracked.kill({ reason: "hook aborted" });
				} else {
					proc?.kill("SIGKILL");
				}
			} catch {
				/* best effort */
			}
		};
		if (signal) {
			signal.addEventListener("abort", onAbort, { once: true });
		}
		try {
			let stdout = "";
			let stderr = "";
			let exitCode: number | null | undefined;

			if (this.tracker) {
				tracked = await this.tracker.spawnDurable(realCommand, argv.slice(1), {
					shell: false,
					cwd,
					env,
					command,
					allowSensitiveEnv: hook.allowSensitiveEnv === true,
				});
				proc = tracked.proc;
				const result = await tracked.wait(timeout);
				stdout = capHookOutput(tracked.stdout?.text() ?? "");
				stderr = capHookOutput(tracked.stderr?.text() ?? "");
				exitCode = result?.exitCode ?? null;
				if (result?.timedOut) {
					await tracked.kill({ reason: "hook timeout" });
					return { action: "allow", stdout, stderr, exitCode, timedOut: true };
				}
			} else {
				proc = spawn(realCommand, argv.slice(1), { shell: false, cwd, env });
				const result = await this._collect(proc, timeout);
				stdout = result.stdout;
				stderr = result.stderr;
				exitCode = result.exitCode;
			}

			try {
				return JSON.parse(stdout) as HookResult;
			} catch {
				return { action: "allow", stdout, stderr, exitCode };
			}
		} catch (err) {
			return { action: "allow", error: (err as Error).message };
		} finally {
			if (signal) {
				signal.removeEventListener("abort", onAbort);
			}
		}
	}

	private _collect(proc: ChildProcess, timeout: number): Promise<CollectedOutput> {
		return new Promise((resolve) => {
			let stdout = "";
			let stderr = "";
			let stdoutCapped = false;
			let stderrCapped = false;
			const onStdoutData = (d: unknown) => {
				if (stdoutCapped) return;
				const s = String(d);
				if (stdout.length + s.length > HOOK_OUTPUT_CAP) {
					stdout += s.slice(0, HOOK_OUTPUT_CAP - stdout.length);
					stdoutCapped = true;
				} else {
					stdout += s;
				}
			};
			const onStderrData = (d: unknown) => {
				if (stderrCapped) return;
				const s = String(d);
				if (stderr.length + s.length > HOOK_OUTPUT_CAP) {
					stderr += s.slice(0, HOOK_OUTPUT_CAP - stderr.length);
					stderrCapped = true;
				} else {
					stderr += s;
				}
			};
			proc.stdout?.on("data", onStdoutData);
			proc.stderr?.on("data", onStderrData);
			const timer = setTimeout(() => {
				try {
					proc.kill("SIGKILL");
				} catch {
					/* best effort */
				}
				cleanup();
				resolve({ stdout, stderr, exitCode: null, timedOut: true });
			}, timeout);
			const cleanup = () => {
				clearTimeout(timer);
				proc.stdout?.off("data", onStdoutData);
				proc.stderr?.off("data", onStderrData);
				proc.off("close", onClose);
				proc.off("error", onError);
			};
			const onClose = (exitCode: number | null) => {
				cleanup();
				resolve({ stdout, stderr, exitCode: exitCode ?? 0 });
			};
			const onError = (err: Error) => {
				cleanup();
				resolve({ stdout, stderr, exitCode: null, error: err.message });
			};
			proc.on("close", onClose);
			proc.on("error", onError);
		});
	}
}

const SAFE_COMMAND_RE = /^[A-Za-z0-9_./~+-]+$/;

const UNSAFE_SHELLS = new Set([
	"sh",
	"bash",
	"zsh",
	"fish",
	"csh",
	"ksh",
	"tcsh",
	"cmd",
	"cmd.exe",
	"powershell",
	"powershell.exe",
	"pwsh",
	"pwsh.exe",
]);

function commandBasename(command: string): string {
	return path.basename(command, path.extname(command)).toLowerCase();
}

export function isUnsafeShell(command: string): boolean {
	return UNSAFE_SHELLS.has(commandBasename(command));
}

export function parseHookCommand(command: string): string[] | null {
	if (typeof command !== "string" || command.length === 0) return null;
	// Split respecting single and double quotes. This is intentionally strict:
	// no shell metacharacters, no redirections, no pipes, no command chaining.
	const argv: string[] = [];
	let current = "";
	let quote: string | null = null;
	for (let i = 0; i < command.length; i++) {
		const ch = command[i]!;
		if (quote) {
			if (ch === quote) {
				quote = null;
			} else {
				current += ch;
			}
		} else if (ch === '"' || ch === "'") {
			quote = ch;
		} else if (/[;&|<>`]/.test(ch) || (ch === "$" && command[i + 1] === "(")) {
			return null;
		} else if (/\s/.test(ch)) {
			if (current.length > 0) {
				argv.push(current);
				current = "";
			}
		} else {
			current += ch;
		}
	}
	if (quote !== null) return null;
	if (current.length > 0) argv.push(current);
	if (argv.length === 0) return null;
	// Only the executable/command itself must be a safe path. Arguments are passed
	// verbatim to spawn with shell: false, so arbitrary (non-shell) content is safe.
	if (!SAFE_COMMAND_RE.test(argv[0]!)) return null;
	if (argv[0]!.includes("..")) return null;
	if (isUnsafeShell(argv[0]!)) return null;
	return argv;
}

function capHookOutput(value: string): string {
	if (Buffer.byteLength(value, "utf8") <= HOOK_OUTPUT_CAP) return value;
	let end = Math.min(value.length, HOOK_OUTPUT_CAP);
	while (end > 0 && Buffer.byteLength(value.slice(0, end), "utf8") > HOOK_OUTPUT_CAP) end -= 1;
	return value.slice(0, end);
}

function isInsideWorkspace(filePath: string, cwd: string): boolean {
	const rel = path.relative(cwd, filePath);
	return !rel.startsWith("..") && !path.isAbsolute(rel);
}

function safeStringifyForEnv(value: unknown): string {
	let text: string;
	try {
		text = JSON.stringify(value);
	} catch {
		text = '"[unserializable arguments]"';
	}
	if (Buffer.byteLength(text, "utf8") > KAGEKO_ARGS_MAX_BYTES) {
		return '"[arguments too large]"';
	}
	return text;
}
