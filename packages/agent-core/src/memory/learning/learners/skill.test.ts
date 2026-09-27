import { describe, expect, it, vi } from "vitest";
import { SkillLearner } from "./skill.js";
import type { SessionEvent } from "../../types.js";
import type { LearningEvent } from "../event.js";

describe("SkillLearner", () => {
	it("counts completed turns across the durable journal before bounding the synthesis transcript", async () => {
		const synthesize = vi.fn().mockResolvedValue({
			name: "stateful-workflow",
			description: "Reuse a verified stateful workflow safely.",
			instructions:
				"Inspect the contract, retain returned identifiers, execute dependencies in order, recover errors, and verify final postconditions.",
		});
		const events = [
			turnEnd("turn-1"),
			...Array.from({ length: 58 }, (_, index) => toolCall(index)),
			turnEnd("turn-2"),
			turnEnd("turn-3"),
		];
		const learner = new SkillLearner({
			synthesizer: { synthesize } as never,
			recordStore: { load: vi.fn().mockResolvedValue(events) },
			skillRegistry: { list: () => [], registerSkill: vi.fn() },
			autoApprove: false,
		});

		const output = await learner.handle({
			source: "session_record",
			payload: { kind: "turn.end" },
		} as unknown as LearningEvent);

		expect(output?.status).toBe("pending");
		expect(synthesize).toHaveBeenCalledOnce();
		const transcript = synthesize.mock.calls[0]?.[0] as SessionEvent[];
		expect(transcript.length).toBeLessThanOrEqual(50);
		expect(transcript.filter((event) => event.type === "turn.end")).toHaveLength(2);
	});

	it("keeps cross-task causal evidence while discarding runtime noise", async () => {
		const synthesize = vi.fn().mockResolvedValue({
			name: "stateful-tool-workflow",
			description: "Coordinate stateful tool workflows with verified dependency handling.",
			instructions:
				"Inspect contracts, preserve identifiers, follow dependency order, recover errors, and verify final postconditions.",
		});
		const events: SessionEvent[] = [];
		for (let task = 1; task <= 3; task += 1) {
			events.push({ type: "user.prompt", data: { content: `task-${task}` } } as SessionEvent);
			for (let noise = 0; noise < 40; noise += 1)
				events.push({ type: "usage.updated", data: { promptTokens: noise, completionTokens: 0 } } as SessionEvent);
			events.push(toolCall(task));
			events.push(turnEnd(`turn-${task}`));
		}
		const learner = new SkillLearner({
			synthesizer: { synthesize } as never,
			recordStore: { load: vi.fn().mockResolvedValue(events) },
			skillRegistry: { list: () => [], registerSkill: vi.fn() },
			autoApprove: false,
		});

		await learner.handle({ source: "session_record", payload: { kind: "turn.end" } } as unknown as LearningEvent);

		const transcript = synthesize.mock.calls[0]?.[0] as SessionEvent[];
		expect(transcript.filter((event) => event.type === "user.prompt").map((event) => event.data.content)).toEqual([
			"task-1",
			"task-2",
			"task-3",
		]);
		expect(transcript.some((event) => event.type === "usage.updated")).toBe(false);
	});

	it("suppresses a paraphrase of an already loaded workflow", async () => {
		const synthesize = vi.fn().mockResolvedValue({
			name: "dependency-safe-artifact-workflow",
			description: "Safely execute dependent artifact delivery across tools.",
			instructions:
				"Inspect schemas, preserve identifiers, execute dependencies, transform artifacts, export assets, and publish links.",
		});
		const learner = new SkillLearner({
			synthesizer: { synthesize } as never,
			recordStore: {
				load: vi.fn().mockResolvedValue([turnEnd("turn-1"), toolCall(1), turnEnd("turn-2"), turnEnd("turn-3")]),
			},
			skillRegistry: {
				list: () =>
					[
						{
							name: "dependency-aware-artifact-workflow",
							content:
								"Inspect schemas, preserve identifiers, execute dependencies, create records, coordinate services, and schedule messages.",
							source: "auto",
						},
					] as never,
				registerSkill: vi.fn(),
			},
			autoApprove: false,
		});

		const output = await learner.handle({
			source: "session_record",
			payload: { kind: "turn.end" },
		} as unknown as LearningEvent);

		expect(synthesize).toHaveBeenCalledOnce();
		expect(output).toBeUndefined();
	});

	it("does not apply relaxed auto-output dedupe to a project-authored skill", async () => {
		const synthesize = vi.fn().mockResolvedValue({
			name: "dependency-safe-artifact-workflow",
			description: "Safely execute dependent artifact delivery across tools.",
			instructions:
				"Inspect schemas, preserve identifiers, execute dependencies, transform artifacts, export assets, and publish links.",
		});
		const learner = new SkillLearner({
			synthesizer: { synthesize } as never,
			recordStore: {
				load: vi.fn().mockResolvedValue([turnEnd("turn-1"), toolCall(1), turnEnd("turn-2"), turnEnd("turn-3")]),
			},
			skillRegistry: {
				list: () =>
					[
						{
							name: "project-release-workflow",
							content:
								"Inspect schemas, preserve identifiers, execute dependencies, create records, coordinate services, and schedule messages.",
							source: "project",
						},
					] as never,
				registerSkill: vi.fn(),
			},
			autoApprove: false,
		});

		const output = await learner.handle({
			source: "session_record",
			payload: { kind: "turn.end" },
		} as unknown as LearningEvent);

		expect(output?.status).toBe("pending");
	});

	it("suppresses a colliding skill name even when the synthesized wording changes", async () => {
		const synthesize = vi.fn().mockResolvedValue({
			name: "existing-workflow",
			description: "A renamed description with a wholly different surface form.",
			instructions: "Completely different generated wording that should never replace an active skill implicitly.",
		});
		const learner = new SkillLearner({
			synthesizer: { synthesize } as never,
			recordStore: {
				load: vi.fn().mockResolvedValue([turnEnd("turn-1"), toolCall(1), turnEnd("turn-2"), turnEnd("turn-3")]),
			},
			skillRegistry: {
				list: () => [{ name: "existing-workflow", content: "Unrelated active instructions." }] as never,
				registerSkill: vi.fn(),
			},
			autoApprove: false,
		});

		const output = await learner.handle({
			source: "session_record",
			payload: { kind: "turn.end" },
		} as unknown as LearningEvent);

		expect(output).toBeUndefined();
	});

	it("suppresses an expanded paraphrase by token containment below the Jaccard threshold", async () => {
		const common = "inspect schemas preserve identifiers dependency order recover errors verify final state";
		const existingInstructions = `${common} create artifact export upload email calendar attendee draft recipient subject body url handle provider`;
		const generatedInstructions = `${common} transform asset publish distribute message collaboration candidate materialize project link status job retry prerequisite authoritative`;
		const synthesize = vi.fn().mockResolvedValue({
			name: "dependency-aware-artifact-publishing",
			description: "Publish dependent artifacts and coordinate the resulting stakeholder actions.",
			instructions: generatedInstructions,
		});
		const learner = new SkillLearner({
			synthesizer: { synthesize } as never,
			recordStore: {
				load: vi.fn().mockResolvedValue([turnEnd("turn-1"), toolCall(1), turnEnd("turn-2"), turnEnd("turn-3")]),
			},
			skillRegistry: {
				list: () =>
					[
						{
							name: "prepare-artifact-and-coordinate-followup",
							content: existingInstructions,
							source: "auto",
							metadata: {},
						},
					] as never,
				registerSkill: vi.fn(),
			},
			autoApprove: false,
		});

		const output = await learner.handle({
			source: "session_record",
			payload: { kind: "turn.end" },
		} as unknown as LearningEvent);

		expect(synthesize).toHaveBeenCalledOnce();
		expect(output).toBeUndefined();
	});

	it("preserves the synthesis cooldown across a resumed runtime", async () => {
		const synthesize = vi.fn().mockResolvedValue({
			name: "new-workflow",
			description: "Handle a newly observed and materially different reusable workflow.",
			instructions:
				"Inspect a distinct contract, preserve its handles, follow prerequisites, recover bounded errors, and verify authoritative postconditions.",
		});
		const loaded = {
			name: "existing-workflow",
			content: "A completely separate previously learned procedure.",
			source: "auto",
			metadata: { learnedThroughTurns: 3 },
		};
		const learner = new SkillLearner({
			synthesizer: { synthesize } as never,
			recordStore: {
				load: vi
					.fn()
					.mockResolvedValue([
						turnEnd("turn-1"),
						toolCall(1),
						turnEnd("turn-2"),
						turnEnd("turn-3"),
						turnEnd("turn-4"),
						turnEnd("turn-5"),
					]),
			},
			skillRegistry: { list: () => [loaded] as never, registerSkill: vi.fn() },
			autoApprove: false,
			synthesisCooldownEvents: 5,
		});

		const output = await learner.handle({
			source: "session_record",
			payload: { kind: "turn.end" },
		} as unknown as LearningEvent);

		expect(output).toBeUndefined();
		expect(synthesize).not.toHaveBeenCalled();
	});
});

function turnEnd(turnId: string): SessionEvent {
	return { type: "turn.end", data: { turnId } } as unknown as SessionEvent;
}

function toolCall(index: number): SessionEvent {
	return {
		type: "tool.call",
		data: { call: { id: `call-${index}`, name: "fixture_tool", arguments: { index } } },
	} as unknown as SessionEvent;
}
