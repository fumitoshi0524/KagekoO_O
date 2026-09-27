import { isDurableEvent, type DurableEvent, type RuntimeEvent } from "@kageko/protocol";

export type ActivityKind = "turn" | "process" | "subagent" | "cron";
export type ActivityStatus = "queued" | "running" | "completed" | "failed" | "cancelled" | "lost";

export interface ActivityProjection {
	readonly activityId: string;
	readonly sessionId: string;
	readonly parentActivityId?: string;
	readonly kind: ActivityKind;
	readonly status: ActivityStatus;
	readonly title: string;
	readonly startedAt: number;
	readonly endedAt?: number;
	readonly taskId?: string;
	readonly subagentId?: string;
	readonly actorId?: string;
	readonly parentToolCallId?: string;
}

/** Deterministically rebuilds the client activity tree from durable history. */
export function projectActivities(events: readonly DurableEvent[]): readonly ActivityProjection[] {
	const activities = new Map<string, ActivityProjection>();
	for (const event of events) applyEvent(activities, event);
	return [...activities.values()].sort((a, b) => b.startedAt - a.startedAt);
}

export function projectLiveActivity(
	previous: readonly ActivityProjection[],
	event: RuntimeEvent,
): readonly ActivityProjection[] {
	if (!isDurableEvent(event)) return previous;
	const values = new Map(previous.map((item) => [item.activityId, item]));
	applyEvent(values, event);
	return [...values.values()].sort((a, b) => b.startedAt - a.startedAt);
}

function applyEvent(activities: Map<string, ActivityProjection>, event: DurableEvent): void {
	const activityId = event.meta.activityId ?? inferActivityId(event);
	if (!activityId) return;
	const prior = activities.get(activityId);
	const base = prior ?? create(event, activityId);
	if (!base) return;
	let next = base;
	if (event.type === "process.started") next = { ...base, status: "running", startedAt: event.data.task.startedAt };
	else if (event.type === "turn.end") next = { ...base, status: "completed", endedAt: event.meta.occurredAt };
	else if (event.type === "turn.interrupted") next = { ...base, status: "cancelled", endedAt: event.meta.occurredAt };
	else if (event.type === "process.terminated") {
		const status =
			event.data.task.status === "completed"
				? "completed"
				: event.data.task.status === "lost"
					? "lost"
					: event.data.task.status === "killed"
						? "cancelled"
						: "failed";
		next = { ...base, status, endedAt: event.data.task.endedAt ?? event.meta.occurredAt };
	} else if (event.type === "subagent.completed")
		next = { ...base, status: "completed", endedAt: event.meta.occurredAt };
	else if (event.type === "subagent.failed") next = { ...base, status: "failed", endedAt: event.meta.occurredAt };
	activities.set(activityId, next);
}

function create(event: DurableEvent, activityId: string): ActivityProjection | undefined {
	const common = {
		activityId,
		sessionId: event.meta.sessionId,
		...(event.meta.parentActivityId ? { parentActivityId: event.meta.parentActivityId } : {}),
		...(event.meta.parentToolCallId ? { parentToolCallId: event.meta.parentToolCallId } : {}),
		...(event.meta.actorId ? { actorId: event.meta.actorId } : {}),
		status: (event.type === "process.requested" ? "queued" : "running") as ActivityStatus,
		startedAt: event.meta.occurredAt,
	};
	if (event.type === "turn.started") return { ...common, kind: "turn", title: "Agent turn" };
	if (event.type === "process.requested" || event.type === "process.started")
		return {
			...common,
			kind: "process",
			title: event.data.task.background ? "Background shell process" : "Shell process",
			taskId: event.data.task.taskId,
		};
	if (event.type === "subagent.started")
		return {
			...common,
			kind: "subagent",
			title: event.data.prompt,
			subagentId: event.data.subagentId ?? activityId,
		};
	return undefined;
}

function inferActivityId(event: DurableEvent): string | undefined {
	if (event.meta.turnId) return event.meta.turnId;
	if (event.type === "process.requested" || event.type === "process.started" || event.type === "process.terminated")
		return `process:${event.data.task.taskId}`;
	if (event.type === "subagent.started" || event.type === "subagent.completed" || event.type === "subagent.failed")
		return event.data.subagentId;
	return undefined;
}
