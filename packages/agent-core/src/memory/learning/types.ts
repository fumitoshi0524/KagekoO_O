import type { LearningEvent } from "./event.js";
import type { DurableEvent } from "@kageko/protocol";

export type TriageAction = "drop" | "learn" | "pending";

export type TriageTarget =
	"knowledge" | "profile" | "skill" | "graph" | "mcp" | "plugin" | "error_pattern" | "capability_gap";

export interface TriageDecision {
	action: TriageAction;
	target?: TriageTarget | string;
	reason?: string;
}

/** A learner consumes triaged events and optionally approves pending outputs. */
export interface Learner {
	handle(event: LearningEvent, decision: TriageDecision): unknown | Promise<unknown>;
	approve?(output: unknown): unknown | Promise<unknown>;
	/** Called when a pending output is rejected; release any suppression state. */
	reject?(output: unknown): void;
	flush?(): void | Promise<void>;
}

export interface PendingEntry {
	event: LearningEvent;
	decision: TriageDecision;
	output?: unknown;
}

export interface ResolvePendingResult {
	resolved: boolean;
	reason?: string;
	action?: "approve" | "reject";
	[key: string]: unknown;
}

/** Store of session events used by skill/capability synthesis. */
export interface JournalEventStore {
	load(): Promise<DurableEvent[]>;
}
