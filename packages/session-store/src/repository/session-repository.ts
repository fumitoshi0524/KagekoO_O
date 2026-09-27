export interface SessionSummary {
	readonly sessionId: string;
	readonly cwd: string;
	readonly title: string | null;
	readonly createdAt: number;
	readonly updatedAt: number;
	readonly archived: boolean;
}
export interface SessionSnapshot {
	readonly schemaVersion: number;
	readonly sessionId: string;
	readonly sequence: number;
	readonly state: unknown;
}
export interface SessionMetadataPatch {
	readonly title?: string | null;
	readonly archived?: boolean;
}
export interface CreateSessionInput {
	readonly sessionId: string;
	readonly cwd: string;
	readonly title?: string | null;
}
import type { SessionPersistenceDiagnostic } from "../diagnostics.js";
export interface SessionListQuery {
	readonly includeArchived?: boolean;
	readonly cwd?: string;
	readonly search?: string;
}
export interface SessionListResult {
	readonly sessions: readonly SessionSummary[];
	readonly diagnostics: readonly SessionPersistenceDiagnostic[];
}
import type { DurableEvent, DurableEventInput } from "@kageko/protocol";
import type { RuntimeLease } from "../lease/runtime-lease.js";
export interface SessionRepository {
	create(input: CreateSessionInput): Promise<SessionSummary>;
	get(sessionId: string): Promise<SessionSummary | undefined>;
	list(query?: SessionListQuery): Promise<readonly SessionSummary[]>;
	listWithDiagnostics(query?: SessionListQuery): Promise<SessionListResult>;
	updateMetadata(sessionId: string, patch: SessionMetadataPatch): Promise<SessionSummary>;
	archive(sessionId: string): Promise<void>;
	delete(sessionId: string): Promise<void>;
	append(sessionId: string, events: readonly DurableEvent[]): Promise<void>;
	appendInputs(sessionId: string, events: readonly DurableEventInput[]): Promise<readonly DurableEvent[]>;
	read(sessionId: string, fromSequence?: number): Promise<readonly DurableEvent[]>;
	writeSnapshot(sessionId: string, snapshot: SessionSnapshot): Promise<void>;
	readSnapshot(sessionId: string): Promise<SessionSnapshot | undefined>;
}

/**
 * Persistence capability required by an executable application session.
 * CRUD-only repositories remain useful for offline tooling, while a runtime
 * must explicitly provide exclusive ownership rather than be type-tested for
 * one concrete implementation.
 */
export interface RuntimeSessionRepository extends SessionRepository {
	acquireRuntimeLease(sessionId: string): Promise<RuntimeLease>;
}
