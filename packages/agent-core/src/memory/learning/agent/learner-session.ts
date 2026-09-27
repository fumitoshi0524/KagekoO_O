import { randomUUID } from "node:crypto";
import {
	EVENT_SCHEMA_VERSION,
	type DurableEvent,
	type DurableEventInput,
	type DurableEventType,
} from "@kageko/protocol";
import type { AgentSession } from "../../../agent/agent.js";
import type { JournalPort } from "../../../ports/repository.js";

/**
 * Session + journal surface for one bounded learner-agent run.
 *
 * The resident learner executes `KagekoAgent` turns exactly like a subagent,
 * but its `tool.call`/`tool.result`/`turn.*` journal events must never enter
 * the main session journal: the composition root's journal wrapper forwards
 * journaled events to the learning bus and to stream-json consumers, so
 * sharing it would feed the learner's own evidence back into the pipeline and
 * leak internal tool traffic into the user-facing transcript.
 *
 * The record store below is therefore an in-memory journal with the same
 * `JournalPort` shape: events are appended with full durable metadata (so
 * diagnostics can inspect a run), kept for the lifetime of the run, and then
 * dropped. The session carries no learning bus, no hook engine, no goal
 * store, and no injection manager — the narrowest surface `KagekoAgent` and
 * `TurnFlow` actually read.
 */
export interface LearnerRunScope {
	/** Minimal session surface; deliberately no learningBus/hookEngine/goalStore. */
	readonly session: AgentSession & { sessionId: string };
	/** Ephemeral per-run journal; nothing here is persisted or forwarded. */
	readonly recordStore: JournalPort;
	/** Events journaled by the run, in append order. */
	readonly events: readonly DurableEvent[];
}

export function createLearnerRunScope(sessionId: string): LearnerRunScope {
	const events: DurableEvent[] = [];
	let sequence = 0;
	const recordStore: JournalPort = {
		sessionId,
		append: async <K extends DurableEventType>(event: DurableEventInput<K>): Promise<DurableEvent<K>> => {
			const appended = {
				type: event.type,
				meta: {
					schemaVersion: EVENT_SCHEMA_VERSION,
					eventId: randomUUID(),
					sequence: ++sequence,
					sessionId,
					occurredAt: event.meta?.occurredAt ?? Date.now(),
					recordedAt: Date.now(),
					...event.meta,
				},
				data: event.data,
			} as DurableEvent<K>;
			events.push(appended);
			return appended;
		},
		load: async () => [...events],
	};
	// `turnAbortController` is assigned by KagekoAgent.prompt per turn; the
	// runner owns aborts, so no runTurn serializer is installed here (the
	// runner's own queue already serializes runs).
	const session: AgentSession & { sessionId: string } = {
		sessionId,
		isClosed: () => false,
		turnAbortController: null,
	};
	return { session, recordStore, events };
}
