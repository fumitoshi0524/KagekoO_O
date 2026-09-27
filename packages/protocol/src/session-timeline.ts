import type { DurableEvent } from "./events.js";

/** A recoverable coordinator, tool, process, or subagent session state. */
export interface SessionTimelineEntry {
	readonly sequence: number;
	readonly eventId: string;
	readonly occurredAt: number;
	readonly timelineId?: string;
	readonly actorId?: string;
	readonly activityId?: string;
	readonly kind: "user" | "assistant" | "tool" | "subagent" | "process" | "turn" | "goal" | "session";
	readonly label: string;
	/** External effects are retained in the audit trail and cannot be undone. */
	readonly hasExternalEffects: boolean;
}

export interface SessionRestoreResult {
	readonly sessionId: string;
	readonly restoredToSequence: number;
	readonly timelineId: string;
	readonly externalEffectsRetained: number;
}

/**
 * Returns the branch which will receive the next durable session event.
 * Undefined denotes the original, pre-restore branch.
 */
export function currentSessionTimelineId(events: readonly DurableEvent[]): string | undefined {
	for (let index = events.length - 1; index >= 0; index -= 1) {
		const event = events[index];
		if (event?.type === "session.restored") return event.data.timelineId;
	}
	return undefined;
}

/**
 * Reconstructs the currently selected logical history without deleting the
 * append-only audit log. A restore event branches from a source sequence; later
 * events in the new branch are retained while abandoned sibling events remain
 * available to the timeline browser.
 */
export function effectiveSessionEvents(events: readonly DurableEvent[]): DurableEvent[] {
	return materializeTimeline(events, currentSessionTimelineId(events));
}

/** Materializes a branch through an optional inclusive durable sequence. */
export function materializeSessionTimeline(
	events: readonly DurableEvent[],
	timelineId: string | undefined,
	throughSequence?: number,
): DurableEvent[] {
	return materializeTimeline(events, timelineId, throughSequence);
}

function materializeTimeline(
	events: readonly DurableEvent[],
	timelineId: string | undefined,
	throughSequence = Number.MAX_SAFE_INTEGER,
	visited = new Set<string>(),
): DurableEvent[] {
	const branchKey = timelineId ?? "__root__";
	if (visited.has(branchKey)) throw new Error("Session timeline contains a restore cycle");
	visited.add(branchKey);
	try {
		const branch = events.filter(
			(event) => event.meta.sequence <= throughSequence && event.meta.timelineId === timelineId,
		);
		// A restore record is appended on the source branch and names its fresh
		// child in data.timelineId. Find that origin globally rather than looking
		// for it among the child's events.
		const restore = [...events]
			.reverse()
			.find(
				(event): event is DurableEvent<"session.restored"> =>
					event.type === "session.restored" &&
					event.data.timelineId === timelineId &&
					event.meta.sequence <= throughSequence,
			);
		if (!restore) return branch.filter((event) => event.type !== "session.restored");

		const base = materializeTimeline(events, restore.data.sourceTimelineId, restore.data.targetSequence, visited);
		// A restore changes the active branch immediately, so a well-formed journal
		// cannot have ordinary events after it in the old branch. Keeping this
		// guard makes malformed journals deterministic instead of replaying them.
		const tail = branch.filter(
			(event) => event.meta.sequence > restore.meta.sequence && event.type !== "session.restored",
		);
		return [...base, ...tail];
	} finally {
		visited.delete(branchKey);
	}
}
