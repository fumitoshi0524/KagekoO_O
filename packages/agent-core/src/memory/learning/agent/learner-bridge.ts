import { capDescription } from "../../capability-synthesizer.js";
import type { CapabilitySynthesizer } from "../../capability-synthesizer.js";
import type { CapabilityManifest, SessionEvent, SynthesizedSkill } from "../../types.js";
import { LearningTriage } from "../triage.js";
import type { CapabilityGapEvidence, LearningEvent, RequiredCapabilityContract } from "../event.js";
import type { Learner, TriageDecision } from "../types.js";
import type { JournalEventStore } from "../types.js";
import type { LearningProcessor } from "../processor.js";
import type { CapabilityGapLearner, CapabilityOutput } from "../learners/capability-gap.js";
import { requestsOverlap } from "../learners/capability-gap.js";
import type { SkillLearner, SkillOutput, SkillRegistryLike } from "../learners/skill.js";
import { assessCapabilityValue, type CapabilityInventoryItem } from "../capability-value-policy.js";
import { validateCapabilityProposal, validateSkillProposal } from "./proposals.js";
import type { LearningTriggers } from "./triggers.js";
import type { LearnerAgentRunner, LearnerProposalSinks, LearnerRunContext, LearnerTrigger } from "./learner-agent.js";
import type {
	LearnerCapabilityProposal,
	LearnerProposalKind,
	SubmitCapabilityProposalResult,
	SubmitSkillProposalResult,
} from "./learner-tools.js";

/** Bound the dedupe sets; oldest fingerprints are evicted past this size. */
const MAX_SEEN_FINGERPRINTS = 500;

/** The payload shape the bridge reads from a capability_gap event (mirrors CapabilityGapLearner.handle). */
interface CapabilityGapEventPayload {
	description?: string;
	context?: string;
	proposedKind?: "tool" | "mcp";
	requiredContracts?: readonly RequiredCapabilityContract[];
	evidence?: CapabilityGapEvidence;
}

export interface LearnerAgentBridgeOptions {
	processor: LearningProcessor;
	/** Legacy learners retained as approve/reject/publish adapters. */
	skillLearner: SkillLearner;
	capabilityGapLearner: CapabilityGapLearner;
	capabilitySynthesizer: CapabilitySynthesizer;
	triggers: LearningTriggers;
	recordStore: JournalEventStore;
	skillRegistry?: SkillRegistryLike;
	capabilityInventory?: () => readonly CapabilityInventoryItem[];
	autoApproveSkills: boolean;
	autoApproveCapabilities: boolean;
	/** Defense-in-depth restriction matching the learner tool surfaces. */
	proposalKinds?: readonly LearnerProposalKind[];
	/** Dedupe threshold for skill proposals; defaults to DEFAULT_SKILL_SIMILARITY_THRESHOLD. */
	skillSimilarityThreshold?: number;
	onDiagnostic?: (message: string, error?: unknown) => void | Promise<void>;
}

/**
 * Processor-facing adapter that routes `skill` / `capability_gap` learning
 * events through the resident learner agent instead of calling the legacy
 * learners' inline synthesis.
 *
 * The deterministic spine is unchanged: trigger gating happens before any
 * model call, proposals flow through {@link LearningProcessor.submitAgentProposal}
 * into the same pending queue, and external approval still delegates verbatim
 * to the legacy `SkillLearner`/`CapabilityGapLearner` publish paths.
 */
export class LearnerAgentBridge implements Learner, LearnerProposalSinks {
	private readonly processor: LearningProcessor;
	private readonly skillLearner: SkillLearner;
	private readonly capabilityGapLearner: CapabilityGapLearner;
	private readonly capabilitySynthesizer: CapabilitySynthesizer;
	private readonly triggers: LearningTriggers;
	private readonly recordStore: JournalEventStore;
	private readonly skillRegistry?: SkillRegistryLike;
	private readonly capabilityInventory?: () => readonly CapabilityInventoryItem[];
	private readonly autoApproveSkills: boolean;
	private readonly autoApproveCapabilities: boolean;
	private readonly proposalKinds: ReadonlySet<LearnerProposalKind>;
	private readonly skillSimilarityThreshold?: number;
	private readonly onDiagnostic?: (message: string, error?: unknown) => void | Promise<void>;
	private _runner?: LearnerAgentRunner;
	private _seenSkillFingerprints = new Set<string>();
	private _seenCapabilityFingerprints = new Set<string>();
	private _seenCapabilityRequests = new Map<string, { kind?: "tool" | "mcp"; description: string }>();
	/**
	 * Synthesis failure observed by the capability sink during the in-flight
	 * run. Runs are serialized by the runner and the processor delivers events
	 * sequentially, so a single slot is race-free.
	 */
	private _capabilityFailure?: string;

	constructor(options: LearnerAgentBridgeOptions) {
		this.processor = options.processor;
		this.skillLearner = options.skillLearner;
		this.capabilityGapLearner = options.capabilityGapLearner;
		this.capabilitySynthesizer = options.capabilitySynthesizer;
		this.triggers = options.triggers;
		this.recordStore = options.recordStore;
		this.skillRegistry = options.skillRegistry;
		this.capabilityInventory = options.capabilityInventory;
		this.autoApproveSkills = options.autoApproveSkills;
		this.autoApproveCapabilities = options.autoApproveCapabilities;
		this.proposalKinds = new Set(options.proposalKinds ?? ["skill", "tool", "mcp"]);
		this.skillSimilarityThreshold = options.skillSimilarityThreshold;
		this.onDiagnostic = options.onDiagnostic;
	}

	/**
	 * One-time wiring for the mutual dependency: the runner's proposal sinks
	 * are this bridge, and the bridge's event handling drives the runner.
	 */
	attachRunner(runner: LearnerAgentRunner): void {
		if (this._runner) throw new Error("LearnerAgentBridge runner is already attached");
		this._runner = runner;
	}

	async handle(event: LearningEvent, decision: TriageDecision): Promise<unknown> {
		if (decision.target === "capability_gap") return this._handleCapabilityGap(event);
		if (decision.target === "skill") return this._handleSkillReview(event);
		return undefined;
	}

	/** Publish path for approved pending entries: delegate verbatim to the legacy learners. */
	async approve(output: unknown): Promise<unknown> {
		const kind = (output as { kind?: unknown } | undefined)?.kind;
		if (kind === "tool" || kind === "mcp" || kind === "none") {
			return this.capabilityGapLearner.approve(output);
		}
		return this.skillLearner.approve(output);
	}

	/** Release bridge-side and legacy suppression state for a rejected proposal. */
	reject(output: unknown): void {
		const fingerprint = (output as { fingerprint?: unknown } | undefined)?.fingerprint;
		if (typeof fingerprint === "string") {
			this._seenSkillFingerprints.delete(fingerprint);
			this._seenCapabilityFingerprints.delete(fingerprint);
			this._seenCapabilityRequests.delete(fingerprint);
		}
		this.skillLearner.reject(output);
		this.capabilityGapLearner.reject(output);
	}

	private async _handleCapabilityGap(event: LearningEvent): Promise<CapabilityOutput | undefined> {
		if (!this.proposalKinds.has("tool") && !this.proposalKinds.has("mcp")) return undefined;
		const payload = event.payload as CapabilityGapEventPayload;
		if (!payload.description) return undefined;
		this._capabilityFailure = undefined;
		const result = await this._requireRunner().run({ kind: "capability_gap", event });
		// A run cancelled by runner close is a shutdown, not an auditable failure.
		if (result.cancelled) return undefined;
		if (result.proposals > 0) {
			if (result.failure) {
				this._reportDiagnostic("Learner capability run failed after a proposal was accepted.", result.failure);
			}
			return undefined;
		}
		// A failed run (provider error, timeout) or a failed synthesis inside the
		// sink keeps the legacy auditable shape: the pending queue records the
		// attempt with the original error text so infra classification can see it.
		const failure = result.failure ?? this._capabilityFailure;
		if (!failure) return undefined;
		return {
			kind: "none",
			description: capDescription(payload.description),
			fingerprint: capabilityFingerprint(payload.proposedKind, payload.description),
			status: "failed",
			failure: capDescription(failure, 2048),
		};
	}

	private async _handleSkillReview(event: LearningEvent): Promise<undefined> {
		if (!this.proposalKinds.has("skill")) return undefined;
		if (!(await this.triggers.shouldTriggerSkillReview(event))) return undefined;
		const result = await this._requireRunner().run({ kind: "skill_review", event });
		// Mirror the legacy SkillLearner failure surface: a failed synthesis was
		// a diagnostic from the processor, never a pending-queue entry.
		if (result.failure && !result.cancelled) {
			this._reportDiagnostic("Learner skill review run failed.", result.failure);
		}
		return undefined;
	}

	async submitSkillProposal(
		skill: SynthesizedSkill,
		trigger: LearnerTrigger,
		run?: LearnerRunContext,
	): Promise<SubmitSkillProposalResult> {
		if (!this.proposalKinds.has("skill")) return { accepted: false, reason: "skill proposals are disabled" };
		if (!this._isLiveRun(run)) return { accepted: false, reason: "the issuing learner run has ended" };
		// Re-validate against the real skill registry (the tool validated against
		// the coarse inventory view; this is the authoritative dedupe surface).
		const verdict = validateSkillProposal(skill, this.skillRegistry?.list() ?? [], {
			similarityThreshold: this.skillSimilarityThreshold,
		});
		if (!verdict.ok) return { accepted: false, reason: verdict.reason };

		const fingerprint = LearningTriage.fingerprint(verdict.skill.instructions);
		if (this._seenSkillFingerprints.has(fingerprint)) {
			return { accepted: false, reason: "an identical skill proposal was already produced" };
		}

		const events = await this.recordStore.load();
		// A sink abandoned by a timeout or runner close must never write under a
		// stale (or a new) run's authority.
		if (!this._isLiveRun(run)) return { accepted: false, reason: "the issuing learner run has ended" };

		const completedTurns = events.filter((candidate) => candidate.type === "turn.end").length;
		// Same post-synthesis shape as the legacy SkillLearner.handle.
		const output: SkillOutput = {
			...verdict.skill,
			fingerprint,
			status: "pending",
			learnedThroughTurns: completedTurns,
		};
		if (this.autoApproveSkills) {
			let filePath: string;
			try {
				({ filePath } = await this.skillLearner.approve(output));
			} catch (error) {
				// A failed publish must surface as a diagnostic and must not
				// suppress a later identical proposal: dedup state is only
				// recorded after the write + hot-load succeeded.
				const message = error instanceof Error ? error.message : String(error);
				this._reportDiagnostic("Learner auto-approved skill publish failed.", error);
				return { accepted: false, reason: message };
			}
			this._seenSkillFingerprints.add(fingerprint);
			evictOldest(this._seenSkillFingerprints);
			// Approved output is never stashed, but submitAgentProposal still
			// fires the onOutput hook (capability reload, graph observation).
			await this.processor.submitAgentProposal("skill", trigger.event, {
				...output,
				filePath,
				status: "approved",
			});
			return { accepted: true, status: "approved" };
		}
		const stash = await this.processor.submitAgentProposal("skill", trigger.event, output);
		// Record the dedup fingerprint only once the proposal is durably queued;
		// a stash miss must not suppress a later identical proposal.
		if (stash.stashed) {
			this._seenSkillFingerprints.add(fingerprint);
			evictOldest(this._seenSkillFingerprints);
		}
		return { accepted: true, status: "pending" };
	}

	async submitCapabilityProposal(
		input: LearnerCapabilityProposal,
		trigger: LearnerTrigger,
		run?: LearnerRunContext,
	): Promise<SubmitCapabilityProposalResult> {
		const requestedKind = input.candidate?.kind ?? input.proposedKind;
		if (requestedKind && !this.proposalKinds.has(requestedKind))
			return { accepted: false, reason: `${requestedKind} proposals are disabled` };
		if (!this.proposalKinds.has("tool") && !this.proposalKinds.has("mcp"))
			return { accepted: false, reason: "capability proposals are disabled" };
		if (!this._isLiveRun(run)) return { accepted: false, reason: "the issuing learner run has ended" };
		const payload = trigger.event.payload as CapabilityGapEventPayload;
		const description = input.description;
		// The value policy and dedupe mirror CapabilityGapLearner.handle; the
		// reuse evidence stays on the trigger event because the proposal tool
		// schema carries no evidence field.
		if (this.capabilityInventory) {
			const value = assessCapabilityValue(description, payload.evidence, this.capabilityInventory());
			if (!value.accepted) return { accepted: false, reason: value.reason };
		}
		const proposedKind = input.proposedKind ?? payload.proposedKind;
		const requiredContracts = pickRequiredContracts(input.requiredContracts, payload.requiredContracts);
		const fingerprint = capabilityFingerprint(proposedKind, description);
		if (this._seenCapabilityFingerprints.has(fingerprint)) {
			return { accepted: false, reason: "an identical capability request was already produced" };
		}
		if (
			[...this._seenCapabilityRequests.values()].some((request) => requestsOverlap(request.description, description))
		) {
			return { accepted: false, reason: "an earlier capability request already covers this" };
		}

		let manifest: CapabilityManifest | undefined;
		let code: string | undefined;
		if (input.candidate) {
			// The effective kind (proposal first, event payload as fallback) is the
			// same value used for the fingerprint above.
			const verdict = validateCapabilityProposal({
				kind: proposedKind,
				...input.candidate,
				requiredContracts,
			});
			if (!verdict.ok) return { accepted: false, reason: verdict.reason };
			const { code: candidateCode, ...candidateManifest } = verdict.output;
			manifest = candidateManifest;
			code = candidateCode;
		} else {
			const recentEvents = await this.recordStore.load();
			const context = input.context ?? payload.context;
			let synthesized;
			try {
				synthesized = await this.capabilitySynthesizer.synthesize({
					description,
					...(context ? { context } : {}),
					...(proposedKind ? { proposedKind } : {}),
					...(requiredContracts ? { requiredContracts } : {}),
					// DurableEvent is a superset of SessionEvent at runtime; the
					// synthesizer only reads fields common to both types.
					recentEvents: recentEvents as SessionEvent[],
					// Let an abandoned run (timeout/runner close) cancel its provider call.
					...(run ? { signal: run.signal } : {}),
				});
			} catch (error) {
				// Keep the original provider/manifest error text: the bridge shapes
				// it into the auditable failed output after the run, and the
				// benchmark classifies infrastructure failures from this message.
				const message = error instanceof Error ? error.message : String(error);
				this._capabilityFailure = message;
				return { accepted: false, reason: message };
			}
			if (!synthesized) {
				this._capabilityFailure = "Capability synthesis returned no safe reusable capability.";
				return { accepted: false, reason: this._capabilityFailure };
			}
			// Support both the { manifest, code } shape and the legacy manifest-only shape.
			const s = synthesized as { manifest?: CapabilityManifest; code?: string };
			({ manifest, code } =
				s.manifest && typeof s.manifest === "object"
					? { manifest: s.manifest, code: s.code }
					: { manifest: synthesized as unknown as CapabilityManifest, code: undefined });
		}
		// A sink abandoned mid-synthesis (timeout/runner close) must never write
		// under a stale or superseded run's authority.
		if (!this._isLiveRun(run)) return { accepted: false, reason: "the issuing learner run has ended" };
		if (!manifest) return { accepted: false, reason: "synthesis produced no manifest" };
		manifest.description = capDescription(manifest.description);

		// Same output shape as the legacy CapabilityGapLearner.handle.
		if (this.autoApproveCapabilities) {
			let filePath: string;
			try {
				({ filePath } = (await this.capabilityGapLearner.approve({ ...manifest, code })) as {
					name: string;
					filePath: string;
				});
			} catch (error) {
				// A failed publish must surface as a diagnostic and must not
				// suppress a later identical proposal: dedup state is only
				// recorded after the write succeeded.
				const message = error instanceof Error ? error.message : String(error);
				this._reportDiagnostic("Learner auto-approved capability publish failed.", error);
				return { accepted: false, reason: message };
			}
			this._rememberCapability(fingerprint, proposedKind, description);
			await this.processor.submitAgentProposal("capability_gap", trigger.event, {
				...manifest,
				code,
				filePath,
				status: "approved",
			});
			return { accepted: true, status: "approved", name: manifest.name };
		}
		const output: CapabilityOutput = { ...manifest, code, fingerprint, status: "pending" };
		const stash = await this.processor.submitAgentProposal("capability_gap", trigger.event, output);
		// Record dedup state only once the proposal is durably queued; a stash
		// miss must not suppress a later identical proposal.
		if (stash.stashed) this._rememberCapability(fingerprint, proposedKind, description);
		return { accepted: true, status: "pending", name: manifest.name };
	}

	/** Record capability dedup state with the bounded-eviction discipline of the legacy learner. */
	private _rememberCapability(fingerprint: string, kind: "tool" | "mcp" | undefined, description: string): void {
		this._seenCapabilityFingerprints.add(fingerprint);
		evictOldest(this._seenCapabilityFingerprints);
		this._seenCapabilityRequests.set(fingerprint, { kind, description });
		if (this._seenCapabilityRequests.size > MAX_SEEN_FINGERPRINTS) {
			const oldest = this._seenCapabilityRequests.keys().next().value;
			if (oldest !== undefined) this._seenCapabilityRequests.delete(oldest);
		}
	}

	private _requireRunner(): LearnerAgentRunner {
		if (!this._runner) throw new Error("LearnerAgentBridge has no runner attached");
		return this._runner;
	}

	/**
	 * A submission is live only while the run that issued it is still active.
	 * Absent context (legacy/direct callers) is always live. Stale submissions
	 * are dropped with a diagnostic, never thrown.
	 */
	private _isLiveRun(run: LearnerRunContext | undefined): boolean {
		if (!run || run.isCurrent()) return true;
		this._reportDiagnostic("Learner proposal dropped: the issuing run ended before submission completed.");
		return false;
	}

	private _reportDiagnostic(message: string, error?: unknown): void {
		try {
			void Promise.resolve(this.onDiagnostic?.(message, error)).catch(() => {});
		} catch {
			// Diagnostics are observational.
		}
	}
}

/** Same fingerprint as CapabilityGapLearner.handle: `${kind ?? "any"}:${description}`. */
function capabilityFingerprint(proposedKind: "tool" | "mcp" | undefined, description: string): string {
	return `${proposedKind ?? "any"}:${description}`;
}

function pickRequiredContracts(
	fromProposal: readonly RequiredCapabilityContract[] | undefined,
	fromEvent: readonly RequiredCapabilityContract[] | undefined,
): readonly RequiredCapabilityContract[] | undefined {
	if (fromProposal && fromProposal.length > 0) return fromProposal;
	return fromEvent && fromEvent.length > 0 ? fromEvent : undefined;
}

/** Set iteration order is insertion order: evict the oldest entry. */
function evictOldest(set: Set<string>): void {
	if (set.size <= MAX_SEEN_FINGERPRINTS) return;
	const oldest = set.keys().next().value;
	if (oldest !== undefined) set.delete(oldest);
}
