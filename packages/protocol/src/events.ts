/**
 * Version of the durable event envelope written to a session journal.
 *
 * This is intentionally independent from the journal file format version:
 * the file container and the events inside it can evolve separately.
 */
export const EVENT_SCHEMA_VERSION = 1 as const;

export type EventSchemaVersion = typeof EVENT_SCHEMA_VERSION;

export interface EventContext {
	readonly turnId?: string;
	readonly stepId?: string;
	readonly toolCallId?: string;
	readonly causationId?: string;
	readonly correlationId?: string;
	/** Stable UI/activity identifier. Root turns use their turn id. */
	readonly activityId?: string;
	/** Optional parent activity for subagents, processes, and scheduled work. */
	readonly parentActivityId?: string;
	/** Tool call that created the activity, when it was delegated from a tool. */
	readonly parentToolCallId?: string;
	/** Actor producing the event, for example a subagent id. */
	readonly actorId?: string;
	/**
	 * Logical session-history branch. Absent events belong to the original
	 * timeline; restores create a new id without rewriting the append-only
	 * journal.
	 */
	readonly timelineId?: string;
}

/** Metadata assigned only after an event has been durably appended. */
export interface DurableEventMeta extends EventContext {
	readonly schemaVersion: EventSchemaVersion;
	readonly eventId: string;
	readonly sequence: number;
	readonly sessionId: string;
	readonly occurredAt: number;
	readonly recordedAt: number;
}

/** Metadata for an ephemeral event that is never written to the journal. */
export interface LiveEventMeta extends EventContext {
	readonly schemaVersion: EventSchemaVersion;
	readonly eventId: string;
	readonly sessionId: string;
	readonly occurredAt: number;
}

/**
 * Metadata supplied by a producer before the journal assigns identity,
 * ordering, and persistence time.
 */
export interface DurableEventContext extends EventContext {
	readonly occurredAt?: number;
}

export interface PromptPart {
	readonly type: string;
	readonly text?: string;
	readonly image_url?: {
		readonly url: string;
	};
	readonly mimeType?: string;
	readonly path?: string;
	readonly data?: string;
}

export interface ToolCallData {
	readonly id: string;
	readonly name: string;
	readonly arguments: Readonly<Record<string, unknown>>;
}

export interface ToolResultData {
	readonly output?: unknown;
	readonly isError?: boolean;
	readonly stopTurn?: boolean;
	readonly skipped?: boolean;
	readonly truncated?: boolean;
}

export interface UsageData {
	readonly promptTokens?: number;
	readonly completionTokens?: number;
	readonly totalTokens?: number;
}

export interface GoalBudgetData {
	readonly maxTurns?: number;
	readonly maxTokens?: number;
	readonly maxWallClockMs?: number;
}

export interface GoalSnapshotData {
	readonly id: string;
	readonly description: string;
	readonly status: string;
	readonly budget?: GoalBudgetData | null;
	readonly turnsUsed?: number;
	readonly createdAt?: number;
}

export type ProcessTaskStatusData = "running" | "completed" | "failed" | "killed" | "timed_out" | "lost";

export interface ProcessTaskData {
	readonly taskId: string;
	readonly pid?: number;
	readonly background: boolean;
	readonly status: ProcessTaskStatusData;
	readonly startedAt: number;
	readonly endedAt?: number;
	readonly exitCode?: number | null;
	readonly stopReason?: string;
	/** SHA-256 correlation value; the possibly sensitive command text is not journaled here. */
	readonly commandDigest: string;
}

export interface DurableEventDataMap {
	"user.prompt": {
		readonly content: string;
		readonly parts?: readonly PromptPart[];
		readonly origin?: string;
	};
	"turn.started": Record<never, never>;
	"step.begin": {
		readonly step: number;
	};
	"step.end": {
		readonly step: number;
		readonly stopReason: string;
		readonly usage?: UsageData;
	};
	"assistant.text": {
		readonly content: string;
	};
	"assistant.thinking": {
		readonly content: string;
	};
	"usage.updated": UsageData;
	"tool.call": {
		readonly call: ToolCallData;
	};
	"tool.result": {
		readonly call: ToolCallData;
		readonly result: ToolResultData;
	};
	"turn.interrupted": {
		readonly stopReason: string;
	};
	"turn.checkpointed": {
		readonly reason: "budget_exhausted" | "stalled" | "slice_exhausted";
		readonly elapsedMs: number;
		readonly tokensUsed: number;
		/** Present when the runtime has an explicit provider price card. */
		readonly costUsd?: number;
	};
	"turn.end": {
		readonly result: {
			readonly content: string;
			readonly stopReason: string;
			readonly tokensUsed?: number;
			readonly costUsd?: number;
		};
	};
	"session.forked": {
		readonly sourceSessionId: string;
		readonly sourceEventCount: number;
		readonly sourceLastEventId?: string;
	};
	"session.restored": {
		/** Durable event sequence selected by the human from the timeline. */
		readonly targetSequence: number;
		/** The source branch containing targetSequence; omitted for the original branch. */
		readonly sourceTimelineId?: string;
		/** Fresh branch id receiving all later durable events. */
		readonly timelineId: string;
	};
	"process.started": {
		readonly task: ProcessTaskData;
	};
	"process.requested": {
		readonly task: ProcessTaskData;
	};
	"process.terminated": {
		readonly task: ProcessTaskData;
	};
	"task.cron.updated": {
		readonly jobs: readonly {
			readonly id: string;
			readonly cron: string;
			readonly prompt: string;
			readonly recurring: boolean;
			readonly createdAt: number;
			readonly stale: boolean;
		}[];
	};
	"goal.created": {
		readonly goal: GoalSnapshotData;
	};
	"goal.updated": {
		readonly goal: GoalSnapshotData;
	};
	"goal.completed": {
		readonly goalId: string;
		readonly reason?: string;
	};
	"goal.blocked": {
		readonly goalId: string;
		readonly reason?: string;
	};
	"goal.paused": {
		readonly goalId: string;
		readonly reason?: string;
	};
	"subagent.started": {
		readonly subagentId?: string;
		readonly parentToolCallId?: string;
		readonly prompt: string;
		readonly profile?: unknown;
	};
	"subagent.completed": {
		readonly subagentId?: string;
		readonly parentToolCallId?: string;
		readonly prompt: string;
		readonly profile?: unknown;
		readonly result: unknown;
	};
	"subagent.failed": {
		readonly subagentId?: string;
		readonly parentToolCallId?: string;
		readonly prompt: string;
		readonly profile?: unknown;
		readonly error: {
			readonly name?: string;
			readonly message: string;
		};
	};
}

export interface LiveEventDataMap {
	"session.status.changed": {
		readonly status: "ready" | "running" | "awaiting_approval" | "awaiting_question" | "closing" | "closed" | "failed";
		readonly previous?: string;
	};
	"text.delta": {
		readonly delta: string;
	};
	"thinking.delta": {
		readonly delta: string;
	};
	"tool.call.delta": {
		readonly id: string;
		readonly name: string;
		readonly argumentsPartial: string;
	};
	"tool.progress": {
		readonly call: ToolCallData;
		readonly progress: unknown;
	};
	"step.retrying": {
		readonly step: number;
		readonly attempt: number;
		readonly maxAttempts: number;
		readonly delayMs: number;
		readonly errorName?: string;
		readonly errorMessage: string;
		readonly reason?: string;
	};
	"tool.retrying": {
		readonly toolName: string;
		readonly attempt: number;
		readonly maxAttempts: number;
		readonly delayMs: number;
		readonly reason: string;
	};
	"turn.failed": {
		readonly turnId?: string;
		readonly message: string;
	};
}

export type DurableEventType = keyof DurableEventDataMap;
export type LiveEventType = keyof LiveEventDataMap;

export type DurableEvent<K extends DurableEventType = DurableEventType> = K extends DurableEventType
	? {
			readonly type: K;
			readonly meta: DurableEventMeta;
			readonly data: Readonly<DurableEventDataMap[K]>;
		}
	: never;

export type DurableEventInput<K extends DurableEventType = DurableEventType> = K extends DurableEventType
	? {
			readonly type: K;
			readonly meta?: DurableEventContext;
			readonly data: Readonly<DurableEventDataMap[K]>;
		}
	: never;

export type LiveEvent<K extends LiveEventType = LiveEventType> = K extends LiveEventType
	? {
			readonly type: K;
			readonly meta: LiveEventMeta;
			readonly data: Readonly<LiveEventDataMap[K]>;
		}
	: never;

export type RuntimeEvent = DurableEvent | LiveEvent;

const DURABLE_EVENT_TYPE_LIST = [
	"user.prompt",
	"turn.started",
	"step.begin",
	"step.end",
	"assistant.text",
	"assistant.thinking",
	"usage.updated",
	"tool.call",
	"tool.result",
	"turn.interrupted",
	"turn.checkpointed",
	"turn.end",
	"session.forked",
	"session.restored",
	"process.started",
	"process.requested",
	"process.terminated",
	"task.cron.updated",
	"goal.created",
	"goal.updated",
	"goal.completed",
	"goal.blocked",
	"goal.paused",
	"subagent.started",
	"subagent.completed",
	"subagent.failed",
] as const satisfies readonly DurableEventType[];

const LIVE_EVENT_TYPE_LIST = [
	"session.status.changed",
	"text.delta",
	"thinking.delta",
	"tool.call.delta",
	"tool.progress",
	"step.retrying",
	"tool.retrying",
	"turn.failed",
] as const satisfies readonly LiveEventType[];

// Compile-time exhaustiveness guards: adding a key to one of the data maps
// without listing it above fails typechecking here, so the runtime sets can
// never silently drift from the protocol contract again.
const _durableEventTypesExhaustive: Record<
	Exclude<DurableEventType, (typeof DURABLE_EVENT_TYPE_LIST)[number]>,
	never
> = {};
const _liveEventTypesExhaustive: Record<Exclude<LiveEventType, (typeof LIVE_EVENT_TYPE_LIST)[number]>, never> = {};

const DURABLE_EVENT_TYPES: ReadonlySet<string> = new Set<string>(DURABLE_EVENT_TYPE_LIST);

const LIVE_EVENT_TYPES: ReadonlySet<string> = new Set<string>(LIVE_EVENT_TYPE_LIST);

const SESSION_STATUS_VALUES: ReadonlySet<string> = new Set([
	"ready",
	"running",
	"awaiting_approval",
	"awaiting_question",
	"closing",
	"closed",
	"failed",
]);

export function isDurableEventType(value: unknown): value is DurableEventType {
	return typeof value === "string" && DURABLE_EVENT_TYPES.has(value);
}

export function isLiveEventType(value: unknown): value is LiveEventType {
	return typeof value === "string" && LIVE_EVENT_TYPES.has(value);
}

export function isDurableEvent(value: unknown): value is DurableEvent {
	if (!isObject(value) || !isDurableEventType(value["type"]) || !isObject(value["meta"]) || !isObject(value["data"])) {
		return false;
	}
	const meta = value["meta"];
	return (
		meta["schemaVersion"] === EVENT_SCHEMA_VERSION &&
		isNonEmptyString(meta["eventId"]) &&
		Number.isSafeInteger(meta["sequence"]) &&
		(meta["sequence"] as number) > 0 &&
		isNonEmptyString(meta["sessionId"]) &&
		isFiniteTimestamp(meta["occurredAt"]) &&
		isFiniteTimestamp(meta["recordedAt"]) &&
		isOptionalString(meta["turnId"]) &&
		isOptionalString(meta["stepId"]) &&
		isOptionalString(meta["toolCallId"]) &&
		isOptionalString(meta["causationId"]) &&
		isOptionalString(meta["correlationId"]) &&
		isOptionalString(meta["activityId"]) &&
		isOptionalString(meta["parentActivityId"]) &&
		isOptionalString(meta["parentToolCallId"]) &&
		isOptionalString(meta["actorId"]) &&
		isDurableEventData(value["type"], value["data"])
	);
}

export function isLiveEvent(value: unknown): value is LiveEvent {
	if (!isObject(value) || !isLiveEventType(value["type"]) || !isObject(value["meta"]) || !isObject(value["data"])) {
		return false;
	}
	const meta = value["meta"];
	return (
		meta["schemaVersion"] === EVENT_SCHEMA_VERSION &&
		isNonEmptyString(meta["eventId"]) &&
		isNonEmptyString(meta["sessionId"]) &&
		isFiniteTimestamp(meta["occurredAt"]) &&
		isOptionalString(meta["turnId"]) &&
		isOptionalString(meta["stepId"]) &&
		isOptionalString(meta["toolCallId"]) &&
		isOptionalString(meta["causationId"]) &&
		isOptionalString(meta["correlationId"]) &&
		isOptionalString(meta["activityId"]) &&
		isOptionalString(meta["parentActivityId"]) &&
		isOptionalString(meta["parentToolCallId"]) &&
		isOptionalString(meta["actorId"]) &&
		isOptionalString(meta["timelineId"]) &&
		isLiveEventData(value["type"], value["data"])
	);
}

function isDurableEventData(type: DurableEventType, data: Record<string, unknown>): boolean {
	switch (type) {
		case "user.prompt":
			return (
				typeof data["content"] === "string" &&
				isOptionalString(data["origin"]) &&
				(data["parts"] === undefined ||
					(Array.isArray(data["parts"]) &&
						data["parts"].every((part) => isObject(part) && typeof part["type"] === "string")))
			);
		case "turn.started":
			return Object.keys(data).length === 0;
		case "step.begin":
			return isPositiveInteger(data["step"]);
		case "step.end":
			return (
				isPositiveInteger(data["step"]) &&
				typeof data["stopReason"] === "string" &&
				(data["usage"] === undefined || isUsage(data["usage"]))
			);
		case "assistant.text":
		case "assistant.thinking":
			return typeof data["content"] === "string";
		case "usage.updated":
			return isUsage(data);
		case "tool.call":
			return isToolCall(data["call"]);
		case "tool.result":
			return isToolCall(data["call"]) && isToolResult(data["result"]);
		case "turn.interrupted":
			return typeof data["stopReason"] === "string";
		case "turn.checkpointed":
			return (
				(data["reason"] === "budget_exhausted" || data["reason"] === "stalled" || data["reason"] === "slice_exhausted") &&
				typeof data["elapsedMs"] === "number" &&
				typeof data["tokensUsed"] === "number" &&
				isOptionalNonNegativeFiniteNumber(data["costUsd"])
			);
		case "turn.end": {
			const result = data["result"];
			return (
				isObject(result) &&
				typeof result["content"] === "string" &&
				typeof result["stopReason"] === "string" &&
				isOptionalNonNegativeFiniteNumber(result["tokensUsed"]) &&
				isOptionalNonNegativeFiniteNumber(result["costUsd"])
			);
		}
		case "session.forked":
			return (
				isNonEmptyString(data["sourceSessionId"]) &&
				isNonNegativeSafeInteger(data["sourceEventCount"]) &&
				isOptionalString(data["sourceLastEventId"])
			);
		case "session.restored":
			return (
				isPositiveInteger(data["targetSequence"]) &&
				isOptionalString(data["sourceTimelineId"]) &&
				isNonEmptyString(data["timelineId"])
			);
		case "process.started":
		case "process.requested":
			return isProcessTask(data["task"], "running");
		case "process.terminated":
			return isProcessTask(data["task"], "terminal");
		case "task.cron.updated":
			return (
				Array.isArray(data["jobs"]) &&
				data["jobs"].every((job) => {
					if (!isObject(job)) return false;
					return (
						isNonEmptyString(job["id"]) &&
						typeof job["cron"] === "string" &&
						typeof job["prompt"] === "string" &&
						typeof job["recurring"] === "boolean" &&
						isNonNegativeFiniteNumber(job["createdAt"]) &&
						typeof job["stale"] === "boolean"
					);
				})
			);
		case "goal.created":
		case "goal.updated":
			return isGoalSnapshot(data["goal"]);
		case "goal.completed":
		case "goal.blocked":
		case "goal.paused":
			return isNonEmptyString(data["goalId"]) && isOptionalString(data["reason"]);
		case "subagent.started":
			return typeof data["prompt"] === "string";
		case "subagent.completed":
			return typeof data["prompt"] === "string" && Object.hasOwn(data, "result");
		case "subagent.failed": {
			const error = data["error"];
			return (
				typeof data["prompt"] === "string" &&
				isObject(error) &&
				typeof error["message"] === "string" &&
				isOptionalString(error["name"])
			);
		}
	}
}

function isLiveEventData(type: LiveEventType, data: Record<string, unknown>): boolean {
	switch (type) {
		case "session.status.changed":
			return SESSION_STATUS_VALUES.has(String(data["status"])) && isOptionalString(data["previous"]);
		case "text.delta":
		case "thinking.delta":
			return typeof data["delta"] === "string";
		case "tool.call.delta":
			return (
				typeof data["id"] === "string" &&
				typeof data["name"] === "string" &&
				typeof data["argumentsPartial"] === "string"
			);
		case "tool.progress":
			return isToolCall(data["call"]) && Object.hasOwn(data, "progress");
		case "step.retrying":
			return (
				isPositiveInteger(data["step"]) &&
				isPositiveInteger(data["attempt"]) &&
				isPositiveInteger(data["maxAttempts"]) &&
				isNonNegativeFiniteNumber(data["delayMs"]) &&
				typeof data["errorMessage"] === "string" &&
				isOptionalString(data["errorName"]) &&
				isOptionalString(data["reason"])
			);
		case "tool.retrying":
			return (
				isNonEmptyString(data["toolName"]) &&
				isPositiveInteger(data["attempt"]) &&
				isPositiveInteger(data["maxAttempts"]) &&
				isNonNegativeFiniteNumber(data["delayMs"]) &&
				typeof data["reason"] === "string"
			);
		case "turn.failed":
			return typeof data["message"] === "string" && isOptionalString(data["turnId"]);
	}
}

function isToolCall(value: unknown): boolean {
	return (
		isObject(value) && isNonEmptyString(value["id"]) && isNonEmptyString(value["name"]) && isObject(value["arguments"])
	);
}

function isToolResult(value: unknown): boolean {
	return (
		isObject(value) &&
		isOptionalBoolean(value["isError"]) &&
		isOptionalBoolean(value["stopTurn"]) &&
		isOptionalBoolean(value["skipped"]) &&
		isOptionalBoolean(value["truncated"])
	);
}

function isUsage(value: unknown): boolean {
	return (
		isObject(value) &&
		isOptionalNonNegativeFiniteNumber(value["promptTokens"]) &&
		isOptionalNonNegativeFiniteNumber(value["completionTokens"]) &&
		isOptionalNonNegativeFiniteNumber(value["totalTokens"])
	);
}

function isGoalSnapshot(value: unknown): boolean {
	return (
		isObject(value) &&
		isNonEmptyString(value["id"]) &&
		typeof value["description"] === "string" &&
		typeof value["status"] === "string" &&
		isOptionalNonNegativeFiniteNumber(value["turnsUsed"]) &&
		isOptionalNonNegativeFiniteNumber(value["createdAt"]) &&
		(value["budget"] === undefined || value["budget"] === null || isGoalBudget(value["budget"]))
	);
}

function isProcessTask(value: unknown, expected: "running" | "terminal"): boolean {
	if (!isObject(value)) return false;
	const status = value["status"];
	const terminalStatuses = new Set(["completed", "failed", "killed", "timed_out", "lost"]);
	return (
		isNonEmptyString(value["taskId"]) &&
		(value["pid"] === undefined || isPositiveInteger(value["pid"])) &&
		typeof value["background"] === "boolean" &&
		(expected === "running" ? status === "running" : terminalStatuses.has(String(status))) &&
		isFiniteTimestamp(value["startedAt"]) &&
		(value["endedAt"] === undefined || isFiniteTimestamp(value["endedAt"])) &&
		(value["exitCode"] === undefined || value["exitCode"] === null || Number.isSafeInteger(value["exitCode"])) &&
		isOptionalString(value["stopReason"]) &&
		typeof value["commandDigest"] === "string" &&
		/^[a-f0-9]{64}$/.test(value["commandDigest"])
	);
}

function isGoalBudget(value: unknown): boolean {
	return (
		isObject(value) &&
		isOptionalNonNegativeFiniteNumber(value["maxTurns"]) &&
		isOptionalNonNegativeFiniteNumber(value["maxTokens"]) &&
		isOptionalNonNegativeFiniteNumber(value["maxWallClockMs"])
	);
}

function isObject(value: unknown): value is Record<string, unknown> {
	return value !== null && typeof value === "object" && !Array.isArray(value);
}

function isNonEmptyString(value: unknown): value is string {
	return typeof value === "string" && value.length > 0;
}

function isOptionalString(value: unknown): boolean {
	return value === undefined || typeof value === "string";
}

function isOptionalBoolean(value: unknown): boolean {
	return value === undefined || typeof value === "boolean";
}

function isFiniteTimestamp(value: unknown): value is number {
	return typeof value === "number" && Number.isFinite(value) && value >= 0;
}

function isPositiveInteger(value: unknown): value is number {
	return Number.isSafeInteger(value) && (value as number) > 0;
}

function isNonNegativeSafeInteger(value: unknown): value is number {
	return Number.isSafeInteger(value) && (value as number) >= 0;
}

function isNonNegativeFiniteNumber(value: unknown): value is number {
	return typeof value === "number" && Number.isFinite(value) && value >= 0;
}

function isOptionalNonNegativeFiniteNumber(value: unknown): boolean {
	return value === undefined || isNonNegativeFiniteNumber(value);
}
