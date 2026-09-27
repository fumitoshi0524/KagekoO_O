import { describe, expect, it } from "vitest";
import { trimEventsForSynthesis } from "./event-trim.js";
import type { SessionEvent } from "../../types.js";

// Reference copy of the pre-refactor skill.ts working-tree logic (capEvents +
// isSynthesisEvidence + computeBytes + compactEvidence, as it existed in the
// working tree before the Task 3 extraction — not the git HEAD version). The
// extracted helper must produce identical output on the same fixture.
function legacyCapEvents(events: SessionEvent[], maxEvents: number, maxBytes: number, minEvents: number): SessionEvent[] {
	const selected = events.filter(legacyIsSynthesisEvidence).slice(-maxEvents);
	while (selected.length > minEvents && legacyComputeBytes(selected) > maxBytes) {
		selected.shift();
	}
	return selected;
}

function legacyComputeBytes(events: SessionEvent[]): number {
	try {
		return Buffer.byteLength(events.map(legacyCompactEvidence).join("\n"), "utf-8");
	} catch {
		return Infinity;
	}
}

function legacyIsSynthesisEvidence(event: SessionEvent): boolean {
	if (event.type === "user.prompt") return event.data.origin === undefined || event.data.origin === "user";
	return ["assistant.text", "tool.call", "tool.result", "turn.end"].includes(event.type);
}

function legacyCompactEvidence(event: SessionEvent): string {
	if (event.type === "user.prompt") return `user:${event.data.content}`;
	if (event.type === "assistant.text") return `assistant:${event.data.content}`;
	if (event.type === "tool.call") return `call:${event.data.call.name}:${JSON.stringify(event.data.call.arguments)}`;
	if (event.type === "tool.result") return `result:${String(event.data.result.output ?? "").slice(0, 200)}`;
	return event.type;
}

function fixture(): SessionEvent[] {
	const events: SessionEvent[] = [];
	for (let task = 1; task <= 4; task += 1) {
		events.push({ type: "session.start", data: { task } } as unknown as SessionEvent);
		events.push({ type: "user.prompt", data: { content: `task-${task}` } } as unknown as SessionEvent);
		events.push({ type: "user.prompt", data: { content: "system-originated", origin: "system" } } as unknown as SessionEvent);
		for (let noise = 0; noise < 30; noise += 1) {
			events.push({ type: "usage.updated", data: { promptTokens: noise } } as unknown as SessionEvent);
		}
		events.push({ type: "assistant.text", data: { content: `answer-${task}` } } as unknown as SessionEvent);
		events.push({
			type: "tool.call",
			data: { call: { id: `call-${task}`, name: "fixture_tool", arguments: { task } } },
		} as unknown as SessionEvent);
		events.push({ type: "tool.result", data: { result: { output: `ok-${task}` } } } as unknown as SessionEvent);
		events.push({ type: "turn.end", data: { turnId: `turn-${task}` } } as unknown as SessionEvent);
	}
	return events;
}

describe("trimEventsForSynthesis", () => {
	it("matches the legacy SkillLearner capEvents output on a mixed journal", () => {
		const events = fixture();
		const expected = legacyCapEvents(events, 50, 16 * 1024, 3);
		expect(trimEventsForSynthesis(events, { minEvents: 3 })).toEqual(expected);
	});

	it("drops runtime noise and non-user prompts, keeping causal evidence", () => {
		const trimmed = trimEventsForSynthesis(fixture());
		expect(trimmed.some((event) => event.type === "usage.updated")).toBe(false);
		expect(trimmed.some((event) => (event.type as string) === "session.start")).toBe(false);
		expect(trimmed.filter((event) => event.type === "user.prompt")).toHaveLength(4);
		expect(trimmed.filter((event) => event.type === "turn.end")).toHaveLength(4);
	});

	it("caps at 50 evidence events, keeping the most recent", () => {
		const events: SessionEvent[] = Array.from({ length: 80 }, (_, index) => ({
			type: "turn.end",
			data: { turnId: `turn-${index}` },
		})) as unknown as SessionEvent[];
		const trimmed = trimEventsForSynthesis(events);
		expect(trimmed).toHaveLength(50);
		const turnIds = trimmed.map((event) => (event.data as Record<string, unknown>)["turnId"]);
		expect(turnIds[turnIds.length - 1]).toBe("turn-79");
		expect(turnIds[0]).toBe("turn-30");
	});

	it("drops oldest events past the byte cap but never below minEvents", () => {
		const big = "x".repeat(8 * 1024);
		const events: SessionEvent[] = Array.from({ length: 6 }, (_, index) => ({
			type: "assistant.text",
			data: { content: `${index}-${big}` },
		})) as unknown as SessionEvent[];
		const trimmed = trimEventsForSynthesis(events, { minEvents: 2 });
		expect(trimmed.length).toBeLessThan(6);
		expect(trimmed.length).toBeGreaterThanOrEqual(2);
		expect(trimmed).toEqual(legacyCapEvents(events, 50, 16 * 1024, 2));
	});

	it("defaults to the SkillLearner caps with a minimum of one event", () => {
		const events = fixture();
		expect(trimEventsForSynthesis(events)).toEqual(legacyCapEvents(events, 50, 16 * 1024, 1));
	});
});
