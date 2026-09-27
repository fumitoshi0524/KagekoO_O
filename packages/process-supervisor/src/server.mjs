import { spawn } from "node:child_process";
import crypto from "node:crypto";
import { createWriteStream, mkdirSync } from "node:fs";
import fs from "node:fs/promises";
import net from "node:net";
import path from "node:path";
import { safeInheritedEnvironment, scrubEnvironment } from "@kageko/kaos";

const MAX_MESSAGE_BYTES = 4 * 1024 * 1024;
const MAX_LOG_BYTES = 50 * 1024 * 1024;
const MAX_CONCURRENT_TASKS = 32;
const MAX_RETAINED_TASKS = 100;
const ORPHAN_IDLE_TIMEOUT_MS = 30_000;
const endpoint = process.argv[2];
const runtimeDir = process.argv[3];
if (!endpoint || !runtimeDir) process.exit(64);

const startup = await readStartup();
if (!startup || startup.version !== 1 || !/^[a-f0-9]{64}$/.test(startup.token)) process.exit(65);
const token = startup.token;
const tasks = new Map();
let shuttingDown = false;
let connectedClients = 0;
let idleTimer;

if (process.platform !== "win32") await fs.rm(endpoint, { force: true });
const server = net.createServer((socket) => handleConnection(socket));
server.on("error", () => process.exit(70));
server.listen(endpoint, async () => {
	if (process.platform !== "win32") await fs.chmod(endpoint, 0o600).catch(() => undefined);
});

function handleConnection(socket) {
	connectedClients++;
	clearTimeout(idleTimer);
	const authTimer = setTimeout(() => socket.destroy(), 5000);
	authTimer.unref();
	socket.once("close", () => {
		clearTimeout(authTimer);
		connectedClients = Math.max(0, connectedClients - 1);
		scheduleIdleExit();
	});
	socket.setEncoding("utf8");
	let input = "";
	let authenticated = false;
	socket.on("data", async (chunk) => {
		input += chunk;
		if (Buffer.byteLength(input, "utf8") > MAX_MESSAGE_BYTES) return socket.destroy();
		while (true) {
			const newline = input.indexOf("\n");
			if (newline < 0) return;
			const line = input.slice(0, newline);
			input = input.slice(newline + 1);
			if (!line) continue;
			let message;
			try {
				message = JSON.parse(line);
			} catch {
				return socket.destroy();
			}
			if (!authenticated) {
				if (message.type !== "hello" || !validToken(message.token)) return socket.destroy();
				authenticated = true;
				clearTimeout(authTimer);
				socket.write(`${JSON.stringify({ type: "hello", ok: true })}\n`);
				continue;
			}
			if (message.type !== "request" || !validToken(message.token) || typeof message.requestId !== "string") {
				return socket.destroy();
			}
			void dispatch(message)
				.then((result) => respond(socket, message.requestId, true, result))
				.catch((error) => respond(socket, message.requestId, false, undefined, error));
		}
	});
}

async function dispatch(message) {
	const params = message.params ?? {};
	switch (message.method) {
		case "spawn":
			return spawnTask(params);
		case "list":
			return [...tasks.values()].map(publicInfo);
		case "stop": {
			const task = tasks.get(params.taskId);
			if (!task) return undefined;
			await stopTask(task, params.reason, params.timedOut ? "timed_out" : "killed");
			return publicInfo(task);
		}
		case "stopAll":
			await Promise.all(
				[...tasks.values()].filter((task) => task.status === "running").map((task) => stopTask(task, params.reason)),
			);
			return [...tasks.values()].map(publicInfo);
		case "shutdown":
			shuttingDown = true;
			await Promise.all(
				[...tasks.values()]
					.filter((task) => task.status === "running")
					.map((task) => stopTask(task, "Supervisor shutdown")),
			);
			server.close();
			if (process.platform !== "win32") void fs.rm(endpoint, { force: true });
			void cleanupControlFiles();
			return null;
		default:
			throw new Error(`Unknown supervisor method: ${String(message.method)}`);
	}
}

function spawnTask(params) {
	if (shuttingDown) throw new Error("Supervisor is shutting down");
	if (typeof params.taskId !== "string" || !/^[a-f0-9-]{16,64}$/i.test(params.taskId))
		throw new Error("Invalid task id");
	if (tasks.has(params.taskId)) throw new Error(`Duplicate task id: ${params.taskId}`);
	if ([...tasks.values()].filter((task) => task.status === "running").length >= MAX_CONCURRENT_TASKS) {
		throw new Error(`Supervisor concurrent task limit (${MAX_CONCURRENT_TASKS}) reached`);
	}
	if (typeof params.command !== "string" || !params.command) throw new Error("Invalid command");
	if (!Array.isArray(params.args) || !params.args.every((arg) => typeof arg === "string"))
		throw new Error("Invalid args");
	if (typeof params.cwd !== "string" || !path.isAbsolute(params.cwd)) throw new Error("Invalid cwd");
	const logPath = assertPrivateLogPath(params.logPath);
	const log = createCappedLog(logPath);
	const child = spawn(params.command, params.args, {
		cwd: params.cwd,
		env: sanitizeEnv(params.env, params.allowSensitiveEnv === true),
		detached: process.platform !== "win32",
		stdio: ["ignore", "pipe", "pipe"],
		windowsHide: true,
	});
	const task = {
		taskId: params.taskId,
		child,
		pid: child.pid,
		status: "running",
		background: params.background === true,
		startedAt: Date.now(),
		endedAt: undefined,
		exitCode: undefined,
		stopReason: undefined,
		logPath,
		log,
		requestedStatus: undefined,
	};
	tasks.set(task.taskId, task);
	child.stdout?.on("data", (chunk) => log.write(chunk));
	let stderrStarted = false;
	child.stderr?.on("data", (chunk) => {
		const marker = stderrStarted ? Buffer.alloc(0) : Buffer.from("\n[stderr]\n");
		stderrStarted = true;
		log.write(Buffer.concat([marker, Buffer.from(chunk)]));
	});
	child.once("error", (error) => settle(task, null, error));
	child.once("close", (code) => settle(task, code, undefined));
	return publicInfo(task);
}

async function stopTask(task, reason = "Stopped", status = "killed") {
	if (task.status !== "running") return;
	task.requestedStatus = status;
	task.stopReason = typeof reason === "string" ? reason : "Stopped";
	const pid = task.pid;
	if (pid) {
		if (process.platform === "win32") {
			// taskkill /T /F is the authoritative Windows tree-stop operation. Do
			// not abandon its helper after an arbitrary startup grace: a lingering
			// helper inherits handles and Node's child close can lag behind the
			// actual process exit while descendant stdio is being torn down.
			await runTaskkill(pid);
			if (isAlive(pid)) {
				try {
					task.child.kill();
				} catch {
					// The process may have exited between the liveness check and kill.
				}
			}
		} else {
			try {
				process.kill(-pid, "SIGTERM");
			} catch {
				try {
					process.kill(pid, "SIGTERM");
				} catch {
					// The process may have exited between group and direct kill.
				}
			}
		}
	}
	for (let attempt = 0; attempt < 50 && task.status === "running"; attempt++) await delay(100);
	if (task.status === "running" && pid && !isAlive(pid)) {
		// The OS has confirmed termination even if Node has not delivered close
		// yet. Settle from that observation so a successful stop is not reported
		// as a lost process merely because pipe teardown lagged.
		await settle(task, null, undefined);
	}
	if (task.status === "running" && pid && process.platform !== "win32") {
		try {
			process.kill(-pid, "SIGKILL");
		} catch {
			try {
				process.kill(pid, "SIGKILL");
			} catch {
				// The process may have exited before escalation.
			}
		}
	}
	for (let attempt = 0; attempt < 20 && task.status === "running"; attempt++) await delay(100);
	if (task.status === "running") {
		task.status = "lost";
		task.endedAt = Date.now();
		task.stopReason = `${task.stopReason}; exit could not be confirmed`;
		await task.log.close();
	}
}

async function settle(task, code, error) {
	if (task.status !== "running") return;
	task.exitCode = code;
	task.endedAt = Date.now();
	if (task.requestedStatus) task.status = task.requestedStatus;
	else if (error || code !== 0) {
		task.status = "failed";
		task.stopReason = error?.message ?? `Process exited with code ${String(code)}`;
	} else task.status = "completed";
	await task.log.close();
	pruneTasks();
	scheduleIdleExit();
}

function publicInfo(task) {
	return {
		taskId: task.taskId,
		pid: task.pid,
		status: task.status,
		background: task.background,
		startedAt: task.startedAt,
		endedAt: task.endedAt,
		exitCode: task.exitCode,
		stopReason: task.stopReason,
		logPath: task.logPath,
	};
}

function assertPrivateLogPath(value) {
	if (typeof value !== "string") throw new Error("Invalid log path");
	const resolved = path.resolve(value);
	const relative = path.relative(path.join(path.resolve(runtimeDir), "tasks"), resolved);
	if (relative.startsWith("..") || path.isAbsolute(relative))
		throw new Error("Log path escapes supervisor runtime directory");
	return resolved;
}

function createCappedLog(logPath) {
	mkdirSync(path.dirname(logPath), { recursive: true, mode: 0o700 });
	const stream = createWriteStream(logPath, { flags: "w", mode: 0o600 });
	let bytes = 0;
	let closed = false;
	return {
		write(chunk) {
			if (closed || bytes >= MAX_LOG_BYTES) return;
			const buffer = Buffer.from(chunk);
			const slice = buffer.subarray(0, MAX_LOG_BYTES - bytes);
			bytes += slice.length;
			stream.write(slice);
		},
		async close() {
			if (closed) return;
			closed = true;
			await new Promise((resolve) => stream.end(resolve));
		},
	};
}

function respond(socket, requestId, ok, result, error) {
	if (socket.destroyed) return;
	socket.write(
		`${JSON.stringify({ type: "response", requestId, ok, result, error: error instanceof Error ? error.message : String(error ?? "") })}\n`,
	);
}

function validToken(candidate) {
	if (typeof candidate !== "string" || !/^[a-f0-9]{64}$/.test(candidate) || candidate.length !== token.length)
		return false;
	return crypto.timingSafeEqual(Buffer.from(candidate), Buffer.from(token));
}

function sanitizeEnv(value, allowSensitive = false) {
	if (!value || typeof value !== "object" || Array.isArray(value)) {
		return safeInheritedEnvironment(process.env, { allowSensitive });
	}
	return scrubEnvironment(value, { allowSensitive });
}

function pruneTasks() {
	const terminal = [...tasks.values()]
		.filter((task) => task.status !== "running")
		.sort((a, b) => (b.endedAt ?? b.startedAt) - (a.endedAt ?? a.startedAt));
	for (const task of terminal.slice(MAX_RETAINED_TASKS)) tasks.delete(task.taskId);
}

function scheduleIdleExit() {
	clearTimeout(idleTimer);
	if (connectedClients > 0 || [...tasks.values()].some((task) => task.status === "running")) return;
	idleTimer = setTimeout(() => {
		server.close();
		if (process.platform !== "win32") void fs.rm(endpoint, { force: true });
		void cleanupControlFiles();
	}, ORPHAN_IDLE_TIMEOUT_MS);
	idleTimer.unref();
}

async function cleanupControlFiles() {
	const descriptorPath = path.join(runtimeDir, "supervisor.json");
	try {
		const descriptor = JSON.parse(await fs.readFile(descriptorPath, "utf8"));
		if (descriptor?.pid !== process.pid) return;
		await Promise.all([
			fs.rm(descriptorPath, { force: true }),
			fs.rm(path.join(runtimeDir, "supervisor.token"), { force: true }),
		]);
	} catch {
		// Missing or replaced control files are not ours to remove.
	}
}

function readStartup() {
	return new Promise((resolve) => {
		process.stdin.setEncoding("utf8");
		let input = "";
		process.stdin.on("data", (chunk) => {
			input += chunk;
			if (Buffer.byteLength(input, "utf8") > 4096) resolve(undefined);
		});
		process.stdin.on("end", () => {
			try {
				resolve(JSON.parse(input.trim()));
			} catch {
				resolve(undefined);
			}
		});
	});
}

function runTaskkill(pid) {
	return new Promise((resolve) => {
		const killer = spawn("taskkill", ["/T", "/F", "/PID", String(pid)], { stdio: "ignore", windowsHide: true });
		killer.once("error", resolve);
		killer.once("close", resolve);
	});
}

function isAlive(pid) {
	try {
		process.kill(pid, 0);
		return true;
	} catch (error) {
		return error?.code === "EPERM";
	}
}

function delay(ms) {
	return new Promise((resolve) => setTimeout(resolve, ms));
}
