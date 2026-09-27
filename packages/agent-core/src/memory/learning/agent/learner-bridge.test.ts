import { describe, expect, it, vi } from "vitest";
import { LearnerAgentBridge } from "./learner-bridge.js";
import type { LearnerTrigger } from "./learner-agent.js";
import { SkillLearner } from "../learners/skill.js";
import { CapabilityGapLearner } from "../learners/capability-gap.js";
import { LearningTriage } from "../triage.js";
import type { LearningEvent } from "../event.js";
import type { SessionEvent } from "../../types.js";

const VALID_INSTRUCTIONS =
	"Inspect the advertised tool schemas before choosing operations, preserve every returned identifier, " +
	"execute dependencies in order, and verify final postconditions with authoritative read-back.";
const VALID_DESCRIPTION = "Reuse a verified stateful workflow safely across tasks.";

function capabilityGapEvent(
	description = "Create normalized workflow definitions as one reusable local tool",
): LearningEvent {
	return {
		id: "gap-1",
		source: "capability_gap",
		timestamp: 1,
		payload: {
			description,
			proposedKind: "tool",
			evidence: {
				scope: "workflow",
				futureTasks: ["Build a webhook workflow", "Build a data pipeline"],
				alternativesChecked: ["No existing capability builds workflows"],
			},
		},
	} as unknown as LearningEvent;
}

const gapDecision = { action: "pending" as const, target: "capability_gap", reason: "missing capability needs design" };
const skillDecision = { action: "pending" as const, target: "skill", reason: "candidate reusable turn sequence" };

interface BridgeFixtureOptions {
	autoApproveSkills?: boolean;
	autoApproveCapabilities?: boolean;
	run?: (
		trigger: LearnerTrigger,
	) => Promise<{ proposals: number; declined: boolean; failure?: string; cancelled?: boolean }>;
	shouldTriggerSkillReview?: boolean;
	synthesize?: (input: unknown) => Promise<unknown>;
	journalEvents?: SessionEvent[];
}

function makeBridge(options: BridgeFixtureOptions = {}) {
	const processor = {
		submitAgentProposal: vi.fn(async (): Promise<{ stashed: boolean; reason?: string }> => ({ stashed: true })),
	};
	const writeSkill = vi.fn(async () => "C:/fixture/.kageko/skills/auto/x/SKILL.md");
	const registerSkill = vi.fn(async () => ({ name: "x", source: "auto" }));
	const skillRegistry = { list: () => [] as never[], registerSkill };
	const toolRegistry = { register: vi.fn() };
	const skillLearner = new SkillLearner({
		synthesizer: { writeSkill } as never,
		recordStore: { load: async () => [] },
		skillRegistry: skillRegistry as never,
		toolRegistry: toolRegistry as never,
		autoApprove: options.autoApproveSkills ?? false,
	});
	const writeToolManifest = vi.fn(async () => "C:/fixture/.kageko/tools/auto/x/manifest.json");
	const capabilityGapLearner = new CapabilityGapLearner({
		synthesizer: { writeToolManifest, writeMcpManifest: vi.fn() } as never,
		autoApprove: options.autoApproveCapabilities ?? false,
	});
	const capabilitySynthesizer = {
		synthesize: vi.fn(
			options.synthesize ??
				(async () => ({
					manifest: {
						kind: "tool",
						name: "create-workflow",
						description: "Create and configure normalized workflow definitions programmatically.",
						parameters: { type: "object", properties: {}, required: [] },
						command: "node",
						args: ["{{__args_json}}"],
					},
					code: "process.stdout.write('{}')",
				})),
		),
	};
	const triggers = { shouldTriggerSkillReview: vi.fn(async () => options.shouldTriggerSkillReview ?? true) };
	const onDiagnostic = vi.fn();
	const bridge = new LearnerAgentBridge({
		processor: processor as never,
		skillLearner,
		capabilityGapLearner,
		capabilitySynthesizer: capabilitySynthesizer as never,
		triggers: triggers as never,
		recordStore: { load: async () => options.journalEvents ?? [] },
		skillRegistry: skillRegistry as never,
		capabilityInventory: () => [],
		autoApproveSkills: options.autoApproveSkills ?? false,
		autoApproveCapabilities: options.autoApproveCapabilities ?? false,
		onDiagnostic,
	});
	const runner = {
		run: vi.fn(options.run ?? (async () => ({ proposals: 1, declined: false }))),
	};
	bridge.attachRunner(runner as never);
	return {
		bridge,
		runner,
		processor,
		triggers,
		onDiagnostic,
		capabilitySynthesizer,
		writeSkill,
		writeToolManifest,
		registerSkill,
		toolRegistry,
	};
}

describe("LearnerAgentBridge.handle", () => {
	it("routes capability_gap events to a learner run and returns nothing on success", async () => {
		const { bridge, runner } = makeBridge();
		const event = capabilityGapEvent();
		const output = await bridge.handle(event, gapDecision);
		expect(output).toBeUndefined();
		expect(runner.run).toHaveBeenCalledWith({ kind: "capability_gap", event });
	});

	it("returns the legacy failed audit shape with the provider error text when the run fails", async () => {
		const { bridge } = makeBridge({
			run: async () => ({ proposals: 0, declined: false, failure: "503: our servers are currently overloaded" }),
		});
		const output = (await bridge.handle(capabilityGapEvent(), gapDecision)) as Record<string, unknown>;
		expect(output).toMatchObject({
			kind: "none",
			description: "Create normalized workflow definitions as one reusable local tool",
			fingerprint: "tool:Create normalized workflow definitions as one reusable local tool",
			status: "failed",
		});
		expect(String(output["failure"])).toContain("overloaded");
	});

	it("surfaces a sink-captured synthesis failure as the failed audit shape", async () => {
		let bridgeRef!: ReturnType<typeof makeBridge>["bridge"];
		const fixture = makeBridge({
			synthesize: async () => {
				throw new Error("Capability synthesis failed: 429 Too Many Requests: usage limit reached");
			},
			run: async (trigger) => {
				await bridgeRef.submitCapabilityProposal(
					{ description: "Create normalized workflow definitions as one reusable local tool" },
					trigger,
				);
				return { proposals: 0, declined: true };
			},
		});
		bridgeRef = fixture.bridge;
		const output = (await fixture.bridge.handle(capabilityGapEvent(), gapDecision)) as Record<string, unknown>;
		expect(output["status"]).toBe("failed");
		expect(String(output["failure"])).toContain("usage limit");
	});

	it("returns nothing when the learner declines a capability gap without a failure", async () => {
		const { bridge, processor } = makeBridge({ run: async () => ({ proposals: 0, declined: true }) });
		expect(await bridge.handle(capabilityGapEvent(), gapDecision)).toBeUndefined();
		expect(processor.submitAgentProposal).not.toHaveBeenCalled();
	});

	it("returns nothing and writes no audit entry when the run was cancelled by runner close", async () => {
		const { bridge, processor } = makeBridge({
			run: async () => ({ proposals: 0, declined: false, cancelled: true }),
		});
		expect(await bridge.handle(capabilityGapEvent(), gapDecision)).toBeUndefined();
		expect(processor.submitAgentProposal).not.toHaveBeenCalled();
	});

	it("reports a diagnostic when a capability run fails after a proposal was accepted", async () => {
		const { bridge, onDiagnostic, processor } = makeBridge({
			run: async () => ({ proposals: 1, declined: false, failure: "late provider error" }),
		});
		expect(await bridge.handle(capabilityGapEvent(), gapDecision)).toBeUndefined();
		expect(processor.submitAgentProposal).not.toHaveBeenCalled();
		expect(onDiagnostic).toHaveBeenCalled();
	});

	it("gates skill events through the trigger check before any run", async () => {
		const { bridge, runner, triggers } = makeBridge({ shouldTriggerSkillReview: false });
		const event = {
			id: "evt-1",
			source: "session_record",
			timestamp: 1,
			payload: { kind: "turn.end" },
		} as unknown as LearningEvent;
		expect(await bridge.handle(event, skillDecision)).toBeUndefined();
		expect(triggers.shouldTriggerSkillReview).toHaveBeenCalledWith(event);
		expect(runner.run).not.toHaveBeenCalled();
	});

	it("runs a skill review when the gate passes and stays silent on run failure", async () => {
		const event = {
			id: "evt-1",
			source: "session_record",
			timestamp: 1,
			payload: { kind: "turn.end" },
		} as unknown as LearningEvent;
		const passing = makeBridge({ shouldTriggerSkillReview: true });
		expect(await passing.bridge.handle(event, skillDecision)).toBeUndefined();
		expect(passing.runner.run).toHaveBeenCalledWith({ kind: "skill_review", event });

		const failing = makeBridge({
			shouldTriggerSkillReview: true,
			run: async () => ({ proposals: 0, declined: false, failure: "provider unavailable" }),
		});
		expect(await failing.bridge.handle(event, skillDecision)).toBeUndefined();
		expect(failing.onDiagnostic).toHaveBeenCalled();
		expect(failing.processor.submitAgentProposal).not.toHaveBeenCalled();
	});

	it("ignores unrelated targets", async () => {
		const { bridge, runner } = makeBridge();
		expect(await bridge.handle(capabilityGapEvent(), { action: "learn", target: "knowledge" })).toBeUndefined();
		expect(runner.run).not.toHaveBeenCalled();
	});
});

describe("LearnerAgentBridge.submitSkillProposal", () => {
	const trigger: LearnerTrigger = { kind: "skill_review", event: capabilityGapEvent() };
	const skill = { name: "stateful-workflows", description: VALID_DESCRIPTION, instructions: VALID_INSTRUCTIONS };

	it("queues a validated proposal with the legacy pending shape", async () => {
		const journalEvents = [0, 1, 2].map(
			(index) => ({ type: "turn.end", data: { turnId: `turn-${index}` } }) as unknown as SessionEvent,
		);
		const { bridge, processor } = makeBridge({ journalEvents });
		const result = await bridge.submitSkillProposal(skill, trigger);
		expect(result).toEqual({ accepted: true, status: "pending" });
		expect(processor.submitAgentProposal).toHaveBeenCalledOnce();
		const [target, event, output] = processor.submitAgentProposal.mock.calls[0] as unknown as [
			string,
			LearningEvent,
			Record<string, unknown>,
		];
		expect(target).toBe("skill");
		expect(event).toBe(trigger.event);
		expect(output).toMatchObject({
			name: "stateful-workflows",
			description: VALID_DESCRIPTION,
			instructions: VALID_INSTRUCTIONS,
			status: "pending",
			learnedThroughTurns: 3,
		});
		expect(output["fingerprint"]).toBe(LearningTriage.fingerprint(VALID_INSTRUCTIONS));
	});

	it("auto-approves through the legacy write path and still fires the output hook", async () => {
		const { bridge, processor, writeSkill, registerSkill, toolRegistry } = makeBridge({ autoApproveSkills: true });
		const result = await bridge.submitSkillProposal(skill, trigger);
		expect(result).toEqual({ accepted: true, status: "approved" });
		expect(writeSkill).toHaveBeenCalledOnce();
		expect(registerSkill).toHaveBeenCalledOnce();
		expect(toolRegistry.register).toHaveBeenCalledOnce();
		const [, , output] = processor.submitAgentProposal.mock.calls[0] as unknown as [
			string,
			unknown,
			Record<string, unknown>,
		];
		expect(output["status"]).toBe("approved");
		expect(output["filePath"]).toContain("SKILL.md");
	});

	it("rejects invalid and duplicate proposals", async () => {
		const { bridge } = makeBridge();
		const invalid = await bridge.submitSkillProposal({ name: "x", description: "short", instructions: "no" }, trigger);
		expect(invalid.accepted).toBe(false);

		expect((await bridge.submitSkillProposal(skill, trigger)).accepted).toBe(true);
		const duplicate = await bridge.submitSkillProposal(skill, trigger);
		expect(duplicate.accepted).toBe(false);
	});

	it("releases the dedupe suppression when a proposal is rejected", async () => {
		const { bridge, processor } = makeBridge();
		await bridge.submitSkillProposal(skill, trigger);
		const [, , output] = processor.submitAgentProposal.mock.calls[0] as unknown as [string, unknown, unknown];
		bridge.reject(output);
		expect((await bridge.submitSkillProposal(skill, trigger)).accepted).toBe(true);
	});
});

describe("LearnerAgentBridge.submitCapabilityProposal", () => {
	const trigger: LearnerTrigger = { kind: "capability_gap", event: capabilityGapEvent() };

	it("runs the synthesizer for description-only proposals and queues the legacy pending shape", async () => {
		const { bridge, processor, capabilitySynthesizer } = makeBridge();
		const result = await bridge.submitCapabilityProposal(
			{ description: "Create normalized workflow definitions as one reusable local tool", proposedKind: "tool" },
			trigger,
		);
		expect(result).toEqual({ accepted: true, status: "pending", name: "create-workflow" });
		expect(capabilitySynthesizer.synthesize).toHaveBeenCalledOnce();
		const synthInput = capabilitySynthesizer.synthesize.mock.calls[0]?.[0] as Record<string, unknown>;
		expect(synthInput["description"]).toBe("Create normalized workflow definitions as one reusable local tool");
		expect(synthInput["proposedKind"]).toBe("tool");
		const [, , output] = processor.submitAgentProposal.mock.calls[0] as unknown as [
			string,
			unknown,
			Record<string, unknown>,
		];
		expect(output).toMatchObject({
			kind: "tool",
			name: "create-workflow",
			command: "node",
			args: ["{{__args_json}}"],
			fingerprint: "tool:Create normalized workflow definitions as one reusable local tool",
			status: "pending",
		});
		expect(typeof output["code"]).toBe("string");
	});

	it("validates an inline candidate instead of calling the synthesizer", async () => {
		const { bridge, processor, capabilitySynthesizer } = makeBridge();
		const result = await bridge.submitCapabilityProposal(
			{
				description: "Create normalized workflow definitions as one reusable local tool",
				proposedKind: "tool",
				candidate: {
					name: "create-workflow",
					description: "Create and configure normalized workflow definitions programmatically.",
					parameters: { type: "object", properties: {}, required: [] },
					command: "node",
					args: ["{{__args_json}}"],
					code: "process.stdout.write('{}')",
				},
			},
			trigger,
		);
		expect(result).toEqual({ accepted: true, status: "pending", name: "create-workflow" });
		expect(capabilitySynthesizer.synthesize).not.toHaveBeenCalled();
		expect(processor.submitAgentProposal).toHaveBeenCalledOnce();
	});

	it("rejects when the value policy finds no reuse evidence", async () => {
		const noEvidence = {
			id: "gap-2",
			source: "capability_gap",
			timestamp: 1,
			payload: { description: "Create normalized workflow definitions as one reusable local tool" },
		} as unknown as LearningEvent;
		const { bridge } = makeBridge();
		const result = await bridge.submitCapabilityProposal(
			{ description: "Create normalized workflow definitions as one reusable local tool" },
			{ kind: "capability_gap", event: noEvidence },
		);
		expect(result.accepted).toBe(false);
		expect(result.reason).toContain("evidence");
	});

	it("rejects an overlapping repeat request", async () => {
		const { bridge } = makeBridge();
		const first = await bridge.submitCapabilityProposal(
			{ description: "Create normalized workflow definitions as one reusable local tool", proposedKind: "tool" },
			trigger,
		);
		expect(first.accepted).toBe(true);
		const second = await bridge.submitCapabilityProposal(
			{ description: "Create normalized workflow definitions as one reusable local tool", proposedKind: "tool" },
			trigger,
		);
		expect(second.accepted).toBe(false);
	});

	it("auto-approves through the legacy manifest writer and fires the output hook", async () => {
		const { bridge, processor, writeToolManifest } = makeBridge({ autoApproveCapabilities: true });
		const result = await bridge.submitCapabilityProposal(
			{ description: "Create normalized workflow definitions as one reusable local tool", proposedKind: "tool" },
			trigger,
		);
		expect(result).toEqual({ accepted: true, status: "approved", name: "create-workflow" });
		expect(writeToolManifest).toHaveBeenCalledOnce();
		const [, , output] = processor.submitAgentProposal.mock.calls[0] as unknown as [
			string,
			unknown,
			Record<string, unknown>,
		];
		expect(output["status"]).toBe("approved");
		expect(output["filePath"]).toContain("manifest.json");
	});
});

describe("LearnerAgentBridge approval delegation", () => {
	it("delegates skill approval to the legacy skill learner", async () => {
		const { bridge, writeSkill, registerSkill } = makeBridge();
		const result = (await bridge.approve({
			name: "stateful-workflows",
			description: VALID_DESCRIPTION,
			instructions: VALID_INSTRUCTIONS,
		})) as { name: string; filePath: string };
		expect(result.name).toBe("stateful-workflows");
		expect(result.filePath).toContain("SKILL.md");
		expect(writeSkill).toHaveBeenCalledOnce();
		expect(registerSkill).toHaveBeenCalledOnce();
	});

	it("delegates capability approval to the legacy capability learner", async () => {
		const { bridge, writeToolManifest } = makeBridge();
		const result = (await bridge.approve({
			kind: "tool",
			name: "create-workflow",
			description: "Create normalized workflow definitions as one reusable local tool.",
			parameters: { type: "object", properties: {}, required: [] },
			command: "node",
			args: ["{{__args_json}}"],
			code: "process.stdout.write('{}')",
		})) as { name: string; filePath: string };
		expect(result.name).toBe("create-workflow");
		expect(writeToolManifest).toHaveBeenCalledOnce();
	});
});

describe("LearnerAgentBridge stale-run submissions", () => {
	const trigger: LearnerTrigger = { kind: "capability_gap", event: capabilityGapEvent() };
	const staleRun = { id: "ended-run", isCurrent: () => false, signal: new AbortController().signal };

	it("drops a stale-run capability submission before synthesis or queue writes", async () => {
		const { bridge, processor, capabilitySynthesizer, onDiagnostic } = makeBridge();
		const result = await bridge.submitCapabilityProposal(
			{ description: "Create normalized workflow definitions as one reusable local tool", proposedKind: "tool" },
			trigger,
			staleRun as never,
		);
		expect(result.accepted).toBe(false);
		expect(capabilitySynthesizer.synthesize).not.toHaveBeenCalled();
		expect(processor.submitAgentProposal).not.toHaveBeenCalled();
		expect(onDiagnostic).toHaveBeenCalled();
	});

	it("drops a capability submission whose run ended during synthesis", async () => {
		let current = true;
		const run = { id: "run-1", isCurrent: () => current, signal: new AbortController().signal };
		const { bridge, processor } = makeBridge({
			synthesize: async () => {
				// The runner abandoned this sink mid-flight (timeout/close).
				current = false;
				return {
					manifest: {
						kind: "tool",
						name: "create-workflow",
						description: "Create and configure normalized workflow definitions programmatically.",
						parameters: { type: "object", properties: {}, required: [] },
						command: "node",
						args: ["{{__args_json}}"],
					},
					code: "process.stdout.write('{}')",
				};
			},
		});
		const result = await bridge.submitCapabilityProposal(
			{ description: "Create normalized workflow definitions as one reusable local tool", proposedKind: "tool" },
			trigger,
			run as never,
		);
		expect(result.accepted).toBe(false);
		expect(processor.submitAgentProposal).not.toHaveBeenCalled();
	});

	it("drops a stale-run skill submission without writing", async () => {
		const { bridge, processor, writeSkill, onDiagnostic } = makeBridge();
		const result = await bridge.submitSkillProposal(
			{ name: "stateful-workflows", description: VALID_DESCRIPTION, instructions: VALID_INSTRUCTIONS },
			{ kind: "skill_review", event: capabilityGapEvent() },
			staleRun as never,
		);
		expect(result.accepted).toBe(false);
		expect(processor.submitAgentProposal).not.toHaveBeenCalled();
		expect(writeSkill).not.toHaveBeenCalled();
		expect(onDiagnostic).toHaveBeenCalled();
	});

	it("passes the run abort signal into the synthesizer", async () => {
		const controller = new AbortController();
		const run = { id: "run-2", isCurrent: () => true, signal: controller.signal };
		const { bridge, capabilitySynthesizer } = makeBridge();
		await bridge.submitCapabilityProposal(
			{ description: "Create normalized workflow definitions as one reusable local tool", proposedKind: "tool" },
			trigger,
			run as never,
		);
		const synthInput = capabilitySynthesizer.synthesize.mock.calls[0]?.[0] as Record<string, unknown>;
		expect(synthInput["signal"]).toBe(controller.signal);
	});
});

describe("LearnerAgentBridge publish/stash failure handling", () => {
	const trigger: LearnerTrigger = { kind: "skill_review", event: capabilityGapEvent() };
	const skill = { name: "stateful-workflows", description: VALID_DESCRIPTION, instructions: VALID_INSTRUCTIONS };
	const capabilityInput = {
		description: "Create normalized workflow definitions as one reusable local tool",
		proposedKind: "tool" as const,
	};
	const capabilityTrigger: LearnerTrigger = { kind: "capability_gap", event: capabilityGapEvent() };

	it("auto-approve skill publish failure returns accepted:false with a diagnostic and does not suppress a retry", async () => {
		const { bridge, writeSkill, onDiagnostic, processor } = makeBridge({ autoApproveSkills: true });
		writeSkill.mockRejectedValueOnce(new Error("disk full"));
		const first = await bridge.submitSkillProposal(skill, trigger);
		expect(first.accepted).toBe(false);
		expect(first.reason).toContain("disk full");
		expect(onDiagnostic).toHaveBeenCalled();
		expect(processor.submitAgentProposal).not.toHaveBeenCalled();

		// The fingerprint was never recorded, so an identical retry runs the
		// publish path again instead of being deduped.
		const retry = await bridge.submitSkillProposal(skill, trigger);
		expect(retry).toEqual({ accepted: true, status: "approved" });
		expect(writeSkill).toHaveBeenCalledTimes(2);
	});

	it("auto-approve capability publish failure returns accepted:false with a diagnostic and does not suppress a retry", async () => {
		const { bridge, writeToolManifest, onDiagnostic, processor } = makeBridge({ autoApproveCapabilities: true });
		writeToolManifest.mockRejectedValueOnce(new Error("manifest write failed"));
		const first = await bridge.submitCapabilityProposal(capabilityInput, capabilityTrigger);
		expect(first.accepted).toBe(false);
		expect(first.reason).toContain("manifest write failed");
		expect(onDiagnostic).toHaveBeenCalled();
		expect(processor.submitAgentProposal).not.toHaveBeenCalled();

		const retry = await bridge.submitCapabilityProposal(capabilityInput, capabilityTrigger);
		expect(retry).toEqual({ accepted: true, status: "approved", name: "create-workflow" });
		expect(writeToolManifest).toHaveBeenCalledTimes(2);
	});

	it("a stash miss leaves skill dedup untouched", async () => {
		const { bridge, processor } = makeBridge();
		processor.submitAgentProposal.mockResolvedValueOnce({ stashed: false, reason: "duplicate" });
		expect((await bridge.submitSkillProposal(skill, trigger)).accepted).toBe(true);
		// Dedup was not recorded on the stash miss, so the identical proposal is
		// evaluated (and stashed) rather than suppressed.
		expect((await bridge.submitSkillProposal(skill, trigger)).accepted).toBe(true);
		expect(processor.submitAgentProposal).toHaveBeenCalledTimes(2);
	});

	it("a stash miss leaves capability dedup untouched", async () => {
		const { bridge, processor, capabilitySynthesizer } = makeBridge();
		processor.submitAgentProposal.mockResolvedValueOnce({ stashed: false, reason: "duplicate" });
		expect((await bridge.submitCapabilityProposal(capabilityInput, capabilityTrigger)).accepted).toBe(true);
		expect((await bridge.submitCapabilityProposal(capabilityInput, capabilityTrigger)).accepted).toBe(true);
		expect(processor.submitAgentProposal).toHaveBeenCalledTimes(2);
		expect(capabilitySynthesizer.synthesize).toHaveBeenCalledTimes(2);
	});
});
