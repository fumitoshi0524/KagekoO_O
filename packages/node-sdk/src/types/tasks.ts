export type ActivityKind = "turn" | "process" | "subagent" | "cron";
export type ActivityStatus = "queued" | "running" | "completed" | "failed" | "cancelled" | "lost";
export interface TaskSummary {
	readonly taskId: string;
	readonly status: string;
}
export interface ActivitySummary {
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
}
export interface ActivityOutputChunk {
	readonly content: string;
	readonly offset: number;
	readonly nextOffset: number;
	readonly totalBytes: number;
	readonly eof: boolean;
	readonly persistedOutputTruncated: boolean;
}
export interface CapabilitySummary {
	readonly sessionId: string;
	readonly id: string;
	readonly kind: "plugin" | "skill" | "mcp";
	readonly description?: string;
	readonly source?: string;
	readonly authSupported?: boolean;
}
/** Redacted mcp.auth result: token material never crosses the SDK boundary. */
export interface McpAuthResult {
	readonly server: string;
	readonly expiresAt: number | null;
}
export interface CronSummary {
	readonly id: string;
	readonly cron: string;
	readonly humanSchedule: string;
	readonly prompt: string;
	readonly nextFireAt: string | null;
	readonly recurring: boolean;
	readonly ageDays: number;
	readonly stale: boolean;
}
