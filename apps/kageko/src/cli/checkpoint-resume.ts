export interface CheckpointSummary {
	readonly reason: "budget_exhausted" | "stalled" | "slice_exhausted";
	readonly tokensUsed?: number;
	readonly costUsd?: number;
}

export type CheckpointAction =
	| { readonly kind: "stop" }
	| { readonly kind: "resume"; readonly prompt: string }
	| { readonly kind: "escalate"; readonly message: string };

const SLICE_CONTINUATION_PROMPT =
	"Continue the active task from its durable checkpoint. Read the todo list and verified state first; do not repeat a completed or pending mutating operation.";

const STALLED_CONTINUATION_PROMPT =
	"This task was circuit-broken for lack of progress: repeated errors, repeated identical tool calls, or unchanged external state. Do not repeat the previous approach. Diagnose why it stalled, then switch to a fundamentally different strategy.";

export function resolveCheckpointAction(
	checkpoint: CheckpointSummary | undefined,
	resumeOnCheckpoint: boolean,
	sessionId: string,
): CheckpointAction {
	if (!resumeOnCheckpoint || checkpoint === undefined) return { kind: "stop" };
	if (checkpoint.reason === "slice_exhausted") {
		return { kind: "resume", prompt: SLICE_CONTINUATION_PROMPT };
	}
	if (checkpoint.reason === "stalled") {
		return { kind: "resume", prompt: STALLED_CONTINUATION_PROMPT };
	}
	const usage: string[] = [];
	if (checkpoint.tokensUsed !== undefined) usage.push(`${checkpoint.tokensUsed} tokens`);
	if (checkpoint.costUsd !== undefined) usage.push(`$${checkpoint.costUsd.toFixed(4)}`);
	const usageText = usage.length > 0 ? ` after ${usage.join(" / ")}` : "";
	return {
		kind: "escalate",
		message:
			`kageko: task stopped (budget_exhausted)${usageText}. ` +
			`The session is preserved; a human can resume it with: kageko --session ${sessionId}\n`,
	};
}
