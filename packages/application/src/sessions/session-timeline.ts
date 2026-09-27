import type { DurableEvent, SessionTimelineEntry } from "@kageko/protocol";

/** Keeps UI wording out of the journal while making every recoverable state searchable. */
export function projectSessionTimeline(events: readonly DurableEvent[]): readonly SessionTimelineEntry[] {
	return events
		.filter((event) => event.type !== "session.restored")
		.map((event) => ({
			sequence: event.meta.sequence,
			eventId: event.meta.eventId,
			occurredAt: event.meta.occurredAt,
			...(event.meta.timelineId ? { timelineId: event.meta.timelineId } : {}),
			...(event.meta.actorId ? { actorId: event.meta.actorId } : {}),
			...(event.meta.activityId ? { activityId: event.meta.activityId } : {}),
			kind: timelineKind(event),
			label: timelineLabel(event),
			hasExternalEffects: hasExternalEffects(event),
		}))
		.sort((left, right) => right.sequence - left.sequence);
}

export function timelineHasExternalEffects(
	events: readonly DurableEvent[],
	timelineId: string | undefined,
	afterSequence: number,
): number {
	return events.filter(
		(event) => event.meta.timelineId === timelineId && event.meta.sequence > afterSequence && hasExternalEffects(event),
	).length;
}

function timelineKind(event: DurableEvent): SessionTimelineEntry["kind"] {
	if (event.type === "user.prompt") return "user";
	if (event.type === "assistant.text" || event.type === "assistant.thinking") return "assistant";
	if (event.type === "tool.call" || event.type === "tool.result") return "tool";
	if (event.type.startsWith("subagent.")) return "subagent";
	if (event.type.startsWith("process.")) return "process";
	if (event.type.startsWith("turn.") || event.type.startsWith("step.") || event.type === "usage.updated") return "turn";
	if (event.type.startsWith("goal.")) return "goal";
	return "session";
}

function timelineLabel(event: DurableEvent): string {
	switch (event.type) {
		case "user.prompt":
			return `User: ${summarize(event.data.content)}`;
		case "assistant.text":
			return `Coordinator: ${summarize(event.data.content)}`;
		case "assistant.thinking":
			return `Coordinator reasoning: ${summarize(event.data.content)}`;
		case "tool.call":
			return `Tool started: ${event.data.call.name}`;
		case "tool.result":
			return `Tool finished: ${event.data.call.name}`;
		case "subagent.started":
			return `Subagent started: ${summarize(event.data.prompt)}`;
		case "subagent.completed":
			return "Subagent completed";
		case "subagent.failed":
			return `Subagent failed: ${summarize(event.data.error.message)}`;
		case "process.requested":
			return "Shell process queued";
		case "process.started":
			return "Shell process started";
		case "process.terminated":
			return `Shell process ${event.data.task.status}`;
		case "turn.started":
			return "Coordinator turn started";
		case "turn.end":
			return `Coordinator turn completed: ${event.data.result.stopReason}`;
		case "turn.interrupted":
			return `Coordinator turn interrupted: ${event.data.stopReason}`;
		case "session.forked":
			return "Session forked";
		default:
			return event.type;
	}
}

function hasExternalEffects(event: DurableEvent): boolean {
	return event.type === "tool.call" || event.type === "tool.result" || event.type.startsWith("process.");
}

function summarize(value: string): string {
	const singleLine = value.replace(/\s+/g, " ").trim();
	return singleLine.length <= 96 ? singleLine : `${singleLine.slice(0, 93)}...`;
}
