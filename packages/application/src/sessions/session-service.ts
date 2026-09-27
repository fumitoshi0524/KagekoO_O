import { randomUUID } from "node:crypto";
import type {
	CreateSessionInput,
	SessionListQuery,
	SessionListResult,
	SessionRepository,
	SessionSummary as RepositorySessionSummary,
} from "@kageko/session-store";
import { SessionFactory, type PromptJournalAppender } from "./session-factory.js";
import { type AgentRuntime, type RuntimeSession } from "./runtime-session.js";

/**
 * The only application lifecycle owner for repository-backed sessions.
 * Runtime handles are cached here so application shutdown can close every
 * active prompt queue before the repository and process resources are torn down.
 */
export class SessionService {
	private readonly factory: SessionFactory;
	private readonly active = new Map<string, RuntimeSession>();
	/** Runtimes that failed before binding and must remain application-owned. */
	private readonly unboundRuntimes = new Map<string, Set<AgentRuntime>>();
	private readonly lifecycle = new Map<string, Promise<void>>();
	private closing = false;
	private closeAllPromise: Promise<void> | undefined;

	constructor(
		readonly repository: SessionRepository,
		readonly releaseResources?: (sessionId: string) => Promise<void>,
		readonly cancelInteractions?: (sessionId: string) => void | Promise<void>,
		appendPrompt?: PromptJournalAppender,
		private readonly onSessionClosed?: (sessionId: string, status: "closed" | "failed") => void,
	) {
		this.factory = new SessionFactory(repository, appendPrompt);
	}

	async create(input: CreateSessionInput): Promise<RuntimeSession> {
		return this.withLifecycle(input.sessionId, async () => {
			this.assertOpen();
			const summary = await this.repository.create(input);
			try {
				return await this.openRuntime(summary.sessionId);
			} catch (error) {
				await this.repository.delete(summary.sessionId).catch(() => {});
				throw error;
			}
		});
	}

	async resume(sessionId: string): Promise<RuntimeSession> {
		return this.withLifecycle(sessionId, async () => {
			this.assertOpen();
			return this.openRuntime(sessionId);
		});
	}

	/**
	 * Compose and bind the one execution runtime while holding the same per-session
	 * lifecycle gate used for resume and close.  A runtime can therefore never be
	 * published after a concurrent close has removed its owning RuntimeSession.
	 */
	async composeRuntime(
		sessionId: string,
		compose: (session: RuntimeSession) => Promise<AgentRuntime>,
	): Promise<RuntimeSession> {
		return this.withLifecycle(sessionId, async () => {
			this.assertOpen();
			const session = await this.openRuntime(sessionId);
			const runtime = await compose(session);
			try {
				if (this.closing) throw new Error("Application is closing");
				session.bindRuntime(runtime);
				return session;
			} catch (error) {
				try {
					await runtime.close();
				} catch (cleanupError) {
					this.retainUnboundRuntime(sessionId, runtime);
					throw new AggregateError(
						[error, cleanupError],
						`Failed to compose and clean up runtime for session ${sessionId}`,
					);
				}
				throw error;
			}
		});
	}

	list(query?: SessionListQuery): Promise<readonly RepositorySessionSummary[]> {
		return this.repository.list(query);
	}

	listWithDiagnostics(query?: SessionListQuery): Promise<SessionListResult> {
		return this.repository.listWithDiagnostics(query);
	}

	/** Read-only lifecycle projection.  Never opens a repository session. */
	activeSnapshot(sessionId: string): ReturnType<RuntimeSession["snapshot"]> | undefined {
		return this.active.get(sessionId)?.snapshot();
	}

	/** Internal composition access; never reopens a persisted session. */
	activeSession(sessionId: string): RuntimeSession | undefined {
		return this.active.get(sessionId);
	}

	/**
	 * Serialize a short mutation of an already-open runtime with composition and
	 * close.  Application orchestration uses this for capability replacement and
	 * prompt admission so no turn can observe a half-swapped session graph.
	 */
	async useActiveRuntime<T>(sessionId: string, operation: (session: RuntimeSession) => Promise<T> | T): Promise<T> {
		return this.withLifecycle(sessionId, async () => {
			this.assertOpen();
			const session = this.active.get(sessionId);
			if (!session) throw new Error(`Session ${sessionId} is not active`);
			return operation(session);
		});
	}

	async rename(sessionId: string, title: string): Promise<void> {
		await this.repository.updateMetadata(sessionId, { title: title.trim() || null });
	}

	async archive(sessionId: string, archived = true): Promise<void> {
		if (archived) await this.repository.archive(sessionId);
		else await this.repository.updateMetadata(sessionId, { archived: false });
	}

	async delete(sessionId: string): Promise<void> {
		await this.close(sessionId);
		await this.repository.delete(sessionId);
	}

	async fork(
		sourceId: string,
		forkId = `fork-${Date.now().toString(36)}-${randomUUID().slice(0, 8)}`,
	): Promise<RuntimeSession> {
		if (sourceId === forkId) throw new Error("Fork session id must differ from the source session id");
		return this.withLifecycle(forkId, async () => {
			this.assertOpen();
			const source = await this.repository.get(sourceId);
			if (!source) throw new Error(`Unknown session: ${sourceId}`);
			const events = await this.repository.read(sourceId);
			const target = await this.repository.create({
				sessionId: forkId,
				cwd: source.cwd,
				title: source.title ? `Fork: ${source.title}` : null,
			});
			try {
				const copied = events.map((event, index) => ({
					...event,
					meta: {
						...event.meta,
						eventId: randomUUID(),
						sequence: index + 2,
						sessionId: forkId,
						causationId: event.meta.eventId,
					},
				}));
				await this.repository.append(forkId, [
					{
						type: "session.forked",
						meta: {
							schemaVersion: 1,
							eventId: randomUUID(),
							sequence: 1,
							sessionId: forkId,
							occurredAt: Date.now(),
							recordedAt: Date.now(),
						},
						data: {
							sourceSessionId: sourceId,
							sourceEventCount: events.length,
							sourceLastEventId: events.at(-1)?.meta.eventId,
						},
					},
					...copied,
				] as never);
				return await this.openRuntime(target.sessionId);
			} catch (error) {
				// Fork creation is all-or-nothing from the application boundary.  The
				// repository may have created metadata before a journal or runtime
				// failure, so remove only that known target and preserve the source.
				this.active.delete(target.sessionId);
				await this.repository.delete(target.sessionId).catch(() => {});
				throw error;
			}
		});
	}

	async close(sessionId: string): Promise<void> {
		return this.withLifecycle(sessionId, async () => {
			const runtime = this.active.get(sessionId);
			if (!runtime) return;
			try {
				await this.closeRuntime(sessionId, runtime);
			} catch (error) {
				// A retained failed runtime is a terminal state for waiters too:
				// they must hear "failed" instead of hanging on a silent retry loop.
				this.onSessionClosed?.(sessionId, "failed");
				throw error;
			}
			// Keep ownership until the entire close chain succeeds. Otherwise a
			// failed resource release turns an active runtime into an unreachable
			// leak that application shutdown cannot retry.
			this.active.delete(sessionId);
			this.onSessionClosed?.(sessionId, "closed");
		});
	}

	async closeAll(): Promise<void> {
		if (this.closeAllPromise) return this.closeAllPromise;
		this.closing = true;
		this.closeAllPromise = (async () => {
			await Promise.allSettled([...this.lifecycle.values()]);
			const runtimes = [...this.active.entries()];
			const results = await Promise.allSettled(
				runtimes.map(([sessionId, runtime]) => this.closeRuntime(sessionId, runtime)),
			);
			for (const [index, result] of results.entries()) {
				if (result.status === "fulfilled") {
					this.active.delete(runtimes[index]![0]);
					this.onSessionClosed?.(runtimes[index]![0], "closed");
				} else {
					this.onSessionClosed?.(runtimes[index]![0], "failed");
				}
			}
			const failures = results.filter((result): result is PromiseRejectedResult => result.status === "rejected");
			if (failures.length)
				throw new AggregateError(
					failures.map((failure) => failure.reason),
					"Failed to close active sessions",
				);
		})();
		try {
			await this.closeAllPromise;
		} catch (error) {
			// Retain failed runtimes and let the composition root retry shutdown.
			this.closeAllPromise = undefined;
			throw error;
		}
	}

	private assertOpen(): void {
		if (this.closing) throw new Error("Application is closing");
	}
	private async openRuntime(sessionId: string): Promise<RuntimeSession> {
		const existing = this.active.get(sessionId);
		if (existing) return existing;
		const runtime = await this.factory.resume(sessionId);
		if (this.closing) {
			await runtime.close();
			throw new Error("Application is closing");
		}
		this.active.set(sessionId, runtime);
		return runtime;
	}
	private async withLifecycle<T>(sessionId: string, operation: () => Promise<T>): Promise<T> {
		const prior = this.lifecycle.get(sessionId) ?? Promise.resolve();
		const result = prior.then(operation, operation);
		const settled = result.then(
			() => undefined,
			() => undefined,
		);
		this.lifecycle.set(sessionId, settled);
		void settled.finally(() => {
			if (this.lifecycle.get(sessionId) === settled) this.lifecycle.delete(sessionId);
		});
		return result;
	}
	private async closeRuntime(sessionId: string, runtime: RuntimeSession): Promise<void> {
		// Unblock pending approvals/questions first so an in-flight turn that is
		// waiting on them can unwind instead of holding the turn lock until the
		// drain timeout. Also include any runtime that failed before it could bind
		// to the facade; that object still owns process/MCP/lease resources.
		const detached = [...(this.unboundRuntimes.get(sessionId) ?? [])];
		const results = await Promise.allSettled([
			Promise.resolve(this.cancelInteractions?.(sessionId)),
			runtime.close(),
			...detached.map((candidate) => candidate.close()),
		]);
		for (const [index, result] of results.slice(2).entries()) {
			if (result.status === "fulfilled") this.unboundRuntimes.get(sessionId)?.delete(detached[index]!);
		}
		if (this.unboundRuntimes.get(sessionId)?.size === 0) this.unboundRuntimes.delete(sessionId);
		const release = await Promise.allSettled([Promise.resolve(this.releaseResources?.(sessionId))]);
		const failures = [...results, ...release].filter(
			(result): result is PromiseRejectedResult => result.status === "rejected",
		);
		if (failures.length === 1) throw failures[0]!.reason;
		if (failures.length)
			throw new AggregateError(
				failures.map((failure) => failure.reason),
				`Failed to close session ${sessionId}`,
			);
	}
	private retainUnboundRuntime(sessionId: string, runtime: AgentRuntime): void {
		const runtimes = this.unboundRuntimes.get(sessionId) ?? new Set<AgentRuntime>();
		runtimes.add(runtime);
		this.unboundRuntimes.set(sessionId, runtimes);
	}
}
