import type { PromptPart } from "@kageko/node-sdk";

/** Semantic records are deliberately independent from terminal presentation. */
export type TranscriptKind =
	| "user"
	| "assistant"
	| "thinking"
	| "tool"
	| "tool-result"
	| "process"
	| "subagent"
	| "status"
	| "warning"
	| "error"
	| "system";
export interface TranscriptRecord {
	readonly id: string;
	readonly kind: TranscriptKind;
	text: string;
	readonly sequence?: number;
	readonly eventId?: string;
	readonly activityId?: string;
	streaming?: boolean;
	detail?: string;
	state?: "running" | "success" | "failed" | "stopped";
	/** Structured tool presentation retained across streaming and durable events. */
	tool?: {
		readonly callId: string;
		readonly name: string;
		readonly arguments?: string;
		readonly progress?: string;
		readonly output?: string;
		readonly error?: string;
		readonly presentation?: "diff" | "code" | "text" | "subagent" | "plan";
	};
	expanded?: boolean;
}
export interface ActivityRecord {
	readonly id: string;
	kind: "tool" | "process" | "subagent" | "turn";
	label: string;
	state: "running" | "success" | "failed" | "stopped";
	detail?: string;
}
export interface QueuedPrompt {
	readonly id: string;
	readonly text: string;
	readonly attachments: readonly PromptPart[];
	state: "queued" | "sending" | "failed";
	error?: string;
}
export type Overlay =
	| "none"
	| "sessions"
	| "approval"
	| "question"
	| "help"
	| "activities"
	| "details"
	| "confirm"
	| "trust"
	| "setup"
	| "shell"
	| "panel";
export type ConnectionState = "ready" | "reconnecting" | "failed";
export interface TuiState {
	readonly overlay: Overlay;
	readonly submitting: boolean;
	readonly connection: ConnectionState;
	readonly turnLive: boolean;
	readonly sessionId?: string;
	readonly transcript: readonly TranscriptRecord[];
	readonly activities: ReadonlyMap<string, ActivityRecord>;
	readonly queue: readonly QueuedPrompt[];
}
