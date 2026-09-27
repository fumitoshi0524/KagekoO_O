import { access, mkdir, readdir, rm, rmdir } from "node:fs/promises";
import { createHash } from "node:crypto";
import path from "node:path";
import * as lockfile from "proper-lockfile";
import type {
	CreateSessionInput,
	RuntimeSessionRepository,
	SessionListQuery,
	SessionListResult,
	SessionMetadataPatch,
	SessionSnapshot,
	SessionSummary,
} from "./session-repository.js";
import type { DurableEvent, DurableEventInput } from "@kageko/protocol";
import { JournalWriter } from "../journal/journal-writer.js";
import { SessionPaths } from "../paths/session-paths.js";
import { MetadataStore } from "../metadata/metadata-store.js";
import { SnapshotReader } from "../snapshot/snapshot-reader.js";
import { SnapshotWriter } from "../snapshot/snapshot-writer.js";
import { JournalReader } from "../journal/journal-reader.js";
import { JournalLock } from "../journal/journal-lock.js";
import { RuntimeLease } from "../lease/runtime-lease.js";
import { persistenceDiagnostic, SessionPersistenceError } from "../diagnostics.js";
import type { SessionPersistenceDiagnostic } from "../diagnostics.js";
import { JournalRecovery } from "../journal/journal-recovery.js";

export class FileSessionRepository implements RuntimeSessionRepository {
	private readonly writers = new Map<string, JournalWriter>();
	private readonly lock = new JournalLock();
	constructor(readonly rootDir: string) {}
	async create(input: CreateSessionInput): Promise<SessionSummary> {
		const paths = new SessionPaths(this.rootDir, input.sessionId);
		return this.withSessionLock(input.sessionId, async () => {
			if (await new MetadataStore(paths.metadata, input.sessionId).read())
				throw new Error(`Session already exists: ${input.sessionId}`);
			const now = Date.now();
			const value = {
				sessionId: input.sessionId,
				cwd: input.cwd,
				title: input.title ?? null,
				createdAt: now,
				updatedAt: now,
				archived: false,
			};
			await mkdir(paths.directory, { recursive: true, mode: 0o700 });
			await new MetadataStore(paths.metadata, input.sessionId).create(value);
			return value;
		});
	}
	async get(sessionId: string): Promise<SessionSummary | undefined> {
		return new MetadataStore(new SessionPaths(this.rootDir, sessionId).metadata, sessionId).read();
	}
	async list(query: SessionListQuery = {}): Promise<readonly SessionSummary[]> {
		return (await this.collectSessions(query, false)).sessions;
	}
	async listWithDiagnostics(query: SessionListQuery = {}): Promise<SessionListResult> {
		return this.collectSessions(query, true);
	}
	private async collectSessions(query: SessionListQuery, inspectPersistence: boolean): Promise<SessionListResult> {
		const entries = await readdir(this.rootDir, { withFileTypes: true }).catch((error: unknown) => {
			if ((error as NodeJS.ErrnoException).code === "ENOENT") return [];
			throw error;
		});
		const results: SessionSummary[] = [];
		const diagnostics: SessionPersistenceDiagnostic[] = [];
		const search = query.search?.trim().toLocaleLowerCase();
		for (const entry of entries) {
			if (!entry.isDirectory() || entry.name === ".repository-locks") continue;
			const paths = new SessionPaths(this.rootDir, entry.name);
			let summary: SessionSummary | undefined;
			try {
				summary = await this.get(entry.name);
			} catch (error) {
				if (error instanceof SessionPersistenceError) diagnostics.push(error.diagnostic);
				else throw error;
				continue;
			}
			if (!summary) {
				diagnostics.push(
					persistenceDiagnostic("metadata-missing", entry.name, paths.metadata, "Session directory has no metadata"),
				);
				continue;
			}
			if (inspectPersistence) diagnostics.push(...(await this.inspectSessionPersistence(paths, summary)));
			if (!query.includeArchived && summary.archived) continue;
			if (query.cwd !== undefined && normalizePath(summary.cwd) !== normalizePath(query.cwd)) continue;
			if (
				search &&
				![summary.sessionId, summary.title ?? "", summary.cwd].some((value) =>
					value.toLocaleLowerCase().includes(search),
				)
			)
				continue;
			results.push(summary);
		}
		results.sort(
			(a, b) => b.updatedAt - a.updatedAt || b.createdAt - a.createdAt || a.sessionId.localeCompare(b.sessionId),
		);
		return { sessions: results, diagnostics };
	}
	async updateMetadata(sessionId: string, patch: SessionMetadataPatch): Promise<SessionSummary> {
		return this.withSessionLock(sessionId, async () => {
			const current = await this.get(sessionId);
			if (!current) throw new Error(`Unknown session: ${sessionId}`);
			return new MetadataStore(new SessionPaths(this.rootDir, sessionId).metadata, sessionId).patch(patch);
		});
	}
	async archive(sessionId: string): Promise<void> {
		await this.updateMetadata(sessionId, { archived: true });
	}
	async delete(sessionId: string): Promise<void> {
		await this.withSessionLock(sessionId, async () => {
			const paths = new SessionPaths(this.rootDir, sessionId);
			if (!(await this.get(sessionId))) throw new Error(`Unknown session: ${sessionId}`);
			const leaseHeld = await lockfile.check(paths.directory, {
				realpath: false,
				lockfilePath: path.join(paths.directory, ".runtime.lock"),
				stale: Number.MAX_SAFE_INTEGER,
			});
			if (leaseHeld) throw new Error(`Cannot delete session "${sessionId}" while its runtime lease is held`);
			await rm(paths.directory, { recursive: true, force: false });
			this.writers.delete(sessionId);
		});
	}
	async append(sessionId: string, events: readonly DurableEvent[]): Promise<void> {
		await this.withSessionLock(sessionId, async () => {
			const paths = new SessionPaths(this.rootDir, sessionId);
			if (!(await this.get(sessionId))) throw new Error(`Unknown session: ${sessionId}`);
			if (events.length === 0) return;
			let writer = this.writers.get(sessionId) ?? new JournalWriter(paths.directory, { sessionId });
			this.writers.set(sessionId, writer);
			try {
				await writer.load();
				await writer.appendEvents(events);
			} catch (error) {
				this.writers.delete(sessionId);
				if (!isSequenceMismatch(error)) throw error;
				writer = new JournalWriter(paths.directory, { sessionId });
				await writer.load();
				this.writers.set(sessionId, writer);
				await writer.appendEvents(events);
			}
			await new MetadataStore(paths.metadata, sessionId).patch({});
		});
	}
	async appendInputs(sessionId: string, events: readonly DurableEventInput[]): Promise<readonly DurableEvent[]> {
		return this.withSessionLock(sessionId, async () => {
			const paths = new SessionPaths(this.rootDir, sessionId);
			if (!(await this.get(sessionId))) throw new Error(`Unknown session: ${sessionId}`);
			if (events.length === 0) return [];
			let writer = this.writers.get(sessionId) ?? new JournalWriter(paths.directory, { sessionId });
			this.writers.set(sessionId, writer);
			let appended: readonly DurableEvent[];
			try {
				await writer.load();
				appended = await writer.appendInputs(events);
			} catch (error) {
				this.writers.delete(sessionId);
				if (!isSequenceMismatch(error)) throw error;
				writer = new JournalWriter(paths.directory, { sessionId });
				await writer.load();
				this.writers.set(sessionId, writer);
				appended = await writer.appendInputs(events);
			}
			await new MetadataStore(paths.metadata, sessionId).patch({});
			return appended;
		});
	}
	async read(sessionId: string, fromSequence = 1): Promise<readonly DurableEvent[]> {
		return this.withSessionLock(sessionId, async () => {
			const paths = new SessionPaths(this.rootDir, sessionId);
			if (!(await this.get(sessionId))) throw new Error(`Unknown session: ${sessionId}`);
			await this.recoverAndSyncWriter(paths, sessionId);
			return new JournalReader(paths.journal, sessionId).read(fromSequence);
		});
	}
	async writeSnapshot(sessionId: string, snapshot: SessionSnapshot): Promise<void> {
		await this.withSessionLock(sessionId, async () => {
			if (!(await this.get(sessionId))) throw new Error(`Unknown session: ${sessionId}`);
			const paths = new SessionPaths(this.rootDir, sessionId);
			const events = await this.readUnlocked(paths, sessionId);
			const latestSequence = events.at(-1)?.meta.sequence ?? 0;
			if (snapshot.sequence > latestSequence) {
				throw new SessionPersistenceError(
					persistenceDiagnostic(
						"snapshot-ahead-of-journal",
						sessionId,
						paths.snapshot,
						`Snapshot sequence ${snapshot.sequence} exceeds journal sequence ${latestSequence}`,
					),
				);
			}
			const current = await new SnapshotReader(paths.snapshot, sessionId).read();
			if (current && snapshot.sequence < current.sequence)
				throw new Error(`Snapshot sequence cannot move backwards from ${current.sequence} to ${snapshot.sequence}`);
			await new SnapshotWriter(paths.snapshot, sessionId).write(snapshot);
		});
	}
	async readSnapshot(sessionId: string): Promise<SessionSnapshot | undefined> {
		return this.withSessionLock(sessionId, async () => {
			if (!(await this.get(sessionId))) throw new Error(`Unknown session: ${sessionId}`);
			return new SnapshotReader(new SessionPaths(this.rootDir, sessionId).snapshot, sessionId).read();
		});
	}
	async acquireRuntimeLease(sessionId: string): Promise<RuntimeLease> {
		if (!(await this.get(sessionId))) throw new Error(`Unknown session: ${sessionId}`);
		return RuntimeLease.acquire(new SessionPaths(this.rootDir, sessionId).directory, sessionId);
	}
	private withSessionLock<T>(sessionId: string, operation: () => Promise<T>): Promise<T> {
		return this.lock.run(new SessionPaths(this.rootDir, sessionId).directory.toLowerCase(), async () => {
			// A stable per-session lock namespace preserves cross-process isolation
			// without serializing unrelated session journals behind one root lock.
			await mkdir(this.rootDir, { recursive: true, mode: 0o700 });
			const lockRoot = path.join(this.rootDir, ".repository-locks");
			const lockTarget = path.join(lockRoot, createHash("sha256").update(sessionId).digest("hex"));
			await mkdir(lockTarget, { recursive: true, mode: 0o700 });
			const release = await lockfile.lock(lockTarget, {
				realpath: false,
				// A holder that dies mid-operation (SIGKILL, container kill) never
				// releases. Let the lock go stale and keep retrying past the stale
				// window so crash recovery does not strand the session journal;
				// live holders release in milliseconds and are unaffected.
				stale: 10_000,
				retries: { retries: 60, factor: 1.2, minTimeout: 50, maxTimeout: 500 },
			});
			try {
				return await operation();
			} finally {
				await release().catch(() => {});
				await rmdir(lockTarget).catch(() => {});
				await rmdir(lockRoot).catch(() => {});
			}
		});
	}

	private async readUnlocked(paths: SessionPaths, sessionId: string): Promise<readonly DurableEvent[]> {
		try {
			await access(paths.journal);
		} catch (error) {
			if ((error as NodeJS.ErrnoException).code === "ENOENT") return [];
			throw error;
		}
		return new JournalReader(paths.journal, sessionId).read();
	}

	private async recoverAndSyncWriter(paths: SessionPaths, sessionId: string): Promise<void> {
		await new JournalRecovery(paths.journal, sessionId).recoverTruncatedTail();
		const writer = this.writers.get(sessionId);
		if (writer) await writer.load();
	}

	private async inspectSessionPersistence(
		paths: SessionPaths,
		summary: SessionSummary,
	): Promise<SessionPersistenceDiagnostic[]> {
		return this.withSessionLock(summary.sessionId, async () => {
			const diagnostics: SessionPersistenceDiagnostic[] = [];
			let latestSequence = 0;
			try {
				const journal = await new JournalRecovery(paths.journal, summary.sessionId).inspect();
				latestSequence = journal.events.at(-1)?.meta.sequence ?? 0;
				if (journal.truncated) {
					diagnostics.push(
						persistenceDiagnostic(
							"journal-truncated",
							summary.sessionId,
							paths.journal,
							`Journal has ${journal.discardedBytes} recoverable trailing bytes`,
						),
					);
				}
			} catch (error) {
				diagnostics.push(
					persistenceDiagnostic("journal-corrupt", summary.sessionId, paths.journal, errorMessage(error)),
				);
			}

			try {
				const snapshot = await new SnapshotReader(paths.snapshot, summary.sessionId).read();
				if (snapshot && snapshot.sequence > latestSequence) {
					diagnostics.push(
						persistenceDiagnostic(
							"snapshot-ahead-of-journal",
							summary.sessionId,
							paths.snapshot,
							`Snapshot sequence ${snapshot.sequence} exceeds journal sequence ${latestSequence}`,
						),
					);
				}
			} catch (error) {
				if (error instanceof SessionPersistenceError) diagnostics.push(error.diagnostic);
				else
					diagnostics.push(
						persistenceDiagnostic("snapshot-corrupt", summary.sessionId, paths.snapshot, errorMessage(error)),
					);
			}
			return diagnostics;
		});
	}
}

function normalizePath(value: string): string {
	const normalized = path.resolve(value).replaceAll("\\", "/");
	return process.platform === "win32" ? normalized.toLocaleLowerCase() : normalized;
}

function errorMessage(error: unknown): string {
	return error instanceof Error ? error.message : String(error);
}

function isSequenceMismatch(error: unknown): boolean {
	return error instanceof Error && /sequence mismatch/i.test(error.message);
}
