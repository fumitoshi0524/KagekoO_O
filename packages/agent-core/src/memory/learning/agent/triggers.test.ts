import { describe, expect, it } from "vitest";
import { LearningTriggers } from "./triggers.js";
import type { LearningEvent } from "../event.js";
import type { SessionEvent } from "../../types.js";

function turnEnd(turnId: string): SessionEvent {
	return { type: "turn.end", data: { turnId } } as unknown as SessionEvent;
}

function toolCall(index: number): SessionEvent {
	return {
		type: "tool.call",
		data: { call: { id: `call-${index}`, name: "fixture_tool", arguments: { index } } },
	} as unknown as SessionEvent;
}

function journal(...events: SessionEvent[]): { load: () => Promise<SessionEvent[]> } {
	return { load: async () => events };
}

const turnEndEvent = (id = "evt-1"): LearningEvent =>
	({ id, source: "session_record", timestamp: 1, payload: { kind: "turn.end" } }) as unknown as LearningEvent;

/** Journal with n completed turns and a tool call per turn. */
function workingJournal(turns: number) {
	const events: SessionEvent[] = [];
	for (let index = 1; index <= turns; index += 1) {
		events.push(toolCall(index), turnEnd(`turn-${index}`));
	}
	return journal(...events);
}

describe("LearningTriggers", () => {
	it("starts cooled-in so the first eligible event triggers, then enforces the event cooldown", async () => {
		const triggers = new LearningTriggers({ recordStore: workingJournal(3) });
		expect(await triggers.shouldTriggerSkillReview(turnEndEvent())).toBe(true);
		// Five gated events after an attempt, mirroring SkillLearner's cooldown.
		for (let index = 0; index < 5; index += 1) {
			expect(await triggers.shouldTriggerSkillReview(turnEndEvent(`evt-next-${index}`))).toBe(false);
		}
		expect(await triggers.shouldTriggerSkillReview(turnEndEvent("evt-sixth"))).toBe(true);
	});

	it("requires the minimum journal history", async () => {
		const triggers = new LearningTriggers({ recordStore: journal(turnEnd("turn-1")) });
		expect(await triggers.shouldTriggerSkillReview(turnEndEvent())).toBe(false);
	});

	it("requires enough completed turns and at least one tool call for session records", async () => {
		const fewTurns = new LearningTriggers({ recordStore: workingJournal(2) });
		expect(await fewTurns.shouldTriggerSkillReview(turnEndEvent())).toBe(false);

		const noToolCalls = new LearningTriggers({
			recordStore: journal(turnEnd("turn-1"), turnEnd("turn-2"), turnEnd("turn-3")),
		});
		expect(await noToolCalls.shouldTriggerSkillReview(turnEndEvent())).toBe(false);

		const eligible = new LearningTriggers({ recordStore: workingJournal(3) });
		expect(await eligible.shouldTriggerSkillReview(turnEndEvent())).toBe(true);
	});

	it("preserves the durable cooldown watermark from auto skills (learnedThroughTurns)", async () => {
		const skillRegistry = {
			list: () => [
				{
					name: "existing-workflow",
					content: "A previously learned procedure.",
					source: "auto",
					metadata: { learnedThroughTurns: 3 },
				},
			],
			registerSkill: async () => undefined,
		};
		// 5 completed turns with the watermark at 3: 5 - 3 <= 5 is still cooled.
		const cooled = new LearningTriggers({ recordStore: workingJournal(5), skillRegistry: skillRegistry as never });
		expect(await cooled.shouldTriggerSkillReview(turnEndEvent())).toBe(false);
		// 9 completed turns: 9 - 3 > 5 lets a new attempt through.
		const warmed = new LearningTriggers({ recordStore: workingJournal(9), skillRegistry: skillRegistry as never });
		expect(await warmed.shouldTriggerSkillReview(turnEndEvent())).toBe(true);
	});

	it("ignores non-auto skills for the durable cooldown", async () => {
		const skillRegistry = {
			list: () => [
				{
					name: "project-workflow",
					content: "A project-authored procedure.",
					source: "project",
					metadata: { learnedThroughTurns: 100 },
				},
			],
			registerSkill: async () => undefined,
		};
		const triggers = new LearningTriggers({ recordStore: workingJournal(3), skillRegistry: skillRegistry as never });
		expect(await triggers.shouldTriggerSkillReview(turnEndEvent())).toBe(true);
	});

	it("skips the value checks for non-session-record events", async () => {
		const triggers = new LearningTriggers({
			recordStore: journal(turnEnd("turn-1"), turnEnd("turn-2"), turnEnd("turn-3")),
		});
		const event = {
			id: "evt-x",
			source: "capability_gap",
			timestamp: 1,
			payload: { description: "irrelevant here" },
		} as unknown as LearningEvent;
		expect(await triggers.shouldTriggerSkillReview(event)).toBe(true);
	});
});
