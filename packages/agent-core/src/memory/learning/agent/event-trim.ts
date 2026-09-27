import type { SessionEvent } from "../../types.js";

export const MAX_EVENTS_FOR_SYNTHESIS: number = 50;
export const MAX_TRANSCRIPT_BYTES: number = 16 * 1024;

export interface TrimEventsForSynthesisOptions {
	maxEvents?: number;
	maxBytes?: number;
	/** Keep at least this many events even when the byte cap is exceeded. */
	minEvents?: number;
}

/**
 * Bound a session journal for synthesis: keep only compact causal evidence
 * (user prompts, assistant text, tool calls/results, turn boundaries), retain
 * the most recent `maxEvents` of them, then drop the oldest until the
 * transcript fits `maxBytes` — never going below `minEvents`.
 *
 * Runtime journals contain many lifecycle, usage, goal-continuation, and
 * streaming events that a synthesizer cannot use. Letting those consume the
 * cap made a "session learner" see little more than the final task.
 *
 * Extracted from `SkillLearner` so the resident learner agent's
 * `read_recent_events` tool presents exactly the same evidence window.
 */
export function trimEventsForSynthesis(
	events: SessionEvent[],
	{ maxEvents = MAX_EVENTS_FOR_SYNTHESIS, maxBytes = MAX_TRANSCRIPT_BYTES, minEvents = 1 }: TrimEventsForSynthesisOptions = {},
): SessionEvent[] {
	const selected = events.filter(isSynthesisEvidence).slice(-maxEvents);
	while (selected.length > minEvents && computeBytes(selected) > maxBytes) {
		selected.shift();
	}
	return selected;
}

function computeBytes(events: SessionEvent[]): number {
	try {
		return Buffer.byteLength(events.map(compactEvidence).join("\n"), "utf-8");
	} catch {
		return Infinity;
	}
}

function isSynthesisEvidence(event: SessionEvent): boolean {
	if (event.type === "user.prompt") return event.data.origin === undefined || event.data.origin === "user";
	return ["assistant.text", "tool.call", "tool.result", "turn.end"].includes(event.type);
}

function compactEvidence(event: SessionEvent): string {
	if (event.type === "user.prompt") return `user:${event.data.content}`;
	if (event.type === "assistant.text") return `assistant:${event.data.content}`;
	if (event.type === "tool.call") return `call:${event.data.call.name}:${JSON.stringify(event.data.call.arguments)}`;
	if (event.type === "tool.result") return `result:${String(event.data.result.output ?? "").slice(0, 200)}`;
	return event.type;
}
