import * as crypto from "node:crypto";
import * as fs from "node:fs/promises";
import * as path from "node:path";
import { createJsonFileStore } from "./json-file-store.js";
import type { Credential, CredentialStore } from "./types.js";
import { kagekoHomeDir } from "./home-dir.js";

const LOCK_RETRY_MS = 50;
const LOCK_STALE_MS = 30_000;
const LOCK_TIMEOUT_MS = 60_000;
const LOCK_HEARTBEAT_MS = 5_000;

export interface FileCredentialStoreOptions {
	/** Override the default `~/.kageko/auth.json` path. */
	filePath?: string;
}

export interface FileCredentialStore extends CredentialStore {
	list(): Promise<Record<string, Credential>>;
}

/**
 * Create a file-backed CredentialStore backed by `~/.kageko/auth.json`.
 *
 * Implements the local `CredentialStore` interface (read/modify/delete) with
 * both an in-memory queue and an on-disk lock. Mutations re-read the complete
 * credential file after acquiring the cross-process lock, so another process
 * can rotate a refresh token without a waiter consuming the stale token.
 */
export function createFileCredentialStore(options?: FileCredentialStoreOptions): FileCredentialStore {
	let lock: Promise<unknown> = Promise.resolve();
	const filePath = options?.filePath ?? path.join(kagekoHomeDir(), ".kageko", "auth.json");
	const backend = createJsonFileStore(filePath);

	/** Serialize tasks for the whole credential file. */
	function enqueue<T>(task: () => Promise<T>): Promise<T> {
		const previous = lock;
		const next = (async () => {
			await previous.catch(() => {});
			return task();
		})();
		lock = next.catch(() => {});
		return next;
	}

	return {
		async read(providerId: string): Promise<Credential | undefined> {
			return enqueue(async () => {
				const all = await backend.readAll<Credential>();
				return all[providerId];
			});
		},

		modify(
			providerId: string,
			fn: (current: Credential | undefined) => Promise<Credential | undefined>,
		): Promise<Credential | undefined> {
			return enqueue(() =>
				withCredentialFileLock(filePath, async () => {
					// This read deliberately happens after the file lock. It is the
					// cross-process refresh-token rotation check.
					const all = await backend.readAll<Credential>();
					const current = all[providerId];
					const next = await fn(current);
					if (next !== undefined) {
						all[providerId] = next;
						await backend.writeAll(all);
						return next;
					}
					return current;
				}),
			);
		},

		delete(providerId: string): Promise<void> {
			return enqueue(() =>
				withCredentialFileLock(filePath, async () => {
					const all = await backend.readAll<Credential>();
					delete all[providerId];
					await backend.writeAll(all);
				}),
			);
		},

		async list(): Promise<Record<string, Credential>> {
			return enqueue(() => backend.readAll<Credential>());
		},
	};
}

async function withCredentialFileLock<T>(filePath: string, task: () => Promise<T>): Promise<T> {
	const release = await acquireCredentialFileLock(filePath);
	try {
		return await task();
	} finally {
		await release();
	}
}

async function acquireCredentialFileLock(filePath: string): Promise<() => Promise<void>> {
	const lockPath = `${filePath}.lock`;
	const ownerPath = path.join(lockPath, "owner");
	const owner = `${process.pid}:${crypto.randomUUID()}`;
	const deadline = Date.now() + LOCK_TIMEOUT_MS;

	await fs.mkdir(path.dirname(filePath), { recursive: true, mode: 0o700 });
	while (true) {
		try {
			await fs.mkdir(lockPath, { mode: 0o700 });
			try {
				await fs.writeFile(ownerPath, owner, { encoding: "utf8", mode: 0o600, flag: "wx" });
			} catch (error) {
				await fs.rm(lockPath, { recursive: true, force: true }).catch(() => undefined);
				throw error;
			}
			break;
		} catch (error) {
			if ((error as NodeJS.ErrnoException).code !== "EEXIST") {
				throw new Error(`Unable to acquire credential lock ${lockPath}`, { cause: error });
			}
			await reclaimStaleLock(lockPath);
			if (Date.now() >= deadline) {
				throw new Error(`Timed out waiting for credential lock ${lockPath}`);
			}
			await delay(LOCK_RETRY_MS);
		}
	}

	let heartbeatRunning = false;
	const heartbeat = setInterval(() => {
		if (heartbeatRunning) return;
		heartbeatRunning = true;
		void refreshOwnedLock(lockPath, ownerPath, owner)
			.catch(() => undefined)
			.finally(() => {
				heartbeatRunning = false;
			});
	}, LOCK_HEARTBEAT_MS);
	heartbeat.unref();

	return async () => {
		clearInterval(heartbeat);
		if ((await readOwner(ownerPath)) !== owner) return;
		await fs.rm(lockPath, { recursive: true, force: true });
	};
}

async function refreshOwnedLock(lockPath: string, ownerPath: string, owner: string): Promise<void> {
	if ((await readOwner(ownerPath)) !== owner) return;
	const now = new Date();
	await fs.utimes(lockPath, now, now).catch(() => undefined);
}

async function reclaimStaleLock(lockPath: string): Promise<void> {
	let stat;
	try {
		stat = await fs.stat(lockPath);
	} catch (error) {
		if ((error as NodeJS.ErrnoException).code === "ENOENT") return;
		throw error;
	}
	if (Date.now() - stat.mtimeMs < LOCK_STALE_MS) return;

	const stalePath = `${lockPath}.stale-${process.pid}-${crypto.randomUUID()}`;
	try {
		await fs.rename(lockPath, stalePath);
	} catch (error) {
		if (["ENOENT", "EACCES", "EPERM"].includes((error as NodeJS.ErrnoException).code ?? "")) return;
		throw error;
	}
	await fs.rm(stalePath, { recursive: true, force: true }).catch(() => undefined);
}

async function readOwner(ownerPath: string): Promise<string | undefined> {
	try {
		return await fs.readFile(ownerPath, "utf8");
	} catch (error) {
		if ((error as NodeJS.ErrnoException).code === "ENOENT") return undefined;
		throw error;
	}
}

function delay(ms: number): Promise<void> {
	return new Promise((resolve) => setTimeout(resolve, ms));
}
