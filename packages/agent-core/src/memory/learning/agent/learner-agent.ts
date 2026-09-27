import { randomUUID } from "node:crypto";
import { KagekoAgent } from "../../../agent/agent.js";
import type { AgentLlm } from "../../../turn/turn-runner.js";
import { ToolRegistry } from "../../../tools/registry.js";
import type { PermissionManager } from "../../../permissions/index.js";
import type { ProcessTrackerPort } from "../../../ports/process.js";
import { noopTelemetryClient, type TelemetryClient } from "../../../telemetry/index.js";
import { capDescription } from "../../capability-synthesizer.js";
import type { LearningEvent } from "../event.js";
import type { SynthesizedSkill } from "../../types.js";
import { createLearnerRunScope } from "./learner-session.js";
import {
	createLearnerTools,
	type LearnerToolsDeps,
	type LearnerCapabilityProposal,
	type SubmitCapabilityProposalResult,
	type SubmitSkillProposalResult,
} from "./learner-tools.js";

/**
 * A deterministic learning trigger. The trigger kind selects the assembled
 * prompt; the event payload is the only evidence handed to the run. User
 * prompts never reach the learner agent directly.
 */
export type LearnerTrigger =
	| { kind: "capability_gap"; event: LearningEvent }
	| { kind: "skill_review"; event: LearningEvent }
	| { kind: "error_pattern"; event: LearningEvent };

export interface LearnerRunResult {
	/** Proposals accepted by the sinks during the run (pending or approved). */
	proposals: number;
	/** A run that ends without proposing is a normal decline, not an error. */
	declined: boolean;
	/** Set when the run itself failed (provider error, timeout, abort). */
	failure?: string;
	/**
	 * Set when the run never executed (or was aborted) because the runner was
	 * closed. Cancelled runs are not failures and must not leave audit entries.
	 */
	cancelled?: boolean;
}

/**
 * Per-run generation context handed to the proposal sinks. A sink that outlives
 * its run (e.g. a synthesizer call abandoned by a timeout or runner close) must
 * check `isCurrent()` before writing anything; stale submissions are dropped.
 */
export interface LearnerRunContext {
	readonly id: string;
	/** The run's abort signal; long sink work (synthesis) should respect it. */
	readonly signal: AbortSignal;
	/** False once the issuing run has ended (completed, failed, or aborted). */
	isCurrent(): boolean;
}

/**
 * Proposal decisions live in the bridge (validation, dedup, pending queue,
 * auto-approve). The runner supplies the per-run trigger context and counts
 * accepted proposals.
 */
export interface LearnerProposalSinks {
	submitSkillProposal(
		skill: SynthesizedSkill,
		trigger: LearnerTrigger,
		run?: LearnerRunContext,
	): Promise<SubmitSkillProposalResult>;
	submitCapabilityProposal(
		input: LearnerCapabilityProposal,
		trigger: LearnerTrigger,
		run?: LearnerRunContext,
	): Promise<SubmitCapabilityProposalResult>;
}

export interface LearnerAgentRunnerOptions {
	/** The learner model route. */
	llm: AgentLlm;
	/** KagekoAgent construction deps; the learner tools never touch them. */
	kaos: unknown;
	tracker: ProcessTrackerPort;
	/**
	 * Permission manager for the learner's dedicated tool registry. The five
	 * learner tools are not user-facing, so the composition root injects a
	 * learner-scoped manager; real gating is the pending queue plus proposal
	 * validation, not runtime permission prompts.
	 */
	permission: PermissionManager;
	telemetry?: TelemetryClient;
	/** Tool deps minus the two submit sinks, which the runner wires to `sinks`. */
	learnerToolsDeps: Omit<LearnerToolsDeps, "submitSkillProposal" | "submitCapabilityProposal">;
	sinks: LearnerProposalSinks;
	systemPrompt?: string;
	/** Context budget for the learner route; forwarded to KagekoAgent compaction. */
	maxContextSize?: number;
	maxSteps?: number;
	timeoutMs?: number;
	/** Maximum triggers queued behind a running learner run; excess is dropped. */
	maxQueuedRuns?: number;
	onDiagnostic?: (message: string, error?: unknown) => void | Promise<void>;
	/**
	 * Run lifecycle hooks. The composition root uses them to drive
	 * `AgentGraph.startLearnerRun`/`finish`; agent-core stays decoupled from any
	 * specific graph instance. A hook failure degrades to a diagnostic.
	 */
	onRunStart?: (trigger: LearnerTrigger) => string | void;
	onRunEnd?: (runToken: string | void, status: "completed" | "failed", summary?: string) => void;
}

// Learning is advisory work running beside a user task. Product policy gates
// which evidence can wake it; these defaults retain sufficient room for a
// grounded offline synthesis when a high-value trigger does arrive.
export const DEFAULT_LEARNER_MAX_STEPS = 6;
export const DEFAULT_LEARNER_TIMEOUT_MS = 300_000;
export const DEFAULT_LEARNER_MAX_QUEUED_RUNS = 4;

/**
 * The resident learner as a real agent: a bounded `KagekoAgent` run against a
 * dedicated registry holding ONLY the five learner tools, journaled into an
 * ephemeral in-memory session so learner tool traffic never enters the main
 * session journal or the learning bus.
 *
 * Runs are serialized behind a promise queue; the deterministic spine
 * (triggers, pending queue, approval, publish) lives outside this class.
 */
export class LearnerAgentRunner {
	private readonly llm: AgentLlm;
	private readonly kaos: unknown;
	private readonly tracker: ProcessTrackerPort;
	private readonly permission: PermissionManager;
	private readonly telemetry: TelemetryClient;
	private readonly learnerToolsDeps: Omit<LearnerToolsDeps, "submitSkillProposal" | "submitCapabilityProposal">;
	private readonly sinks: LearnerProposalSinks;
	private readonly systemPrompt: string;
	private readonly maxContextSize?: number;
	private readonly maxSteps: number;
	private readonly timeoutMs: number;
	private readonly maxQueuedRuns: number;
	private readonly onDiagnostic?: (message: string, error?: unknown) => void | Promise<void>;
	private readonly onRunStart?: (trigger: LearnerTrigger) => string | void;
	private readonly onRunEnd?: (runToken: string | void, status: "completed" | "failed", summary?: string) => void;
	private readonly _closeError = new Error("Learner runner closed.");
	private _tail: Promise<unknown> = Promise.resolve();
	private _queued = 0;
	private _closed = false;
	/** Per-run sink context; only mutated while a run holds the queue. */
	private _currentTrigger: LearnerTrigger | undefined;
	private _currentRun: LearnerRunContext | undefined;
	private _activeAbort: AbortController | null = null;
	private _acceptedProposals = 0;

	constructor(options: LearnerAgentRunnerOptions) {
		this.llm = options.llm;
		this.kaos = options.kaos;
		this.tracker = options.tracker;
		this.permission = options.permission;
		this.telemetry = options.telemetry ?? noopTelemetryClient;
		this.learnerToolsDeps = options.learnerToolsDeps;
		this.sinks = options.sinks;
		this.systemPrompt = options.systemPrompt ?? LEARNER_SYSTEM_PROMPT;
		this.maxContextSize = options.maxContextSize;
		this.maxSteps = options.maxSteps ?? DEFAULT_LEARNER_MAX_STEPS;
		this.timeoutMs = options.timeoutMs ?? DEFAULT_LEARNER_TIMEOUT_MS;
		this.maxQueuedRuns = options.maxQueuedRuns ?? DEFAULT_LEARNER_MAX_QUEUED_RUNS;
		this.onDiagnostic = options.onDiagnostic;
		this.onRunStart = options.onRunStart;
		this.onRunEnd = options.onRunEnd;
	}

	/** Number of runs currently queued or executing. */
	get pendingRuns(): number {
		return this._queued;
	}

	/**
	 * Stop the runner: abort the in-flight run and let every queued trigger
	 * resolve as cancelled without executing. Session close calls this BEFORE
	 * draining learning work so shutdown never blocks on a 300s learner run.
	 * Idempotent; the queue chain settles on its own afterwards.
	 */
	close(): void {
		if (this._closed) return;
		this._closed = true;
		this._activeAbort?.abort(this._closeError);
	}

	/**
	 * Queue a bounded learner run for a trigger. Runs execute strictly one at a
	 * time; when the queue is full the trigger is dropped with a diagnostic and
	 * reported as a failure so the caller can keep its audit trail honest.
	 * After {@link close}, triggers resolve immediately as cancelled.
	 */
	async run(trigger: LearnerTrigger): Promise<LearnerRunResult> {
		if (this._closed) return cancelledRunResult();
		if (this._queued >= this.maxQueuedRuns) {
			const message = `Learner run queue is full (${this.maxQueuedRuns}); dropped ${trigger.kind} trigger.`;
			this._reportDiagnostic(message);
			return { proposals: 0, declined: false, failure: message };
		}
		this._queued += 1;
		const result = this._tail.then(() => (this._closed ? cancelledRunResult() : this._runNow(trigger)));
		this._tail = result.then(
			() => undefined,
			() => undefined,
		);
		try {
			return await result;
		} finally {
			this._queued -= 1;
		}
	}

	private async _runNow(trigger: LearnerTrigger): Promise<LearnerRunResult> {
		const abortController = new AbortController();
		const runId = randomUUID();
		const run: LearnerRunContext = {
			id: runId,
			signal: abortController.signal,
			isCurrent: () => this._currentRun?.id === runId && !abortController.signal.aborted,
		};
		this._currentTrigger = trigger;
		this._currentRun = run;
		this._activeAbort = abortController;
		this._acceptedProposals = 0;
		let runToken: string | void = undefined;
		try {
			runToken = this.onRunStart?.(trigger);
		} catch (error) {
			this._reportDiagnostic("Learner onRunStart hook failed.", error);
		}
		const scope = createLearnerRunScope(`learner-run-${runId}`);
		const registry = new ToolRegistry();
		for (const tool of createLearnerTools(this._toolDeps())) {
			registry.register(tool, { origin: "builtin" });
		}
		const agent = new KagekoAgent({
			llm: this.llm,
			registry,
			kaos: this.kaos,
			tracker: this.tracker,
			permission: this.permission,
			telemetry: this.telemetry,
			session: scope.session,
			systemPrompt: this.systemPrompt,
			maxContextSize: this.maxContextSize,
			maxSteps: this.maxSteps,
			recordStore: scope.recordStore,
			onDiagnostic: this.onDiagnostic,
		});
		const timeoutError = new Error(`Learner run timed out after ${this.timeoutMs} ms.`);
		const timer = setTimeout(() => abortController.abort(timeoutError), this.timeoutMs);
		let failure: string | undefined;
		let cancelled = false;
		try {
			await agent.prompt(buildTriggerPrompt(trigger), { signal: abortController.signal });
		} catch (error) {
			if (abortController.signal.aborted && abortController.signal.reason === this._closeError) {
				// Runner close: an aborted run is a cancellation, never an auditable failure.
				cancelled = true;
			} else {
				// If our own timeout fired, surface the timeout even when the turn
				// machinery wrapped the abort reason in another error.
				failure =
					abortController.signal.aborted && abortController.signal.reason === timeoutError
						? timeoutError.message
						: error instanceof Error
							? error.message
							: String(error);
			}
		} finally {
			clearTimeout(timer);
		}
		const proposals = this._acceptedProposals;
		// End the generation: any sink still in flight now observes a stale context.
		this._currentTrigger = undefined;
		this._currentRun = undefined;
		this._activeAbort = null;
		try {
			this.onRunEnd?.(
				runToken,
				failure || cancelled ? "failed" : "completed",
				failure ?? (cancelled ? this._closeError.message : `${trigger.kind}: ${proposals} proposal(s)`),
			);
		} catch (error) {
			this._reportDiagnostic("Learner onRunEnd hook failed.", error);
		}
		if (cancelled) return { proposals, declined: false, cancelled: true };
		return { proposals, declined: !failure && proposals === 0, ...(failure ? { failure } : {}) };
	}

	private _toolDeps(): LearnerToolsDeps {
		return {
			...this.learnerToolsDeps,
			submitSkillProposal: async (skill) => {
				const run = this._requireRun();
				const result = await this.sinks.submitSkillProposal(skill, this._requireTrigger(), run);
				if (result.accepted) this._acceptedProposals += 1;
				return result;
			},
			submitCapabilityProposal: async (input) => {
				const run = this._requireRun();
				const result = await this.sinks.submitCapabilityProposal(input, this._requireTrigger(), run);
				if (result.accepted) this._acceptedProposals += 1;
				return result;
			},
		};
	}

	private _requireTrigger(): LearnerTrigger {
		if (!this._currentTrigger) throw new Error("Learner proposal submitted outside a run");
		return this._currentTrigger;
	}

	private _requireRun(): LearnerRunContext {
		if (!this._currentRun) throw new Error("Learner proposal submitted outside a run");
		return this._currentRun;
	}

	private _reportDiagnostic(message: string, error?: unknown): void {
		try {
			void Promise.resolve(this.onDiagnostic?.(message, error)).catch(() => {});
		} catch {
			// Diagnostics are observational.
		}
	}
}

export const LEARNER_SYSTEM_PROMPT: string = [
	"You are Kageko's resident learner. You run in the background when the learning pipeline hands you a trigger; you never interact with the user.",
	"Inspect before proposing: ground every decision in read_recent_events, inspect_inventory, or read_error_patterns rather than in assumptions.",
	"Propose at most one capability or one skill per run. If the evidence does not justify a durable, reusable artifact, decline by ending your turn without proposing.",
	"Executable capabilities require reuse evidence (distinct future tasks plus checked alternatives); when the trigger payload carries structured requiredContracts, pass them through unchanged instead of re-deriving them.",
	"Never propose something the current inventory already covers, and never invent contracts the evidence does not contain.",
].join("\n");

function cancelledRunResult(): LearnerRunResult {
	return { proposals: 0, declined: false, cancelled: true };
}

/** Bound the serialized trigger payload in the prompt; payloads can carry full tool results. */
const MAX_TRIGGER_PAYLOAD_BYTES = 4 * 1024;

/**
 * Assemble the trigger prompt in code: trigger kind + bounded event payload
 * JSON + per-kind instruction. The payload arrives from the deterministic
 * pipeline (already redacted); it is data for inspection, never an instruction
 * source the user controls directly. Error-pattern triggers omit the raw
 * payload entirely — the instruction directs the agent to read_error_patterns.
 */
export function buildTriggerPrompt(trigger: LearnerTrigger): string {
	const parts = [`Learning trigger: ${trigger.kind}`, ""];
	if (trigger.kind !== "error_pattern") {
		let payloadJson: string;
		try {
			payloadJson = JSON.stringify(trigger.event.payload, null, 2) ?? "{}";
		} catch {
			payloadJson = "[unserializable payload]";
		}
		// capDescription is the shared UTF-8 byte cap (default 4 KiB).
		parts.push("Trigger event payload (JSON):", capDescription(payloadJson, MAX_TRIGGER_PAYLOAD_BYTES), "");
	}
	parts.push(TRIGGER_INSTRUCTIONS[trigger.kind]);
	return parts.join("\n");
}

const TRIGGER_INSTRUCTIONS: Record<LearnerTrigger["kind"], string> = {
	capability_gap:
		"A capability gap was recorded. Inspect the inventory and recent events, then either propose_capability once for the described gap — passing through the payload's description, context, proposedKind, and requiredContracts — or decline.",
	skill_review:
		"A session segment completed. Review the recent events; if they contain a reusable workflow that inspect_inventory shows no existing skill covers, propose_skill once; otherwise decline.",
	error_pattern:
		"A recurring tool error pattern was recorded. Inspect it with read_error_patterns; propose one skill or capability that prevents the pattern, or decline.",
};
