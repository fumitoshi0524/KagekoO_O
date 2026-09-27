import { randomUUID } from "node:crypto";

export const LEARNING_SOURCES: readonly [
	"tool_result",
	"user_feedback",
	"session_record",
	"external_fetch",
	"file_change",
	"plugin",
	"capability_gap",
] = Object.freeze([
	"tool_result",
	"user_feedback",
	"session_record",
	"external_fetch",
	"file_change",
	"plugin",
	"capability_gap",
] as const);

export type LearningSource = (typeof LEARNING_SOURCES)[number];

export interface LearningEventContext {
	sessionId?: string;
	turnId?: string;
	step?: number;
	toolName?: string;
	toolCallId?: string;
	[key: string]: unknown;
}

export interface LearningEvent {
	id: string;
	source: LearningSource;
	timestamp: number;
	payload: Record<string, unknown>;
	context?: LearningEventContext;
}

export interface ToolCallLike {
	name: string;
	id?: string;
	arguments?: Record<string, unknown>;
}

export function createLearningEvent(
	source: LearningSource,
	payload: Record<string, unknown>,
	context: LearningEventContext = {},
): LearningEvent {
	if (!(LEARNING_SOURCES as readonly string[]).includes(source)) {
		throw new Error(`Unknown learning source: ${source}`);
	}
	return {
		id: randomUUID(),
		source,
		timestamp: Date.now(),
		payload,
		context,
	};
}

export function createToolResultEvent(
	toolCall: ToolCallLike,
	result: unknown,
	context?: LearningEventContext,
): LearningEvent {
	return createLearningEvent(
		"tool_result",
		{
			toolName: toolCall.name,
			toolCallId: toolCall.id,
			arguments: toolCall.arguments,
			result,
		},
		context,
	);
}

export function createFileChangeEvent(
	filePath: string,
	operation: "write" | "edit" | "delete",
	context?: LearningEventContext,
): LearningEvent {
	return createLearningEvent(
		"file_change",
		{
			path: filePath,
			operation,
		},
		context,
	);
}

export function createUserFeedbackEvent(
	kind: "remember" | "deny" | "correction" | "preference",
	payload: Record<string, unknown>,
	context?: LearningEventContext,
): LearningEvent {
	return createLearningEvent(
		"user_feedback",
		{
			kind,
			...payload,
		},
		context,
	);
}

export function createSessionJournalEvent(
	kind: "goal.completed" | "goal.blocked" | "goal.paused" | "turn.end" | "session.summary",
	payload: Record<string, unknown>,
	context?: LearningEventContext,
): LearningEvent {
	return createLearningEvent(
		"session_record",
		{
			kind,
			...payload,
		},
		context,
	);
}

export function createExternalFetchEvent(
	kind: "url" | "topic" | "explore",
	payload: Record<string, unknown>,
	context?: LearningEventContext,
): LearningEvent {
	return createLearningEvent(
		"external_fetch",
		{
			kind,
			...payload,
		},
		context,
	);
}

export function createPluginEvent(
	kind: "command.run" | "command.list",
	payload: Record<string, unknown>,
	context?: LearningEventContext,
): LearningEvent {
	return createLearningEvent(
		"plugin",
		{
			kind,
			...payload,
		},
		context,
	);
}

export interface RequiredCapabilityContract {
	name: string;
	inputSchema: Record<string, unknown>;
}

export interface CapabilityGapPayload {
	description: string;
	context?: string;
	proposedKind?: "tool" | "mcp";
	/**
	 * Structured public tool contracts supplied through the tool-call channel.
	 * When present and non-empty, these take precedence over the free-text
	 * `Required public tool contracts:` marker parsed from the session journal.
	 */
	requiredContracts?: readonly RequiredCapabilityContract[];
	/**
	 * Evidence gathered by the agent before it asks the learner to persist a
	 * capability.  This is deliberately about future user tasks, rather than
	 * the current implementation: a correct one-shot helper is not a durable
	 * product capability.
	 */
	evidence?: CapabilityGapEvidence;
}

export interface CapabilityGapEvidence {
	/** The capability boundary: a reusable workflow, a local operation, or an external service. */
	scope: "workflow" | "local_operation" | "external_service";
	/** At least two distinct future tasks that the same capability will improve. */
	futureTasks: string[];
	/** Existing tools, skills, MCP servers, or manual approaches considered first. */
	alternativesChecked: string[];
}

export function createCapabilityGapEvent(payload: CapabilityGapPayload, context?: LearningEventContext): LearningEvent {
	return createLearningEvent(
		"capability_gap",
		{
			description: payload.description,
			context: payload.context,
			proposedKind: payload.proposedKind,
			requiredContracts: payload.requiredContracts,
			evidence: payload.evidence,
		},
		context,
	);
}
