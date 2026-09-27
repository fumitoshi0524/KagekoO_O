import { spawn, type ChildProcess } from "node:child_process";
import * as crypto from "node:crypto";
import * as fs from "node:fs/promises";
import * as net from "node:net";
import * as os from "node:os";
import * as path from "node:path";
import { fileURLToPath } from "node:url";
import { safeInheritedEnvironment } from "@kageko/kaos";
import type { SupervisorDescriptor, SupervisorSpawnRequest, SupervisorTaskInfo } from "./types.js";

const CONNECT_TIMEOUT_MS = 5000;
const MAX_MESSAGE_BYTES = 4 * 1024 * 1024;
const REQUEST_TIMEOUT_MS = 30_000;

interface ResponseMessage {
	type: "response";
	requestId: string;
	ok: boolean;
	result?: unknown;
	error?: string;
}

export class SessionProcessSupervisor {
	readonly runtimeDir: string;
	readonly descriptorPath: string;
	readonly tokenPath: string;
	private socket: net.Socket | undefined;
	private token: string | undefined;
	private descriptor: SupervisorDescriptor | undefined;
	private pending = new Map<
		string,
		{ resolve(value: unknown): void; reject(error: Error): void; timer: NodeJS.Timeout }
	>();
	private input = "";
	private shutdownComplete = false;
	private shutdownPromise: Promise<void> | undefined;

	constructor(runtimeDir: string) {
		this.runtimeDir = path.resolve(runtimeDir);
		this.descriptorPath = path.join(this.runtimeDir, "supervisor.json");
		this.tokenPath = path.join(this.runtimeDir, "supervisor.token");
	}

	async connectOrStart(): Promise<"connected" | "started"> {
		await ensurePrivateRuntimeDirectory(this.runtimeDir);
		const recovered = await this.readCredentials();
		if (recovered) {
			for (let attempt = 0; attempt < 3; attempt += 1) {
				if (await this.connect(recovered.descriptor, recovered.token).catch(() => false)) return "connected";
				if (attempt < 2) await new Promise((resolve) => setTimeout(resolve, 500));
			}
			// A supervisor that does not answer its own socket is stale. The
			// recorded pid is not evidence otherwise: after a SIGKILL or container
			// kill the pid is recycled by an unrelated process (pid namespaces make
			// every low pid "alive" somewhere), so refusing to recover here used to
			// make an unlucky kill permanently fatal for the session.
		}
		await this.removeStaleControlFiles();
		await this.start();
		return "started";
	}

	async spawn(request: SupervisorSpawnRequest): Promise<SupervisorTaskInfo> {
		return this.request("spawn", request) as Promise<SupervisorTaskInfo>;
	}

	async list(): Promise<SupervisorTaskInfo[]> {
		return this.request("list", {}) as Promise<SupervisorTaskInfo[]>;
	}

	async stop(taskId: string, reason = "Stopped by client", timedOut = false): Promise<SupervisorTaskInfo | undefined> {
		return this.request("stop", { taskId, reason, timedOut }) as Promise<SupervisorTaskInfo | undefined>;
	}

	async stopAll(reason = "Session closed"): Promise<SupervisorTaskInfo[]> {
		return this.request("stopAll", { reason }) as Promise<SupervisorTaskInfo[]>;
	}

	async shutdown(): Promise<void> {
		if (this.shutdownComplete) return;
		if (this.shutdownPromise) return this.shutdownPromise;
		this.shutdownPromise = (async () => {
			if (!this.socket || !this.token) {
				// The connection is already gone — typically because the supervisor
				// acknowledged an earlier shutdown, exited, and the socket close tore
				// down this client before the control-file poll could finish. The
				// RPC can never be re-sent, so converge on the observable end state
				// instead: an exited supervisor removes its descriptor, and a
				// descriptor whose pid is dead is equally terminal.
				if (await this.supervisorReleased()) return;
				throw new Error("Supervisor connection lost before shutdown could be confirmed");
			}
			await this.request("shutdown", {});
			for (let attempt = 0; attempt < 40; attempt++) {
				const exists = await fs.access(this.descriptorPath).then(
					() => true,
					() => false,
				);
				if (!exists) return;
				await new Promise((resolve) => setTimeout(resolve, 50));
			}
			throw new Error("Supervisor acknowledged shutdown but did not release its control files");
		})();
		try {
			await this.shutdownPromise;
			this.shutdownComplete = true;
			this.close();
		} catch (error) {
			this.shutdownPromise = undefined;
			throw error;
		}
	}

	close(): void {
		this.socket?.destroy();
		this.socket = undefined;
		for (const pending of this.pending.values()) {
			clearTimeout(pending.timer);
			pending.reject(new Error("Supervisor connection closed"));
		}
		this.pending.clear();
	}

	/**
	 * Fail-closed liveness verdict used when shutdown can no longer reach the
	 * supervisor over the socket. Only two observations prove the supervisor is
	 * gone: its descriptor file was removed (the server deletes it during exit
	 * cleanup after verifying the recorded pid is its own), or the descriptor's
	 * pid is dead. Anything else — a live pid, or an unreadable/corrupt
	 * descriptor — leaves the state unconfirmed.
	 */
	private async supervisorReleased(): Promise<boolean> {
		let text: string;
		try {
			text = await fs.readFile(this.descriptorPath, "utf8");
		} catch (error) {
			return (error as NodeJS.ErrnoException).code === "ENOENT";
		}
		try {
			const descriptor = JSON.parse(text) as SupervisorDescriptor;
			return !Number.isSafeInteger(descriptor.pid) || !isProcessAlive(descriptor.pid);
		} catch {
			return false;
		}
	}

	private async start(): Promise<void> {
		const token = crypto.randomBytes(32).toString("hex");
		const endpoint = endpointFor(this.runtimeDir);
		const serverPath = resolveSupervisorServerPath();
		const child = spawn(process.execPath, [serverPath, endpoint, this.runtimeDir], {
			// The detached supervisor must not inherit the caller workspace as its
			// process cwd. On Windows, a still-exiting taskkill helper inherits this
			// cwd and can keep an otherwise fully closed workspace undeletable.
			// Individual tasks still receive their explicit request.cwd in server.mjs.
			cwd: os.tmpdir(),
			detached: true,
			stdio: ["pipe", "ignore", "ignore"],
			env: safeInheritedEnvironment(process.env),
			windowsHide: true,
		});
		try {
			await writeStartupSecret(child, token);
			child.unref();
			const descriptor: SupervisorDescriptor = { version: 1, pid: child.pid!, endpoint, createdAt: Date.now() };
			await Promise.all([
				atomicPrivateWrite(this.tokenPath, `${token}\n`),
				atomicPrivateWrite(this.descriptorPath, `${JSON.stringify(descriptor)}\n`),
			]);
			for (let attempt = 0; attempt < 50; attempt++) {
				if (await this.connect(descriptor, token).catch(() => false)) return;
				await new Promise((resolve) => setTimeout(resolve, 100));
			}
			throw new Error("Process supervisor did not become ready");
		} catch (error) {
			// No caller can yet own a usable supervisor connection on this path.
			// Terminate the just-spawned child here rather than leaving a detached
			// sidecar that a later runtime cannot authenticate or close.
			child.kill();
			this.close();
			throw error;
		}
	}

	private connect(descriptor: SupervisorDescriptor, token: string): Promise<boolean> {
		return new Promise((resolve, reject) => {
			const socket = net.createConnection(descriptor.endpoint);
			const timer = setTimeout(() => socket.destroy(new Error("Supervisor connect timeout")), CONNECT_TIMEOUT_MS);
			const fail = (error: Error): void => {
				clearTimeout(timer);
				socket.destroy();
				reject(error);
			};
			socket.setEncoding("utf8");
			socket.once("error", fail);
			socket.once("connect", () => {
				socket.write(`${JSON.stringify({ type: "hello", token })}\n`);
			});
			let initial = "";
			const onData = (chunk: string) => {
				initial += chunk;
				const newline = initial.indexOf("\n");
				if (newline < 0) return;
				clearTimeout(timer);
				const line = initial.slice(0, newline);
				const rest = initial.slice(newline + 1);
				try {
					const message = JSON.parse(line) as { type?: string; ok?: boolean };
					if (message.type !== "hello" || message.ok !== true) throw new Error("Supervisor authentication failed");
					socket.off("data", onData);
					socket.removeAllListeners("error");
					this.socket = socket;
					this.token = token;
					this.descriptor = descriptor;
					socket.on("data", (data) => this.onData(data.toString()));
					socket.on("error", () => this.close());
					socket.on("close", () => this.close());
					if (rest) this.onData(rest);
					resolve(true);
				} catch (error) {
					socket.destroy();
					reject(error);
				}
			};
			socket.on("data", onData);
		});
	}

	private request(method: string, params: unknown): Promise<unknown> {
		if (!this.socket || !this.token) return Promise.reject(new Error("Supervisor is not connected"));
		const requestId = crypto.randomUUID();
		return new Promise((resolve, reject) => {
			const timer = setTimeout(() => {
				this.pending.delete(requestId);
				reject(new Error(`Supervisor request timed out: ${method}`));
			}, REQUEST_TIMEOUT_MS);
			this.pending.set(requestId, { resolve, reject, timer });
			this.socket!.write(`${JSON.stringify({ type: "request", token: this.token, requestId, method, params })}\n`);
		});
	}

	private onData(chunk: string): void {
		this.input += chunk;
		if (Buffer.byteLength(this.input, "utf8") > MAX_MESSAGE_BYTES) return this.close();
		while (true) {
			const newline = this.input.indexOf("\n");
			if (newline < 0) return;
			const line = this.input.slice(0, newline);
			this.input = this.input.slice(newline + 1);
			if (!line) continue;
			let message: ResponseMessage;
			try {
				message = JSON.parse(line) as ResponseMessage;
			} catch {
				return this.close();
			}
			if (message.type !== "response") continue;
			const pending = this.pending.get(message.requestId);
			if (!pending) continue;
			this.pending.delete(message.requestId);
			clearTimeout(pending.timer);
			if (message.ok) pending.resolve(message.result);
			else pending.reject(new Error(message.error ?? "Supervisor request failed"));
		}
	}

	private async readCredentials(): Promise<{ descriptor: SupervisorDescriptor; token: string } | undefined> {
		try {
			await Promise.all([assertPrivateRegularFile(this.descriptorPath), assertPrivateRegularFile(this.tokenPath)]);
		} catch (error) {
			if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
			const [descriptorExists, tokenExists] = await Promise.all([
				fs.access(this.descriptorPath).then(
					() => true,
					() => false,
				),
				fs.access(this.tokenPath).then(
					() => true,
					() => false,
				),
			]);
			if (!descriptorExists && !tokenExists) return undefined;
			throw new Error("Supervisor control files are incomplete; refusing unsafe replacement");
		}
		const [descriptorText, tokenText] = await Promise.all([
			fs.readFile(this.descriptorPath, "utf8"),
			fs.readFile(this.tokenPath, "utf8"),
		]);
		const descriptor = JSON.parse(descriptorText) as SupervisorDescriptor;
		if (
			descriptor.version !== 1 ||
			!descriptor.endpoint ||
			!Number.isSafeInteger(descriptor.pid) ||
			descriptor.pid <= 0
		) {
			throw new Error("Supervisor descriptor is invalid");
		}
		const token = tokenText.trim();
		if (!/^[a-f0-9]{64}$/.test(token)) throw new Error("Supervisor token file is invalid");
		return { descriptor, token };
	}

	private async removeStaleControlFiles(): Promise<void> {
		await Promise.all([fs.rm(this.descriptorPath, { force: true }), fs.rm(this.tokenPath, { force: true })]);
	}
}

async function ensurePrivateRuntimeDirectory(directory: string): Promise<void> {
	await fs.mkdir(directory, { recursive: true, mode: 0o700 });
	const stat = await fs.lstat(directory);
	if (!stat.isDirectory() || stat.isSymbolicLink()) throw new Error("Supervisor runtime path must be a real directory");
	if (process.platform !== "win32" && (stat.mode & 0o077) !== 0) {
		await fs.chmod(directory, 0o700);
	}
}

async function assertPrivateRegularFile(filePath: string): Promise<void> {
	const stat = await fs.lstat(filePath);
	if (!stat.isFile() || stat.isSymbolicLink())
		throw new Error(`Supervisor control file is not a regular file: ${filePath}`);
	if (process.platform !== "win32" && (stat.mode & 0o077) !== 0) {
		throw new Error(`Supervisor control file permissions are too broad: ${filePath}`);
	}
}

/**
 * Published builds must spawn the package's dist subpath.  Vitest executes
 * this TypeScript source directly without first producing dist, so the only
 * development fallback is its sibling source entry; it never becomes a
 * package export or a production resolution path.
 */
function resolveSupervisorServerPath(): string {
	const currentFile = fileURLToPath(import.meta.url);
	if (currentFile.endsWith(".ts")) return path.join(path.dirname(currentFile), "server.mjs");
	return fileURLToPath(import.meta.resolve("@kageko/process-supervisor/server"));
}

function isProcessAlive(pid: number): boolean {
	try {
		process.kill(pid, 0);
		return true;
	} catch (error) {
		return (error as NodeJS.ErrnoException).code === "EPERM";
	}
}

function endpointFor(runtimeDir: string): string {
	const id = crypto.createHash("sha256").update(runtimeDir).digest("hex").slice(0, 24);
	if (process.platform === "win32") return `\\\\.\\pipe\\kageko-${id}`;
	const local = path.join(runtimeDir, "supervisor.sock");
	return Buffer.byteLength(local) <= 100 ? local : path.join(os.tmpdir(), `kageko-${id}.sock`);
}

async function writeStartupSecret(child: ChildProcess, token: string): Promise<void> {
	if (!child.stdin) throw new Error("Supervisor startup channel is unavailable");
	await new Promise<void>((resolve, reject) => {
		child.stdin!.once("error", reject);
		child.stdin!.end(`${JSON.stringify({ version: 1, token })}\n`, () => resolve());
	});
}

async function atomicPrivateWrite(filePath: string, content: string): Promise<void> {
	const temporary = `${filePath}.${process.pid}.${crypto.randomUUID()}.tmp`;
	await fs.writeFile(temporary, content, { encoding: "utf8", mode: 0o600, flag: "wx" });
	await fs.rename(temporary, filePath);
	await fs.chmod(filePath, 0o600).catch(() => undefined);
}
