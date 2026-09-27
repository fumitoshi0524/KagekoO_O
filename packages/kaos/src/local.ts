/**
 * Local execution environment backed by Node.js fs/child_process.
 * Never mutates process.cwd(); all paths are resolved against an instance cwd.
 */
import { spawn, type ChildProcess } from "node:child_process";
import * as crypto from "node:crypto";
import * as fs from "node:fs/promises";
import type { Dirent } from "node:fs";
import * as path from "node:path";
import { safeInheritedEnvironment, scrubEnvironment } from "./environment.js";

const PROCESS_TREE_KILL_GRACE_MS = 5000;

function isOutsideWorkspace(relativePath: string): boolean {
	return relativePath === ".." || relativePath.startsWith(`..${path.sep}`) || path.isAbsolute(relativePath);
}

function sleep(ms: number): Promise<void> {
	return new Promise((resolve) => setTimeout(resolve, ms));
}

function isProcessAlive(pid: number): boolean {
	try {
		process.kill(pid, 0);
		return true;
	} catch (error) {
		return (error as NodeJS.ErrnoException).code === "EPERM";
	}
}

async function killProcessTree(proc: ChildProcess | null, isWindows: boolean): Promise<void> {
	if (!proc || proc.killed || !proc.pid) return;
	if (isWindows) {
		await new Promise<void>((resolve) => {
			try {
				const killer = spawn("taskkill", ["/T", "/F", "/PID", String(proc.pid)], {
					env: safeInheritedEnvironment(process.env),
					stdio: "ignore",
					windowsHide: true,
				});
				killer.once("error", () => resolve());
				killer.once("close", () => resolve());
			} catch {
				resolve();
			}
		});
		if (isProcessAlive(proc.pid)) proc.kill("SIGKILL");
		return;
	}
	// On Unix, the child was spawned with `detached: true`, so it became the
	// leader of a new process group. Killing the negative PID targets the whole
	// group, preventing grandchild orphans.
	try {
		process.kill(-proc.pid, "SIGTERM");
	} catch {
		try {
			proc.kill("SIGTERM");
		} catch {
			// Already gone.
		}
	}
	const deadline = Date.now() + PROCESS_TREE_KILL_GRACE_MS;
	while (isProcessAlive(proc.pid) && Date.now() < deadline) await sleep(50);
	if (isProcessAlive(proc.pid)) {
		try {
			process.kill(-proc.pid, "SIGKILL");
		} catch {
			try {
				proc.kill("SIGKILL");
			} catch {
				// Already gone.
			}
		}
	}
}

export class PathSecurityError extends Error {
	readonly filePath: string;
	readonly cwd: string;

	constructor(filePath: string, cwd: string) {
		super(`Path "${filePath}" resolves outside the workspace "${cwd}"`);
		this.name = "PathSecurityError";
		this.filePath = filePath;
		this.cwd = cwd;
	}
}

export class FileTooLargeError extends Error {
	readonly filePath: string;
	readonly size: number;
	readonly max: number;

	constructor(filePath: string, size: number, max: number) {
		super(`File "${filePath}" is ${size} bytes, exceeding the ${max} byte limit`);
		this.name = "FileTooLargeError";
		this.filePath = filePath;
		this.size = size;
		this.max = max;
	}
}

export interface LocalKaosOptions {
	cwd?: string;
	env?: Record<string, string | undefined>;
	allowOutsideCwd?: boolean;
	maxFileSizeBytes?: number;
	shellDialect?: ShellDialect;
	shellExecutable?: string;
	allowSensitiveEnv?: boolean;
}

export type ShellDialect = "bash" | "powershell" | "cmd";

export interface ExecOptions {
	timeout?: number;
	outputCap?: number;
	signal?: AbortSignal;
	shell?: boolean;
}

export interface ExecResult {
	exitCode: number | null;
	signal: string | null;
	stdout: string;
	stderr: string;
	pid: number | undefined;
	timedOut?: boolean;
}

export class LocalKaos {
	readonly cwd: string;
	readonly env: Record<string, string | undefined>;
	readonly allowOutsideCwd: boolean;
	readonly maxFileSizeBytes: number;
	readonly shellDialect: ShellDialect;
	readonly shellExecutable: string;
	readonly allowSensitiveEnv: boolean;

	constructor(options: LocalKaosOptions = {}) {
		this.cwd = path.resolve(options.cwd ?? process.cwd());
		this.allowSensitiveEnv = options.allowSensitiveEnv ?? false;
		this.env = scrubEnvironment(
			{ ...process.env, ...(options.env ?? {}) },
			{
				allowSensitive: this.allowSensitiveEnv,
			},
		);
		this.allowOutsideCwd = options.allowOutsideCwd ?? false;
		this.maxFileSizeBytes = options.maxFileSizeBytes ?? 5 * 1024 * 1024;
		this.shellDialect = options.shellDialect ?? (process.platform === "win32" ? "powershell" : "bash");
		this.shellExecutable = options.shellExecutable ?? defaultShellExecutable(this.shellDialect);
	}

	withCwd(cwd: string): LocalKaos {
		return new LocalKaos({
			cwd,
			env: this.env,
			allowOutsideCwd: this.allowOutsideCwd,
			maxFileSizeBytes: this.maxFileSizeBytes,
			shellDialect: this.shellDialect,
			shellExecutable: this.shellExecutable,
			allowSensitiveEnv: this.allowSensitiveEnv,
		});
	}

	withEnv(env: Record<string, string | undefined>): LocalKaos {
		return new LocalKaos({
			cwd: this.cwd,
			env: { ...this.env, ...env },
			allowOutsideCwd: this.allowOutsideCwd,
			maxFileSizeBytes: this.maxFileSizeBytes,
			shellDialect: this.shellDialect,
			shellExecutable: this.shellExecutable,
			allowSensitiveEnv: this.allowSensitiveEnv,
		});
	}

	resolve(filePath: string): string {
		const resolved = path.resolve(this.cwd, filePath);
		if (!this.allowOutsideCwd) {
			const rel = path.relative(this.cwd, resolved);
			// `path.relative` can return a string starting with ".." or an absolute
			// path on Windows when resolved is outside cwd.
			if (isOutsideWorkspace(rel)) {
				throw new PathSecurityError(filePath, this.cwd);
			}
		}
		return resolved;
	}

	/**
	 * Resolve a path and follow symlinks, re-verifying the real target stays
	 * inside the workspace. Falls back to the non-realpath resolved path when the
	 * target does not yet exist (e.g., a new file write).
	 */
	async resolveReal(filePath: string): Promise<string> {
		const resolved = this.resolve(filePath);
		try {
			const real = await fs.realpath(resolved);
			if (!this.allowOutsideCwd) {
				const rel = path.relative(await this._canonicalCwd(), real);
				if (isOutsideWorkspace(rel)) {
					throw new PathSecurityError(filePath, this.cwd);
				}
			}
			return real;
		} catch (err) {
			if (err instanceof PathSecurityError) throw err;
			// realpath fails for not-yet-existing targets (new writes); fall
			// back to the already-sandbox-checked resolved path.
			return resolved;
		}
	}

	/** Resolve the deepest existing ancestor so authorization sees symlink targets even for new files. */
	async resolveForPolicy(filePath: string): Promise<string> {
		const resolved = this.resolve(filePath);
		let current = resolved;
		const missing: string[] = [];
		while (true) {
			try {
				const real = await fs.realpath(current);
				const canonical = path.join(real, ...missing.reverse());
				if (!this.allowOutsideCwd) {
					const realCwd = await fs.realpath(this.cwd).catch(() => this.cwd);
					const rel = path.relative(realCwd, canonical);
					if (isOutsideWorkspace(rel)) throw new PathSecurityError(filePath, this.cwd);
				}
				return canonical;
			} catch (error) {
				if (error instanceof PathSecurityError) throw error;
				if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
				const parent = path.dirname(current);
				if (parent === current) throw new PathSecurityError(filePath, this.cwd);
				missing.push(path.basename(current));
				current = parent;
			}
		}
	}

	async readText(filePath: string): Promise<string> {
		const target = await this.resolveReal(filePath);
		let handle: fs.FileHandle | undefined;
		try {
			handle = await fs.open(target, "r");
			const stat = await handle.stat();
			if (stat.size > this.maxFileSizeBytes) {
				throw new FileTooLargeError(filePath, stat.size, this.maxFileSizeBytes);
			}
			return await handle.readFile({ encoding: "utf-8" });
		} finally {
			await handle?.close().catch(() => {});
		}
	}

	async writeText(filePath: string, data: string): Promise<void> {
		const target = await this.resolveReal(filePath);
		if (Buffer.byteLength(data, "utf-8") > this.maxFileSizeBytes) {
			throw new FileTooLargeError(filePath, Buffer.byteLength(data, "utf-8"), this.maxFileSizeBytes);
		}
		const parent = path.dirname(target);
		await this._assertAncestorsContained(parent);
		await fs.mkdir(parent, { recursive: true });
		await this._assertAncestorsContained(parent);
		let tmp: string;
		do {
			tmp = `${target}.tmp.${crypto.randomUUID()}`;
		} while (
			await fs
				.access(tmp)
				.then(() => true)
				.catch(() => false)
		);
		let renamed = false;
		let handle: fs.FileHandle | undefined;
		try {
			handle = await fs.open(tmp, "wx", 0o600);
			await handle.writeFile(data, "utf-8");
			await handle.sync();
			await handle.close();
			handle = undefined;
			await fs.rename(tmp, target);
			renamed = true;
		} finally {
			await handle?.close().catch(() => undefined);
			if (!renamed) await fs.rm(tmp, { force: true }).catch(() => undefined);
		}
	}

	async mkdir(dirPath: string, { parents = true }: { parents?: boolean } = {}): Promise<void> {
		const target = this.resolve(dirPath);
		await this._assertAncestorsContained(target);
		await fs.mkdir(target, { recursive: parents });
		await this._assertAncestorsContained(target);
	}

	/**
	 * Verify that the deepest existing ancestor of `resolvedPath` resolves to a
	 * real directory inside the workspace. This prevents symlinked directories
	 * inside the workspace from redirecting writes outside it.
	 */
	private async _assertAncestorsContained(resolvedPath: string): Promise<void> {
		if (this.allowOutsideCwd) return;
		const canonicalCwd = await this._canonicalCwd();
		let current = resolvedPath;
		while (true) {
			const real = await fs.realpath(current).catch(() => null);
			if (real) {
				const rel = path.relative(canonicalCwd, real);
				if (isOutsideWorkspace(rel)) {
					throw new PathSecurityError(resolvedPath, this.cwd);
				}
				return;
			}
			const parent = path.dirname(current);
			if (parent === current) break;
			current = parent;
		}
		throw new PathSecurityError(resolvedPath, this.cwd);
	}

	private async _canonicalCwd(): Promise<string> {
		return fs.realpath(this.cwd).catch(() => this.cwd);
	}

	async readdir(dirPath: string): Promise<Dirent[]> {
		const target = await this.resolveReal(dirPath);
		return fs.readdir(target, { withFileTypes: true });
	}

	exec(command: string, args: string[] = [], options: ExecOptions = {}): Promise<ExecResult> {
		const timeoutMs = options.timeout ?? 30000;
		const outputCap = options.outputCap ?? 64 * 1024;
		const signal = options.signal;
		if (signal?.aborted) {
			return Promise.reject(new Error("Command aborted before spawn"));
		}
		const isWindows = process.platform === "win32";
		return new Promise((resolve, reject) => {
			const proc = spawn(command, args, {
				cwd: this.cwd,
				env: this.env,
				shell: options.shell ?? false,
				detached: !isWindows,
				stdio: ["ignore", "pipe", "pipe"],
			});

			let stdout = "";
			let stderr = "";
			let stdoutCapped = false;
			let stderrCapped = false;
			let settled = false;
			let timedOut = false;
			// Set when WE terminate the process tree (abort/timeout). Windows
			// reports an exit code (1) for TerminateProcess/taskkill instead of a
			// signal; normalize those kills to exitCode null + signal SIGKILL so
			// callers see consistent signal-kill semantics on every platform.
			let killed = false;

			const onStdoutData = (chunk: Buffer) => {
				if (stdoutCapped) return;
				const s = chunk.toString("utf-8");
				if (stdout.length + s.length > outputCap) {
					stdout += s.slice(0, outputCap - stdout.length);
					stdoutCapped = true;
				} else {
					stdout += s;
				}
			};
			const onStderrData = (chunk: Buffer) => {
				if (stderrCapped) return;
				const s = chunk.toString("utf-8");
				if (stderr.length + s.length > outputCap) {
					stderr += s.slice(0, outputCap - stderr.length);
					stderrCapped = true;
				} else {
					stderr += s;
				}
			};
			proc.stdout?.on("data", onStdoutData);
			proc.stderr?.on("data", onStderrData);

			const timer = setTimeout(() => {
				timedOut = true;
				void killProc("timeout");
			}, timeoutMs);
			const hardDeadlineMs = timeoutMs + PROCESS_TREE_KILL_GRACE_MS + 5000;
			const hardDeadline = setTimeout(() => {
				if (settled) return;
				cleanup();
				void killProcessTree(proc, isWindows).finally(() => {
					resolve({ exitCode: null, signal: "SIGKILL", stdout, stderr, pid: proc.pid, timedOut });
				});
			}, hardDeadlineMs);

			const cleanup = () => {
				if (settled) return;
				settled = true;
				clearTimeout(timer);
				clearTimeout(hardDeadline);
				if (signal) signal.removeEventListener("abort", onAbort);
				proc.stdout?.off("data", onStdoutData);
				proc.stderr?.off("data", onStderrData);
				proc.off("error", onError);
				proc.off("close", onClose);
			};

			const killProc = async (_reason: string) => {
				if (settled) return;
				killed = true;
				await killProcessTree(proc, isWindows);
			};

			const onAbort = () => {
				void killProc("aborted");
			};
			if (signal) {
				signal.addEventListener("abort", onAbort, { once: true });
			}

			const onError = (err: Error) => {
				cleanup();
				reject(err);
			};
			const onClose = (exitCode: number | null, sig: NodeJS.Signals | null) => {
				cleanup();
				const normalizedCode = killed ? null : (exitCode ?? null);
				const normalizedSignal = killed ? (sig ?? "SIGKILL") : (sig ?? null);
				resolve({
					exitCode: normalizedCode,
					signal: normalizedSignal,
					stdout,
					stderr,
					pid: proc.pid,
					...(timedOut ? { timedOut: true } : {}),
				});
			};
			proc.on("error", onError);
			proc.on("close", onClose);
		});
	}

	async execShell(script: string, options: ExecOptions = {}): Promise<ExecResult> {
		const invocation = this.shellInvocation(script);
		return this.exec(invocation.command, invocation.args, { ...options, shell: false });
	}

	shellInvocation(script: string): { command: string; args: string[] } {
		return { command: this.shellExecutable, args: shellArguments(this.shellDialect, script) };
	}
}

function defaultShellExecutable(dialect: ShellDialect): string {
	if (dialect === "powershell") return "pwsh";
	if (dialect === "cmd") return "cmd.exe";
	return "bash";
}

function shellArguments(dialect: ShellDialect, script: string): string[] {
	if (dialect === "powershell") {
		return ["-NoLogo", "-NoProfile", "-NonInteractive", "-Command", script];
	}
	return [dialect === "cmd" ? "/d" : "-c", ...(dialect === "cmd" ? ["/s", "/c"] : []), script];
}
