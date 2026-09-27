import { spawn } from "node:child_process";
import type { ChildProcess, SpawnOptions } from "node:child_process";
import * as fs from "node:fs/promises";
import { createWriteStream, mkdirSync } from "node:fs";
import type { WriteStream } from "node:fs";
import type { Readable } from "node:stream";
import * as path from "node:path";
import * as crypto from "node:crypto";
import { safeInheritedEnvironment, scrubEnvironment } from "@kageko/kaos";
import { SessionProcessSupervisor } from "./supervisor.js";
import type { SupervisorTaskInfo } from "./types.js";

const OUTPUT_CAP = 50 * 1024; // bounded live memory per stream
const MAX_PERSISTED_OUTPUT_BYTES = 50 * 1024 * 1024;
const SNAPSHOT_BYTES = 32 * 1024;
const MAX_OUTPUT_READ_BYTES = 64 * 1024;
const DEFAULT_KILL_GRACE_MS = 5000;
const WINDOWS_TREE_KILL_START_GRACE_MS = 250;
const DEFAULT_TERMINAL_TTL_MS = 24 * 60 * 60 * 1000;
const DEFAULT_MAX_TASKS = 100;
const DEFAULT_MAX_CONCURRENT = 32;
const DEFAULT_SUPERVISOR_POLL_INTERVAL_MS = 250;

export type TaskStatus = "running" | "completed" | "failed" | "killed" | "timed_out" | "lost";

export interface TaskInfo {
	taskId: string;
	pid: number | undefined;
	status: TaskStatus;
	stopReason: string | undefined;
	command: string;
	background: boolean;
	startedAt: number;
	endedAt: number | undefined;
	exitCode: number | null | undefined;
	outputPath: string | undefined;
}

export interface TaskExitResult {
	exitCode: number | null;
	error?: string;
	info: TaskInfo;
	timedOut?: boolean;
}

export interface OutputSnapshot {
	preview: string;
	outputSizeBytes: number;
	previewBytes: number;
	truncated: boolean;
	fullOutputAvailable: boolean;
	persistedOutputTruncated: boolean;
	outputPath: string | undefined;
}

export interface OutputChunk {
	content: string;
	offset: number;
	nextOffset: number;
	totalBytes: number;
	eof: boolean;
	persistedOutputTruncated: boolean;
}

/**
 * Reads a supervisor-owned task log after its runtime has been reconstructed.
 * The task id is constrained before joining it into the private runtime path,
 * so this public recovery API cannot escape the process-supervisor log root.
 */
export async function readPersistedTaskOutput(
	sessionDir: string,
	taskId: string,
	offset = 0,
	limit = MAX_OUTPUT_READ_BYTES,
): Promise<OutputChunk | undefined> {
	if (!/^[A-Za-z0-9-]{1,128}$/.test(taskId)) throw new Error("Invalid task id");
	const outputPath = path.join(path.resolve(sessionDir), "tasks", `${taskId}.log`);
	const safeOffset = Number.isSafeInteger(offset) && offset >= 0 ? offset : 0;
	const safeLimit =
		Number.isSafeInteger(limit) && limit > 0 ? Math.min(limit, MAX_OUTPUT_READ_BYTES) : MAX_OUTPUT_READ_BYTES;
	let handle: fs.FileHandle | undefined;
	try {
		const stat = await fs.stat(outputPath);
		const start = Math.min(safeOffset, stat.size);
		const length = Math.min(safeLimit, stat.size - start);
		handle = await fs.open(outputPath, "r");
		const { buffer, bytesRead } = await handle.read(Buffer.alloc(length), 0, length, start);
		return {
			content: buffer.subarray(0, bytesRead).toString("utf-8"),
			offset: start,
			nextOffset: start + bytesRead,
			totalBytes: stat.size,
			eof: start + bytesRead >= stat.size,
			persistedOutputTruncated: stat.size >= MAX_PERSISTED_OUTPUT_BYTES,
		};
	} catch (error) {
		if ((error as NodeJS.ErrnoException).code === "ENOENT") return undefined;
		throw error;
	} finally {
		await handle?.close().catch(() => {});
	}
}

export interface ProcessTrackerOptions {
	sessionDir?: string;
	terminalTtlMs?: number;
	maxTasks?: number;
	maxConcurrent?: number;
	supervisorPollIntervalMs?: number;
	onTaskEvent?: (event: ProcessTaskEvent) => void | Promise<void>;
	supervisor?: SessionProcessSupervisor;
	ownsSupervisor?: boolean;
}

export interface ProcessTaskEvent {
	phase: "requested" | "started" | "terminated";
	task: TaskInfo;
}

export interface TrackedSpawnOptions extends SpawnOptions {
	command?: string;
	background?: boolean;
	/** Explicitly allow credential-bearing variables in the child environment. */
	allowSensitiveEnv?: boolean;
}

export interface KillOptions {
	signal?: NodeJS.Signals | number;
	reason?: string;
	graceMs?: number;
	status?: "killed" | "timed_out";
}

export interface CollectedOutput {
	text(): string;
	truncated(): boolean;
	close(): void;
	removeListeners?: () => void;
}

export interface TrackedProcessHandle {
	readonly taskId: string;
	readonly proc: ChildProcess | null;
	readonly background: boolean;
	readonly startedAt: number;
	endedAt: number | undefined;
	exitCode: number | null | undefined;
	status: TaskStatus;
	stopReason: string | undefined;
	readonly outputPath: string | undefined;
	readonly stdout: CollectedOutput;
	readonly stderr: CollectedOutput;
	readonly isTerminal: boolean;
	wait(timeoutMs?: number): Promise<TaskExitResult>;
	kill(options?: KillOptions): Promise<void>;
	outputSnapshot(previewBytes?: number): Promise<OutputSnapshot>;
	readOutput(offset?: number, limit?: number): Promise<OutputChunk>;
	toInfo(): TaskInfo;
	dispose(): void;
}

/**
 * Tracks spawned child processes and provides cross-platform tree cleanup.
 *
 * Also acts as a simple background-task manager: each spawn gets an 8-hex
 * task id, output is persisted to disk, and callers can list/get/wait/stop
 * tasks.
 */
export class ProcessTracker {
	readonly tasks = new Map<string, TrackedProcessHandle>();
	readonly sessionDir: string | undefined;
	private _closing = false;
	private _stopped = false;
	private _stopAllPromise: Promise<void> | undefined;
	private _supervisorStopped = false;
	readonly terminalTtlMs: number;
	readonly maxTasks: number;
	readonly maxConcurrent: number;
	private readonly _onTaskEvent?: (event: ProcessTaskEvent) => void | Promise<void>;
	private _observerChain: Promise<void> = Promise.resolve();
	private _observerError: Error | undefined;
	private readonly _startedPublished = new Set<string>();
	private readonly _pendingTerminalEvents = new Map<string, TaskInfo>();
	private readonly _supervisor?: SessionProcessSupervisor;
	private readonly _ownsSupervisor: boolean;
	private readonly _supervisorPollIntervalMs: number;

	constructor({
		sessionDir,
		terminalTtlMs,
		maxTasks,
		maxConcurrent,
		onTaskEvent,
		supervisor,
		supervisorPollIntervalMs,
		ownsSupervisor = true,
	}: ProcessTrackerOptions = {}) {
		this.sessionDir = sessionDir ? path.resolve(sessionDir) : undefined;
		this.terminalTtlMs = terminalTtlMs ?? DEFAULT_TERMINAL_TTL_MS;
		this.maxTasks = maxTasks ?? DEFAULT_MAX_TASKS;
		this.maxConcurrent = maxConcurrent ?? DEFAULT_MAX_CONCURRENT;
		this._onTaskEvent = onTaskEvent;
		this._supervisor = supervisor;
		this._ownsSupervisor = ownsSupervisor;
		this._supervisorPollIntervalMs = Math.max(25, supervisorPollIntervalMs ?? DEFAULT_SUPERVISOR_POLL_INTERVAL_MS);
	}

	fork(): ProcessTracker {
		return new ProcessTracker({
			sessionDir: this.sessionDir,
			terminalTtlMs: this.terminalTtlMs,
			maxTasks: this.maxTasks,
			maxConcurrent: this.maxConcurrent,
			onTaskEvent: this._onTaskEvent,
			supervisor: this._supervisor,
			supervisorPollIntervalMs: this._supervisorPollIntervalMs,
			ownsSupervisor: false,
		});
	}

	/**
	 * Spawn a tracked process.
	 */
	spawn(command: string, args: string[] = [], options: TrackedSpawnOptions = {}): TrackedProcess {
		if (this._onTaskEvent) {
			throw new Error("ProcessTracker with lifecycle persistence requires spawnDurable() write-ahead");
		}
		return this._spawn(crypto.randomUUID(), command, args, options, undefined, true);
	}

	async spawnDurable(
		command: string,
		args: string[] = [],
		options: TrackedSpawnOptions = {},
	): Promise<TrackedProcessHandle> {
		if (!this._onTaskEvent) return this.spawn(command, args, options);
		const taskId = crypto.randomUUID();
		const requestedAt = Date.now();
		await this._notifyRequired({
			phase: "requested",
			task: {
				taskId,
				pid: undefined,
				status: "running",
				stopReason: undefined,
				command: options.command ?? [command, ...args].join(" "),
				background: options.background ?? false,
				startedAt: requestedAt,
				endedAt: undefined,
				exitCode: undefined,
				outputPath: undefined,
			},
		});
		const tracked = this._supervisor
			? await this._spawnSupervised(taskId, command, args, options)
			: this._spawn(taskId, command, args, options, requestedAt, false);
		try {
			this._publishStarted(tracked);
			await this.flushEvents();
			return tracked;
		} catch (error) {
			await tracked.kill({ reason: "Lifecycle journal failed after process creation", graceMs: 1000 });
			throw error;
		}
	}

	private async _spawnSupervised(
		taskId: string,
		command: string,
		args: string[],
		options: TrackedSpawnOptions,
	): Promise<SupervisedTrackedProcess> {
		if (!this._supervisor || !this.sessionDir)
			throw new Error("Supervisor-backed tracking requires a private session directory");
		if (this._closing) throw new Error("ProcessTracker is shutting down; cannot spawn new processes");
		this._pruneTerminal();
		if (Array.from(this.tasks.values()).filter((task) => !task.isTerminal).length >= this.maxConcurrent) {
			throw new Error(`ProcessTracker concurrent task limit (${this.maxConcurrent}) reached`);
		}
		const cwd = typeof options.cwd === "string" ? options.cwd : process.cwd();
		const info = await this._supervisor.spawn({
			taskId,
			command,
			args,
			cwd,
			env: options.env as Record<string, string | undefined> | undefined,
			allowSensitiveEnv: options.allowSensitiveEnv === true,
			background: options.background ?? false,
			logPath: path.join(this.sessionDir, "tasks", `${taskId}.log`),
		});
		const tracked = new SupervisedTrackedProcess({
			supervisor: this._supervisor,
			info,
			command: options.command ?? [command, ...args].join(" "),
			pollIntervalMs: this._supervisorPollIntervalMs,
			onTerminal: (task) => this._publishTerminal(task),
			onDispose: () => this._pruneTerminal(),
		});
		this.tasks.set(taskId, tracked);
		return tracked;
	}

	private _spawn(
		taskId: string,
		command: string,
		args: string[],
		options: TrackedSpawnOptions,
		startedAt: number | undefined,
		notifyStarted: boolean,
	): TrackedProcess {
		if (this._closing) {
			throw new Error("ProcessTracker is shutting down; cannot spawn new processes");
		}
		this._pruneTerminal();
		if (Array.from(this.tasks.values()).filter((task) => !task.isTerminal).length >= this.maxConcurrent) {
			throw new Error(`ProcessTracker concurrent task limit (${this.maxConcurrent}) reached`);
		}
		const isWindows = process.platform === "win32";
		const { background, allowSensitiveEnv, ...spawnOptions } = options;
		const env = spawnOptions.env
			? scrubEnvironment(spawnOptions.env as Record<string, string | undefined>, {
					allowSensitive: allowSensitiveEnv === true,
				})
			: safeInheritedEnvironment(process.env, { allowSensitive: allowSensitiveEnv === true });
		const proc = spawn(command, args, {
			...spawnOptions,
			env,
			detached: isWindows ? false : true,
			stdio: ["ignore", "pipe", "pipe"],
		});

		if (this.tasks.has(taskId)) throw new Error(`Duplicate process task id: ${taskId}`);
		const tracked = new TrackedProcess({
			taskId,
			proc,
			isWindows,
			sessionDir: this.sessionDir,
			displayCommand: options.command ?? [command, ...args].join(" "),
			background: background ?? false,
			onDispose: () => this._pruneTerminal(),
			onTerminal: (task) => this._publishTerminal(task),
			startedAt,
		});
		this.tasks.set(taskId, tracked);
		if (notifyStarted) this._publishStarted(tracked);
		return tracked;
	}

	list(activeOnly = true, limit = 20): TaskInfo[] {
		this._pruneTerminal();
		const tasks = Array.from(this.tasks.values());
		const filtered = activeOnly ? tasks.filter((t) => !t.isTerminal) : tasks;
		return filtered
			.sort((a, b) => b.startedAt - a.startedAt)
			.slice(0, limit)
			.map((t) => t.toInfo());
	}

	private _pruneTerminal(): void {
		const now = Date.now();
		for (const [id, task] of this.tasks) {
			if (task.isTerminal && task.endedAt !== undefined && now - task.endedAt > this.terminalTtlMs)
				this.tasks.delete(id);
		}
		const terminal = Array.from(this.tasks.values())
			.filter((task) => task.isTerminal)
			.sort((a, b) => b.startedAt - a.startedAt);
		for (const task of terminal.slice(this.maxTasks)) {
			this.tasks.delete(task.taskId);
		}
	}

	getTask(taskId: string): TaskInfo | undefined {
		this._pruneTerminal();
		return this.tasks.get(taskId)?.toInfo();
	}

	async wait(taskId: string, timeoutMs = 30000): Promise<TaskExitResult | undefined> {
		const tracked = this.tasks.get(taskId);
		if (!tracked) return undefined;
		return tracked.wait(timeoutMs);
	}

	async stop(
		taskId: string,
		reason = "Stopped by TaskStop",
		{ graceMs }: { graceMs?: number } = {},
	): Promise<TaskInfo | undefined> {
		const tracked = this.tasks.get(taskId);
		if (!tracked) return undefined;
		await tracked.kill({ reason, graceMs });
		return tracked.toInfo();
	}

	async getOutputSnapshot(taskId: string, previewBytes = SNAPSHOT_BYTES): Promise<OutputSnapshot | undefined> {
		this._pruneTerminal();
		const tracked = this.tasks.get(taskId);
		if (!tracked) return undefined;
		return tracked.outputSnapshot(previewBytes);
	}

	async readOutput(taskId: string, offset = 0, limit = MAX_OUTPUT_READ_BYTES): Promise<OutputChunk | undefined> {
		this._pruneTerminal();
		const tracked = this.tasks.get(taskId);
		if (!tracked) return undefined;
		return tracked.readOutput(offset, limit);
	}

	/**
	 * Kill every tracked process and wait for them to actually exit.
	 */
	async stopAll(): Promise<void> {
		if (this._stopped) return;
		if (this._stopAllPromise) return this._stopAllPromise;
		this._closing = true;
		this._stopAllPromise = (async () => {
			const tasks = Array.from(this.tasks.values());
			const failures: unknown[] = [];
			const stopped = await Promise.allSettled(tasks.map((task) => task.kill()));
			for (const result of stopped) if (result.status === "rejected") failures.push(result.reason);
			try {
				await this.flushEvents();
			} catch (error) {
				failures.push(error);
			}
			try {
				if (this._ownsSupervisor && !this._supervisorStopped) {
					await this._supervisor?.shutdown();
					this._supervisorStopped = true;
				}
			} catch (error) {
				failures.push(error);
			}
			if (failures.length) throw new AggregateError(failures, "Process tracker shutdown failed");
			this.tasks.clear();
			this._startedPublished.clear();
			this._pendingTerminalEvents.clear();
			this._stopped = true;
		})();
		try {
			await this._stopAllPromise;
		} catch (error) {
			// Keep failed task handles and the supervisor owner reachable so a
			// higher-level session close can retry instead of losing processes.
			this._stopAllPromise = undefined;
			throw error;
		}
	}

	async flushEvents(): Promise<void> {
		await this._observerChain;
		if (this._observerError) throw this._observerError;
	}

	/**
	 * Kill tracked foreground processes (non-background tasks) and wait for
	 * them to actually exit (up to a short deadline).
	 */
	async stopForeground(): Promise<void> {
		const foreground = Array.from(this.tasks.values()).filter((p) => !p.background);
		const results = await Promise.allSettled(foreground.map((p) => p.kill({ reason: "Turn aborted", graceMs: 2000 })));
		const failures = results.filter((result): result is PromiseRejectedResult => result.status === "rejected");
		if (failures.length)
			throw new AggregateError(
				failures.map((failure) => failure.reason),
				"Failed to stop foreground processes",
			);
	}

	private _notify(event: ProcessTaskEvent): void {
		if (!this._onTaskEvent) return;
		this._observerChain = this._observerChain
			.then(() => this._onTaskEvent?.(event))
			.then(() => undefined)
			.catch((error: unknown) => {
				this._observerError = error instanceof Error ? error : new Error(String(error));
			});
	}

	private _publishStarted(tracked: TrackedProcessHandle): void {
		this._startedPublished.add(tracked.taskId);
		this._notify({
			phase: "started",
			task: {
				...tracked.toInfo(),
				status: "running",
				endedAt: undefined,
				exitCode: undefined,
				stopReason: undefined,
			},
		});
		const pending = this._pendingTerminalEvents.get(tracked.taskId);
		if (pending) {
			this._pendingTerminalEvents.delete(tracked.taskId);
			this._publishTerminal(pending);
		}
	}

	private _publishTerminal(task: TaskInfo): void {
		if (!this._startedPublished.has(task.taskId)) {
			this._pendingTerminalEvents.set(task.taskId, task);
			return;
		}
		this._startedPublished.delete(task.taskId);
		this._notify({ phase: "terminated", task });
	}

	private async _notifyRequired(event: ProcessTaskEvent): Promise<void> {
		if (!this._onTaskEvent) return;
		if (this._observerError) throw this._observerError;
		const publish = this._observerChain.then(() => this._onTaskEvent?.(event)).then(() => undefined);
		this._observerChain = publish.catch((error: unknown) => {
			this._observerError = error instanceof Error ? error : new Error(String(error));
		});
		await publish;
	}
}

type ExitPromiseResult = number | null | { error: Error };

interface TrackedProcessOptions {
	taskId: string;
	proc: ChildProcess;
	isWindows: boolean;
	sessionDir?: string | undefined;
	displayCommand: string;
	background?: boolean;
	onDispose: () => void;
	onTerminal: (task: TaskInfo) => void;
	startedAt?: number;
}

export class TrackedProcess {
	readonly taskId: string;
	readonly proc: ChildProcess;
	readonly isWindows: boolean;
	readonly onDispose: () => void;
	readonly onTerminal: (task: TaskInfo) => void;
	readonly displayCommand: string;
	readonly background: boolean;
	readonly startedAt: number;
	endedAt: number | undefined;
	exitCode: number | null | undefined;
	status: TaskStatus = "running";
	stopReason: string | undefined = undefined;
	readonly outputPath: string | undefined;
	readonly stdout: CollectedOutput;
	readonly stderr: CollectedOutput;
	private readonly persistedOutput: PersistedOutput;
	private _isKilling = false;
	private _settled = false;
	private _requestedStatus: "killed" | "timed_out" | undefined;
	private _disposed = false;
	private _onProcClose: ((exitCode: number | null) => void) | null = null;
	private _onProcError: ((err: Error) => void) | null = null;
	private _resolveExit: ((result: ExitPromiseResult) => void) | null = null;
	private _exitPromise: Promise<ExitPromiseResult>;

	constructor({
		taskId,
		proc,
		isWindows,
		sessionDir,
		displayCommand,
		background,
		onDispose,
		onTerminal,
		startedAt,
	}: TrackedProcessOptions) {
		this.taskId = taskId;
		this.proc = proc;
		this.isWindows = isWindows;
		this.onDispose = onDispose;
		this.onTerminal = onTerminal;
		this.displayCommand = displayCommand;
		this.background = background ?? false;
		this.startedAt = startedAt ?? Date.now();
		this.outputPath = sessionDir ? path.join(sessionDir, "tasks", `${taskId}.log`) : undefined;
		this.persistedOutput = createPersistedOutput(this.outputPath);
		this.stdout = collect(proc.stdout, this.persistedOutput, "stdout");
		this.stderr = collect(proc.stderr, this.persistedOutput, "stderr");
		this._exitPromise = new Promise<ExitPromiseResult>((resolve) => {
			this._resolveExit = resolve;
			this._onProcClose = (exitCode) => {
				void this._settle(exitCode, undefined);
			};
			this._onProcError = (err) => {
				void this._settle(null, err);
			};
			proc.on("close", this._onProcClose);
			proc.on("error", this._onProcError);
		});
	}

	get pid(): number | undefined {
		return this.proc.pid;
	}

	get isTerminal(): boolean {
		return ["completed", "failed", "killed", "timed_out", "lost"].includes(this.status);
	}

	async wait(timeoutMs?: number): Promise<TaskExitResult> {
		if (this.isTerminal) return this.exitResult(this.exitCode ?? undefined);
		const effectiveTimeoutMs = clampTimeoutMs(timeoutMs);
		if (!effectiveTimeoutMs || effectiveTimeoutMs <= 0) {
			const result = await this._exitPromise;
			return this.exitResult(result);
		}
		let timer: NodeJS.Timeout | undefined;
		const timeoutPromise = new Promise<{ done: false }>((resolve) => {
			timer = setTimeout(() => resolve({ done: false }), effectiveTimeoutMs);
		});
		const race = await Promise.race([
			this._exitPromise.then((result) => {
				clearTimeout(timer);
				return { done: true as const, result };
			}),
			timeoutPromise,
		]);
		if (race.done) {
			return this.exitResult(race.result);
		}
		return { exitCode: null, timedOut: true, info: this.toInfo() };
	}

	exitResult(result?: ExitPromiseResult): TaskExitResult {
		if (result && typeof result === "object" && "error" in result) {
			this.status = "failed";
			return { exitCode: null, error: result.error.message, info: this.toInfo() };
		}
		return { exitCode: result === undefined ? (this.exitCode ?? null) : result, info: this.toInfo() };
	}

	async kill({ signal, reason, graceMs, status = "killed" }: KillOptions = {}): Promise<void> {
		if (this._isKilling || this.isTerminal) {
			this.dispose();
			return;
		}
		this._isKilling = true;

		const pid = this.proc.pid;
		if (!pid) {
			this.dispose();
			return;
		}

		this._requestedStatus = status;
		this.stopReason = reason ?? this.stopReason ?? "Stopped";

		if (this.isWindows) {
			const treeKill = killWindowsTree(pid);
			await Promise.race([
				treeKill,
				this._exitPromise,
				new Promise<void>((resolve) => setTimeout(resolve, WINDOWS_TREE_KILL_START_GRACE_MS)),
			]);
			if (!this._settled) this.proc.kill();
		} else {
			await killUnixGroup(pid, signal ?? "SIGTERM");
		}

		const deadline = Math.max(0, Number.isFinite(graceMs) ? graceMs! : DEFAULT_KILL_GRACE_MS);
		let timer: NodeJS.Timeout | undefined;
		await Promise.race([
			this._exitPromise.finally(() => clearTimeout(timer)),
			new Promise<void>((resolve) => {
				timer = setTimeout(resolve, deadline);
			}),
		]);

		if (!this._settled) {
			if (this.isWindows) {
				void killWindowsTree(pid).catch(() => {});
				if (!this._settled) this.proc.kill();
			} else {
				await killUnixGroup(pid, "SIGKILL").catch(() => {});
			}
			let killTimer: NodeJS.Timeout | undefined;
			await Promise.race([
				this._exitPromise.finally(() => clearTimeout(killTimer)),
				new Promise<void>((resolve) => {
					killTimer = setTimeout(resolve, 2000);
				}),
			]);
		}
		if (!this._settled) {
			this.status = "lost";
			this.endedAt = Date.now();
			this.stopReason = `${this.stopReason}; process exit could not be confirmed`;
			await this.persistedOutput.close();
			this.onTerminal(this.toInfo());
			this.dispose();
		}
	}

	async outputSnapshot(previewBytes = SNAPSHOT_BYTES): Promise<OutputSnapshot> {
		if (this.outputPath) {
			let handle: fs.FileHandle | undefined;
			try {
				const stat = await fs.stat(this.outputPath);
				const size = stat.size;
				const start = Math.max(0, size - previewBytes);
				handle = await fs.open(this.outputPath, "r");
				const { buffer } = await handle.read(
					Buffer.alloc(Math.min(previewBytes, size)),
					0,
					Math.min(previewBytes, size),
					start,
				);
				const text = buffer.toString("utf-8");
				return {
					preview: text,
					outputSizeBytes: size,
					previewBytes: buffer.length,
					truncated: size > previewBytes,
					fullOutputAvailable: !this.persistedOutput.truncated,
					persistedOutputTruncated: this.persistedOutput.truncated,
					outputPath: this.outputPath,
				};
			} catch {
				// Fall through to in-memory fallback.
			} finally {
				await handle?.close().catch(() => {});
			}
		}
		const stdout = this.stdout.text();
		const stderr = this.stderr.text();
		const combined = [stdout, stderr ? `stderr:\n${stderr}` : ""].filter(Boolean).join("\n");
		const text = combined.slice(-previewBytes);
		return {
			preview: text,
			outputSizeBytes: Buffer.byteLength(combined, "utf-8"),
			previewBytes: Buffer.byteLength(text, "utf-8"),
			truncated: Buffer.byteLength(combined, "utf-8") > previewBytes,
			fullOutputAvailable: false,
			persistedOutputTruncated: this.persistedOutput.truncated,
			outputPath: this.outputPath,
		};
	}

	async readOutput(offset = 0, limit = MAX_OUTPUT_READ_BYTES): Promise<OutputChunk> {
		const safeOffset = Number.isSafeInteger(offset) && offset >= 0 ? offset : 0;
		const safeLimit =
			Number.isSafeInteger(limit) && limit > 0 ? Math.min(limit, MAX_OUTPUT_READ_BYTES) : MAX_OUTPUT_READ_BYTES;
		if (this.outputPath) {
			let handle: fs.FileHandle | undefined;
			try {
				const stat = await fs.stat(this.outputPath);
				const start = Math.min(safeOffset, stat.size);
				const length = Math.min(safeLimit, stat.size - start);
				handle = await fs.open(this.outputPath, "r");
				const { buffer, bytesRead } = await handle.read(Buffer.alloc(length), 0, length, start);
				return {
					content: buffer.subarray(0, bytesRead).toString("utf-8"),
					offset: start,
					nextOffset: start + bytesRead,
					totalBytes: stat.size,
					eof: start + bytesRead >= stat.size,
					persistedOutputTruncated: this.persistedOutput.truncated,
				};
			} catch {
				// Fall through to bounded in-memory output when persistence is unavailable.
			} finally {
				await handle?.close().catch(() => {});
			}
		}
		const combined = Buffer.from(
			[this.stdout.text(), this.stderr.text() ? `stderr:\n${this.stderr.text()}` : ""].filter(Boolean).join("\n"),
			"utf-8",
		);
		const start = Math.min(safeOffset, combined.length);
		const end = Math.min(start + safeLimit, combined.length);
		return {
			content: combined.subarray(start, end).toString("utf-8"),
			offset: start,
			nextOffset: end,
			totalBytes: combined.length,
			eof: end >= combined.length,
			persistedOutputTruncated: true,
		};
	}

	toInfo(): TaskInfo {
		return {
			taskId: this.taskId,
			pid: this.proc.pid,
			status: this.status,
			stopReason: this.stopReason,
			command: this.displayCommand,
			background: this.background,
			startedAt: this.startedAt,
			endedAt: this.endedAt,
			exitCode: this.exitCode,
			outputPath: this.outputPath,
		};
	}

	dispose(): void {
		if (this._disposed) return;
		this._disposed = true;
		if (this._onProcClose) this.proc.off("close", this._onProcClose);
		if (this._onProcError) this.proc.off("error", this._onProcError);
		this.stdout?.removeListeners?.();
		this.stderr?.removeListeners?.();
		this.stdout?.close?.();
		this.stderr?.close?.();
		this.onDispose();
	}

	private async _settle(exitCode: number | null, error: Error | undefined): Promise<void> {
		if (this._settled) return;
		this._settled = true;
		this.exitCode = exitCode;
		this.endedAt = Date.now();
		if (this._requestedStatus) {
			this.status = this._requestedStatus;
		} else if (error) {
			this.status = "failed";
			this.stopReason = error.message;
		} else {
			this.status = exitCode === 0 ? "completed" : "failed";
			if (exitCode !== 0) this.stopReason = `Process exited with code ${String(exitCode)}`;
		}
		await this.persistedOutput.close();
		this.onTerminal(this.toInfo());
		this._resolveExit?.(error ? { error } : exitCode);
		this.dispose();
	}
}

interface SupervisedTrackedProcessOptions {
	supervisor: SessionProcessSupervisor;
	info: SupervisorTaskInfo;
	command: string;
	onTerminal: (task: TaskInfo) => void;
	onDispose: () => void;
	pollIntervalMs: number;
}

class SupervisedTrackedProcess implements TrackedProcessHandle {
	readonly proc = null;
	readonly taskId: string;
	readonly background: boolean;
	readonly startedAt: number;
	readonly outputPath: string;
	readonly pid: number | undefined;
	readonly stdout: CollectedOutput;
	readonly stderr: CollectedOutput;
	endedAt: number | undefined;
	exitCode: number | null | undefined;
	status: TaskStatus;
	stopReason: string | undefined;
	private readonly supervisor: SessionProcessSupervisor;
	private readonly command: string;
	private readonly onTerminal: (task: TaskInfo) => void;
	private readonly onDispose: () => void;
	private output = "";
	private outputTruncated = false;
	private terminalPublished = false;
	private monitor: NodeJS.Timeout | undefined;

	constructor({ supervisor, info, command, onTerminal, onDispose, pollIntervalMs }: SupervisedTrackedProcessOptions) {
		this.supervisor = supervisor;
		this.taskId = info.taskId;
		this.background = info.background;
		this.startedAt = info.startedAt;
		this.outputPath = info.logPath;
		this.pid = info.pid;
		this.status = info.status;
		this.endedAt = info.endedAt;
		this.exitCode = info.exitCode;
		this.stopReason = info.stopReason;
		this.command = command;
		this.onTerminal = onTerminal;
		this.onDispose = onDispose;
		this.stdout = {
			text: () => this.output,
			truncated: () => this.outputTruncated,
			close: () => undefined,
		};
		this.stderr = { text: () => "", truncated: () => false, close: () => undefined };
		if (!this.isTerminal) {
			this.monitor = setInterval(() => void this.refresh().catch(() => undefined), pollIntervalMs);
			this.monitor.unref();
		}
	}

	get isTerminal(): boolean {
		return this.status !== "running";
	}

	async wait(timeoutMs?: number): Promise<TaskExitResult> {
		const deadline = timeoutMs && timeoutMs > 0 ? Date.now() + clampTimeoutMs(timeoutMs) : Number.POSITIVE_INFINITY;
		while (!this.isTerminal && Date.now() < deadline) {
			await this.refresh();
			if (!this.isTerminal) await new Promise((resolve) => setTimeout(resolve, 100));
		}
		if (!this.isTerminal) return { exitCode: null, timedOut: true, info: this.toInfo() };
		await this.loadOutput();
		return { exitCode: this.exitCode ?? null, info: this.toInfo() };
	}

	async kill({ reason, status = "killed" }: KillOptions = {}): Promise<void> {
		if (this.isTerminal) return;
		const info = await this.supervisor.stop(this.taskId, reason, status === "timed_out");
		if (info) await this.apply(info);
	}

	async outputSnapshot(previewBytes = SNAPSHOT_BYTES): Promise<OutputSnapshot> {
		await this.loadOutput();
		let handle: fs.FileHandle | undefined;
		try {
			const stat = await fs.stat(this.outputPath);
			const size = stat.size;
			const start = Math.max(0, size - previewBytes);
			handle = await fs.open(this.outputPath, "r");
			const buffer = Buffer.alloc(Math.min(previewBytes, size));
			const { bytesRead } = await handle.read(buffer, 0, buffer.length, start);
			return {
				preview: buffer.subarray(0, bytesRead).toString("utf8"),
				outputSizeBytes: size,
				previewBytes: bytesRead,
				truncated: size > previewBytes,
				fullOutputAvailable: size <= MAX_PERSISTED_OUTPUT_BYTES,
				persistedOutputTruncated: size >= MAX_PERSISTED_OUTPUT_BYTES,
				outputPath: this.outputPath,
			};
		} catch {
			return {
				preview: this.output,
				outputSizeBytes: Buffer.byteLength(this.output),
				previewBytes: Buffer.byteLength(this.output),
				truncated: this.outputTruncated,
				fullOutputAvailable: false,
				persistedOutputTruncated: true,
				outputPath: this.outputPath,
			};
		} finally {
			await handle?.close().catch(() => undefined);
		}
	}

	async readOutput(offset = 0, limit = MAX_OUTPUT_READ_BYTES): Promise<OutputChunk> {
		const safeOffset = Number.isSafeInteger(offset) && offset >= 0 ? offset : 0;
		const safeLimit =
			Number.isSafeInteger(limit) && limit > 0 ? Math.min(limit, MAX_OUTPUT_READ_BYTES) : MAX_OUTPUT_READ_BYTES;
		let handle: fs.FileHandle | undefined;
		try {
			const stat = await fs.stat(this.outputPath);
			const start = Math.min(safeOffset, stat.size);
			const length = Math.min(safeLimit, stat.size - start);
			handle = await fs.open(this.outputPath, "r");
			const buffer = Buffer.alloc(length);
			const { bytesRead } = await handle.read(buffer, 0, length, start);
			return {
				content: buffer.subarray(0, bytesRead).toString("utf8"),
				offset: start,
				nextOffset: start + bytesRead,
				totalBytes: stat.size,
				eof: start + bytesRead >= stat.size,
				persistedOutputTruncated: stat.size >= MAX_PERSISTED_OUTPUT_BYTES,
			};
		} catch {
			return { content: "", offset: 0, nextOffset: 0, totalBytes: 0, eof: true, persistedOutputTruncated: false };
		} finally {
			await handle?.close().catch(() => undefined);
		}
	}

	toInfo(): TaskInfo {
		return {
			taskId: this.taskId,
			pid: this.pid,
			status: this.status,
			stopReason: this.stopReason,
			command: this.command,
			background: this.background,
			startedAt: this.startedAt,
			endedAt: this.endedAt,
			exitCode: this.exitCode,
			outputPath: this.outputPath,
		};
	}

	dispose(): void {
		if (this.monitor) clearInterval(this.monitor);
		this.monitor = undefined;
		this.onDispose();
	}

	private async refresh(): Promise<void> {
		if (this.isTerminal) return;
		const info = (await this.supervisor.list()).find((task) => task.taskId === this.taskId);
		if (info) await this.apply(info);
	}

	private async apply(info: SupervisorTaskInfo): Promise<void> {
		this.status = info.status;
		this.endedAt = info.endedAt;
		this.exitCode = info.exitCode;
		this.stopReason = info.stopReason;
		if (this.isTerminal && !this.terminalPublished) {
			this.terminalPublished = true;
			await this.loadOutput();
			this.onTerminal(this.toInfo());
			this.dispose();
		}
	}

	private async loadOutput(): Promise<void> {
		try {
			const buffer = await fs.readFile(this.outputPath);
			this.outputTruncated = buffer.length > OUTPUT_CAP;
			this.output = buffer.subarray(Math.max(0, buffer.length - OUTPUT_CAP)).toString("utf8");
		} catch {
			this.output = "";
		}
	}
}

function killWindowsTree(pid: number): Promise<void> {
	return new Promise((resolve) => {
		const killer = spawn("taskkill", ["/T", "/F", "/PID", String(pid)], {
			stdio: "ignore",
			windowsHide: true,
		});
		killer.once("error", () => resolve());
		killer.once("close", () => resolve());
	});
}

function killUnixGroup(pid: number, signal: NodeJS.Signals | number): Promise<void> {
	return new Promise((resolve) => {
		try {
			process.kill(-pid, signal);
			resolve();
		} catch (err) {
			const code = (err as NodeJS.ErrnoException).code;
			if (code === "ESRCH") {
				resolve();
			} else if (code === "EPERM") {
				try {
					process.kill(pid, signal);
				} catch {
					/* best effort */
				}
				resolve();
			} else {
				resolve();
			}
		}
	});
}

interface PersistedOutput {
	readonly truncated: boolean;
	write(kind: "stdout" | "stderr", buffer: Buffer): boolean;
	onDrain(listener: () => void): void;
	offDrain(listener: () => void): void;
	close(): Promise<void>;
}

function createPersistedOutput(logPath: string | undefined): PersistedOutput {
	let stream: WriteStream | undefined;
	let failed = false;
	let closed = false;
	let bytes = 0;
	let truncated = false;
	let stderrStarted = false;
	if (logPath) {
		try {
			mkdirSync(path.dirname(logPath), { recursive: true });
			stream = createWriteStream(logPath, { flags: "w", mode: 0o600 });
			stream.on("error", () => {
				failed = true;
			});
		} catch {
			failed = true;
		}
	}
	return {
		get truncated() {
			return truncated || failed;
		},
		write(kind, buffer) {
			if (!stream || failed || closed) return true;
			let payload = buffer;
			if (kind === "stderr" && !stderrStarted) {
				stderrStarted = true;
				payload = Buffer.concat([Buffer.from("\n[stderr]\n", "utf8"), buffer]);
			}
			const room = MAX_PERSISTED_OUTPUT_BYTES - bytes;
			if (room <= 0) {
				truncated = true;
				return true;
			}
			const slice = payload.subarray(0, room);
			bytes += slice.length;
			if (slice.length < payload.length) truncated = true;
			return stream.write(slice);
		},
		onDrain(listener) {
			stream?.once("drain", listener);
		},
		offDrain(listener) {
			stream?.off("drain", listener);
		},
		async close() {
			if (!stream || closed) return;
			closed = true;
			const target = stream;
			await new Promise<void>((resolve) => {
				if (target.destroyed || target.closed) {
					resolve();
					return;
				}
				const finish = () => {
					target.off("error", finish);
					resolve();
				};
				target.once("error", finish);
				target.end(finish);
			});
		},
	};
}

function collect(stream: Readable | null, persisted: PersistedOutput, kind: "stdout" | "stderr"): CollectedOutput {
	const chunks: Buffer[] = [];
	let size = 0;
	let removeListeners: (() => void) | undefined;
	if (stream) {
		let pausedForBackpressure = false;
		let drainListener: (() => void) | null = null;
		const onData = (chunk: Buffer | string) => {
			const buffer = Buffer.isBuffer(chunk) ? chunk : Buffer.from(String(chunk), "utf-8");
			if (size < OUTPUT_CAP) {
				const room = OUTPUT_CAP - size;
				chunks.push(buffer.slice(0, room));
			}
			size += buffer.length;
			const ok = persisted.write(kind, buffer);
			if (!ok && !pausedForBackpressure) {
				pausedForBackpressure = true;
				stream.pause();
				drainListener = () => {
					pausedForBackpressure = false;
					drainListener = null;
					stream.resume();
				};
				persisted.onDrain(drainListener);
			}
		};
		stream.on("data", onData);
		removeListeners = () => {
			stream.off("data", onData);
			if (drainListener) persisted.offDrain(drainListener);
			if (pausedForBackpressure) stream.resume();
		};
	}
	return {
		text() {
			return Buffer.concat(chunks).toString("utf-8");
		},
		truncated() {
			return size > OUTPUT_CAP;
		},
		close() {
			removeListeners?.();
		},
		removeListeners,
	};
}

const MAX_SAFE_TIMEOUT_MS = 2 ** 31 - 1;

function clampTimeoutMs(value: number | undefined): number {
	const n = Number(value);
	if (!Number.isFinite(n) || n < 1) {
		return 0;
	}
	return Math.min(n, MAX_SAFE_TIMEOUT_MS);
}
