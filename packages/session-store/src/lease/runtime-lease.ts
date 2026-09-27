import { randomUUID } from "node:crypto";
import * as fs from "node:fs/promises";
import * as os from "node:os";
import * as path from "node:path";
import * as lockfile from "proper-lockfile";

const OWNER_VERSION = 1 as const;
const LOCK_DIRECTORY_NAME = ".runtime.lock";
const OWNER_FILE_NAME = ".runtime-owner.json";
const NORMAL_STALE_MS = Number.MAX_SAFE_INTEGER;
const NORMAL_UPDATE_MS = 10_000;
const DEAD_OWNER_STALE_MS = 5_000;
const DEAD_OWNER_UPDATE_MS = 1_000;

export interface RuntimeLeaseOwner {
	readonly version: typeof OWNER_VERSION;
	readonly sessionId: string;
	readonly instanceId: string;
	readonly pid: number;
	readonly hostname: string;
	readonly startedAt: number;
}

export class RuntimeLeaseError extends Error {
	constructor(message: string, options?: ErrorOptions) {
		super(message, options);
		this.name = new.target.name;
	}
}

export class RuntimeLeaseBusyError extends RuntimeLeaseError {
	readonly owner?: RuntimeLeaseOwner;

	constructor(sessionId: string, owner?: RuntimeLeaseOwner, options?: ErrorOptions) {
		const ownerDescription = owner
			? `pid ${owner.pid} on ${owner.hostname}, started ${new Date(owner.startedAt).toISOString()}`
			: "an unknown owner";
		super(`Session "${sessionId}" is already owned by ${ownerDescription}`, options);
		this.owner = owner;
	}
}

export class RuntimeLeaseCompromisedError extends RuntimeLeaseError {}

interface CompromiseState {
	error: Error | undefined;
}

/**
 * Cross-process, cross-platform ownership lease for one session runtime.
 *
 * The underlying lock uses atomic mkdir plus an mtime heartbeat. A foreign-host
 * lock is never considered stale automatically. A same-host owner whose PID no
 * longer exists is recovered through the lock library's stale-lock protocol.
 */
export class RuntimeLease {
	readonly sessionDir: string;
	readonly sessionId: string;
	readonly lockPath: string;
	readonly ownerPath: string;
	readonly owner: RuntimeLeaseOwner;
	private _releaseLock: (() => Promise<void>) | undefined;
	private readonly _compromiseState: CompromiseState;
	private _released = false;

	private constructor(
		sessionDir: string,
		sessionId: string,
		owner: RuntimeLeaseOwner,
		releaseLock: () => Promise<void>,
		compromiseState: CompromiseState,
	) {
		this.sessionDir = sessionDir;
		this.sessionId = sessionId;
		this.lockPath = path.join(sessionDir, LOCK_DIRECTORY_NAME);
		this.ownerPath = path.join(sessionDir, OWNER_FILE_NAME);
		this.owner = owner;
		this._releaseLock = releaseLock;
		this._compromiseState = compromiseState;
	}

	static async acquire(sessionDir: string, sessionId: string): Promise<RuntimeLease> {
		if (!sessionId) {
			throw new TypeError("RuntimeLease requires a non-empty sessionId");
		}
		const resolvedDir = path.resolve(sessionDir);
		await fs.mkdir(resolvedDir, { recursive: true });
		const lockPath = path.join(resolvedDir, LOCK_DIRECTORY_NAME);
		const ownerPath = path.join(resolvedDir, OWNER_FILE_NAME);
		const compromiseState: CompromiseState = { error: undefined };
		const normalOptions: lockfile.LockOptions = {
			realpath: false,
			lockfilePath: lockPath,
			stale: NORMAL_STALE_MS,
			update: NORMAL_UPDATE_MS,
			retries: 0,
			onCompromised: (error) => {
				compromiseState.error = error;
			},
		};

		let releaseLock: (() => Promise<void>) | undefined;
		try {
			releaseLock = await lockfile.lock(resolvedDir, normalOptions);
		} catch (error) {
			if (!isLockBusyError(error)) {
				throw new RuntimeLeaseError(`Failed to acquire runtime lease for session "${sessionId}"`, {
					cause: error,
				});
			}
			const existingOwner = await readOwner(ownerPath);
			if (
				existingOwner &&
				(existingOwner.sessionId !== sessionId ||
					existingOwner.hostname !== os.hostname() ||
					isProcessAlive(existingOwner.pid))
			) {
				throw new RuntimeLeaseBusyError(sessionId, existingOwner, { cause: error });
			}

			// The owner is on this host and its PID no longer exists. Use a
			// consistent short stale/update pair so concurrent reclaimers remain
			// mutually exclusive inside proper-lockfile's tested recovery path.
			try {
				releaseLock = await lockfile.lock(resolvedDir, {
					...normalOptions,
					stale: DEAD_OWNER_STALE_MS,
					update: DEAD_OWNER_UPDATE_MS,
					retries: {
						retries: 8,
						factor: 1,
						minTimeout: 750,
						maxTimeout: 750,
					},
				});
			} catch (recoveryError) {
				throw new RuntimeLeaseBusyError(sessionId, await readOwner(ownerPath), {
					cause: recoveryError,
				});
			}
		}

		const owner: RuntimeLeaseOwner = {
			version: OWNER_VERSION,
			sessionId,
			instanceId: randomUUID(),
			pid: process.pid,
			hostname: os.hostname(),
			startedAt: Date.now(),
		};
		try {
			await writeOwner(ownerPath, owner);
		} catch (error) {
			await releaseLock().catch(() => {});
			throw new RuntimeLeaseError(`Failed to publish runtime lease owner for session "${sessionId}"`, {
				cause: error,
			});
		}

		return new RuntimeLease(resolvedDir, sessionId, owner, releaseLock, compromiseState);
	}

	assertOwned(): void {
		if (this._released) {
			throw new RuntimeLeaseCompromisedError(`Runtime lease for session "${this.sessionId}" has been released`);
		}
		if (this._compromiseState.error) {
			throw new RuntimeLeaseCompromisedError(`Runtime lease for session "${this.sessionId}" was compromised`, {
				cause: this._compromiseState.error,
			});
		}
	}

	async release(): Promise<void> {
		if (this._released) {
			return;
		}
		const releaseLock = this._releaseLock;
		this._releaseLock = undefined;

		// Move our metadata out of the canonical location while the lock is
		// still held. This prevents cleanup from deleting a newer owner's file.
		// Every step here is idempotent so a retried release after a failed
		// unlock is safe: the owner file may already be tombstoned and the
		// tombstone may already be gone.
		const tombstonePath = `${this.ownerPath}.${this.owner.instanceId}.released`;
		try {
			const current = await readOwner(this.ownerPath);
			if (current?.instanceId === this.owner.instanceId) {
				await fs.rename(this.ownerPath, tombstonePath);
			}
		} catch (error) {
			if ((error as NodeJS.ErrnoException).code !== "ENOENT") {
				this._compromiseState.error ??= error as Error;
			}
		}

		try {
			await releaseLock?.();
		} catch (error) {
			// The unlock failed, so the underlying mkdir lock is still held.
			// Stay unreleased and restore the release function so the next
			// release() retries the unlock instead of leaking the lock forever.
			this._releaseLock ??= releaseLock;
			throw error;
		} finally {
			await fs.unlink(tombstonePath).catch(() => {});
		}
		this._released = true;
	}
}

async function readOwner(ownerPath: string): Promise<RuntimeLeaseOwner | undefined> {
	let parsed: unknown;
	try {
		parsed = JSON.parse(await fs.readFile(ownerPath, "utf8")) as unknown;
	} catch (error) {
		if ((error as NodeJS.ErrnoException).code === "ENOENT") {
			return undefined;
		}
		return undefined;
	}
	if (!isRecord(parsed)) {
		return undefined;
	}
	if (
		parsed["version"] !== OWNER_VERSION ||
		typeof parsed["sessionId"] !== "string" ||
		typeof parsed["instanceId"] !== "string" ||
		!Number.isSafeInteger(parsed["pid"]) ||
		typeof parsed["hostname"] !== "string" ||
		typeof parsed["startedAt"] !== "number"
	) {
		return undefined;
	}
	return parsed as unknown as RuntimeLeaseOwner;
}

async function writeOwner(ownerPath: string, owner: RuntimeLeaseOwner): Promise<void> {
	const temporaryPath = `${ownerPath}.${owner.instanceId}.tmp`;
	let handle: fs.FileHandle | undefined;
	try {
		handle = await fs.open(temporaryPath, "wx");
		await handle.writeFile(`${JSON.stringify(owner)}\n`, "utf8");
		await handle.sync();
		await handle.close();
		handle = undefined;
		await fs.rename(temporaryPath, ownerPath);
	} catch (error) {
		await handle?.close().catch(() => {});
		await fs.unlink(temporaryPath).catch(() => {});
		throw error;
	}
}

function isProcessAlive(pid: number): boolean {
	if (!Number.isSafeInteger(pid) || pid <= 0) {
		return false;
	}
	try {
		process.kill(pid, 0);
		return true;
	} catch (error) {
		const code = (error as NodeJS.ErrnoException).code;
		return code !== "ESRCH";
	}
}

function isLockBusyError(error: unknown): boolean {
	return (error as NodeJS.ErrnoException | undefined)?.code === "ELOCKED";
}

function isRecord(value: unknown): value is Record<string, unknown> {
	return value !== null && typeof value === "object" && !Array.isArray(value);
}
