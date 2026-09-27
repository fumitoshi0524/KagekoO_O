export interface SessionSummary {
	readonly sessionId: string;
	readonly cwd: string;
	readonly title: string | null;
	readonly archived: boolean;
	/** Unix milliseconds of the latest durable session mutation. */
	readonly updatedAt: number;
}
export interface SessionSnapshot extends SessionSummary {
	readonly status: string;
	readonly queuedPrompts: number;
	readonly provider?: string;
	readonly modelName?: string;
	readonly model?: {
		readonly provider: string;
		readonly modelName: string;
		readonly contextLength?: number;
		readonly capabilities?: readonly string[];
		readonly maxContextSize?: number;
		readonly maxOutputTokens?: number;
		readonly reasoningConfig?: Readonly<Record<string, unknown>>;
		readonly authMode?: "api" | "oauth";
		readonly provenance?: {
			readonly contextLength: "authoritative" | "catalog" | "configured" | "estimated" | "unknown";
			readonly capabilities: "authoritative" | "catalog" | "configured" | "estimated" | "unknown";
			readonly maxContextSize: "authoritative" | "catalog" | "configured" | "estimated" | "unknown";
			readonly maxOutputTokens: "authoritative" | "catalog" | "configured" | "estimated" | "unknown";
		};
		readonly metadataSource?: {
			readonly kind: "provider" | "catalog";
			readonly providerId: string;
			readonly endpoint?: string;
			readonly authMode?: "api" | "oauth";
			readonly source?: "provider-live" | "public-catalog" | "local-cache" | "static-fallback";
			readonly authoritative?: boolean;
		};
	};
	readonly contextUsed?: number;
	readonly contextLength?: number;
	readonly contextLimit?: number;
	readonly contextRemaining?: number;
	readonly contextRatio?: number;
	readonly contextSource?: string;
	readonly contextUsedSource?: "authoritative" | "catalog" | "configured" | "estimated" | "unknown";
	readonly contextLimitSource?: "authoritative" | "catalog" | "configured" | "estimated" | "unknown";
	readonly authMode?: "api" | "oauth";
}

export type SessionTimelineEntry = ProtocolSessionTimelineEntry;
export type SessionRestoreResult = ProtocolSessionRestoreResult;

/** Stable SDK request contract; it intentionally does not expose storage types. */
export interface CreateSessionInput {
	readonly sessionId?: string;
	readonly cwd: string;
	readonly title?: string | null;
}

export interface SessionListQuery {
	readonly includeArchived?: boolean;
	readonly cwd?: string;
	readonly search?: string;
}
import type {
	SessionRestoreResult as ProtocolSessionRestoreResult,
	SessionTimelineEntry as ProtocolSessionTimelineEntry,
} from "@kageko/protocol";
