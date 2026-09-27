import {
	createSkillTool,
	type LoadedSkill as Skill,
	type SkillTool,
} from "../../../capabilities/skills/skill-loader.js";
import { noAccess } from "../../../tools/accesses.js";
import { LearningTriage } from "../triage.js";
import type { SkillSynthesizer } from "../../skill-synthesizer.js";
import type { SessionEvent, SynthesizedSkill } from "../../types.js";
import type { LearningEvent } from "../event.js";
import type { Learner, JournalEventStore } from "../types.js";
import type { ToolRegistrationOptions } from "../../../tools/types.js";
import { trimEventsForSynthesis } from "../agent/event-trim.js";
import { DEFAULT_SKILL_SIMILARITY_THRESHOLD, isSimilarToExistingSkills } from "../agent/proposals.js";

const DEFAULT_SYNTHESIS_COOLDOWN_EVENTS = 5;
const DEFAULT_MIN_COMPLETED_TURNS = 3;
const DEFAULT_SIMILARITY_THRESHOLD = DEFAULT_SKILL_SIMILARITY_THRESHOLD;
/** Bound the dedupe set; oldest fingerprints are evicted past this size. */
const MAX_SEEN_FINGERPRINTS = 500;

export interface SkillRegistryLike {
	list(): Skill[];
	registerSkill(filePath: string, source: string): Promise<Skill | undefined>;
}

export interface ToolRegistryLike {
	register(tool: SkillTool, options: ToolRegistrationOptions): string;
}

export interface SkillLearnerOptions {
	synthesizer?: SkillSynthesizer;
	recordStore?: JournalEventStore;
	skillRegistry?: SkillRegistryLike;
	toolRegistry?: ToolRegistryLike;
	cwd?: string;
	autoApprove?: boolean;
	minEvents?: number;
	similarityThreshold?: number;
	/**
	 * Minimum number of handled events between synthesis attempts. Each attempt
	 * loads the whole journal and calls the LLM, so bursts of eligible events
	 * (e.g. several completed goals in one session) must not each trigger one.
	 * Counted in events (deterministic, time-free). Default: 5.
	 */
	synthesisCooldownEvents?: number;
	/** Do not synthesize a reusable workflow from a single short interaction. */
	minCompletedTurns?: number;
}

export interface SkillOutput extends SynthesizedSkill {
	fingerprint?: string;
	filePath?: string;
	status?: "approved" | "pending";
	/** Durable completed-turn watermark used to preserve cooldown across CLI resumes. */
	learnedThroughTurns?: number;
}

/**
 * Learns reusable skills from completed goals or valuable turns.
 *
 * Synthesizes a SKILL.md from the current session record, checks for
 * similarity with existing skills, and either hot-loads the skill or
 * queues it as pending for user approval.
 */
export class SkillLearner implements Learner {
	private readonly synthesizer?: SkillSynthesizer;
	private readonly recordStore?: JournalEventStore;
	private readonly skillRegistry?: SkillRegistryLike;
	private readonly toolRegistry?: ToolRegistryLike;
	readonly cwd?: string;
	readonly autoApprove: boolean;
	readonly minEvents: number;
	readonly similarityThreshold: number;
	readonly synthesisCooldownEvents: number;
	readonly minCompletedTurns: number;
	private _seenFingerprints = new Set<string>();
	private _eventsSinceSynthesisAttempt: number;

	constructor({
		synthesizer,
		recordStore,
		skillRegistry,
		toolRegistry,
		cwd,
		autoApprove = false,
		minEvents = 3,
		similarityThreshold = DEFAULT_SIMILARITY_THRESHOLD,
		synthesisCooldownEvents = DEFAULT_SYNTHESIS_COOLDOWN_EVENTS,
		minCompletedTurns = DEFAULT_MIN_COMPLETED_TURNS,
	}: SkillLearnerOptions) {
		this.synthesizer = synthesizer;
		this.recordStore = recordStore;
		this.skillRegistry = skillRegistry;
		this.toolRegistry = toolRegistry;
		this.cwd = cwd;
		this.autoApprove = autoApprove;
		this.minEvents = minEvents;
		this.similarityThreshold = similarityThreshold;
		// Malformed config (NaN/Infinity) must not silently disable the cooldown.
		this.synthesisCooldownEvents = Number.isFinite(synthesisCooldownEvents)
			? Math.max(0, Math.floor(synthesisCooldownEvents))
			: DEFAULT_SYNTHESIS_COOLDOWN_EVENTS;
		this.minCompletedTurns = Number.isFinite(minCompletedTurns)
			? Math.max(1, Math.floor(minCompletedTurns))
			: DEFAULT_MIN_COMPLETED_TURNS;
		// Start cooled-in so the first eligible event may attempt synthesis.
		this._eventsSinceSynthesisAttempt = this.synthesisCooldownEvents;
	}

	async handle(event: LearningEvent): Promise<SkillOutput | undefined> {
		if (!this.synthesizer || !this.recordStore) return undefined;

		// Cooldown BEFORE the journal load: the load + LLM call are the
		// expensive parts and must not run per event.
		this._eventsSinceSynthesisAttempt += 1;
		if (this._eventsSinceSynthesisAttempt <= this.synthesisCooldownEvents) return undefined;
		this._eventsSinceSynthesisAttempt = 0;

		const events = await this.recordStore.load();
		if (events.length < this.minEvents) return undefined;
		// DurableEvent is a superset of SessionEvent at runtime; downstream helpers
		// only read fields common to both types.
		const sessionEvents = events as SessionEvent[];
		// Eligibility describes the durable session, not the bounded model prompt.
		// Counting completed turns after truncation prevents long, tool-heavy
		// workflows from ever reaching the threshold: the earlier turn.end events
		// disappear precisely because those turns contained useful work.
		if (!this._hasEnoughValue(event, sessionEvents)) return undefined;
		const completedTurns = sessionEvents.filter((candidate) => candidate.type === "turn.end").length;
		if (this._isWithinDurableCooldown(completedTurns)) return undefined;
		const cappedEvents = trimEventsForSynthesis(sessionEvents, { minEvents: this.minEvents });

		const skill = await this.synthesizer.synthesize(cappedEvents);
		if (!skill) return undefined;

		const fingerprint = LearningTriage.fingerprint(skill.instructions);
		if (this._seenFingerprints.has(fingerprint)) return undefined;

		if (await this._isSimilarToExisting(skill)) return undefined;

		this._rememberFingerprint(fingerprint);

		if (this.autoApprove) {
			const filePath = await this.synthesizer.writeSkill({ ...skill, learnedThroughTurns: completedTurns });
			await this._loadSkill(filePath);
			return { ...skill, filePath, fingerprint, status: "approved", learnedThroughTurns: completedTurns };
		}

		return { ...skill, fingerprint, status: "pending", learnedThroughTurns: completedTurns };
	}

	async approve(skillOutput: unknown): Promise<{ name: string; filePath: string }> {
		if (!this.synthesizer) {
			throw new Error("Cannot approve skill: no synthesizer configured.");
		}
		const o = skillOutput as SkillOutput | undefined;
		if (!o || !o.name || !o.instructions) {
			throw new Error("Invalid skill output");
		}
		const skill: SynthesizedSkill = {
			name: o.name,
			description: o.description,
			instructions: o.instructions,
		};
		const filePath = await this.synthesizer.writeSkill({
			...skill,
			learnedThroughTurns: o.learnedThroughTurns,
		});
		await this._loadSkill(filePath);
		return { name: skill.name, filePath };
	}

	reject(skillOutput: unknown): void {
		// A rejected proposal must not suppress an identical future one.
		const fingerprint = (skillOutput as SkillOutput | undefined)?.fingerprint;
		if (fingerprint) this._seenFingerprints.delete(fingerprint);
	}

	private _rememberFingerprint(value: string): void {
		this._seenFingerprints.add(value);
		if (this._seenFingerprints.size > MAX_SEEN_FINGERPRINTS) {
			// Set iteration order is insertion order: evict the oldest entry.
			const oldest = this._seenFingerprints.keys().next().value;
			if (oldest !== undefined) this._seenFingerprints.delete(oldest);
		}
	}

	private _hasEnoughValue(event: LearningEvent, events: SessionEvent[]): boolean {
		if (event.source !== "session_record") return true;
		const completedTurns = events.filter((candidate) => candidate.type === "turn.end").length;
		if (completedTurns < this.minCompletedTurns) return false;
		const toolCalls = events.filter((e) => e.type === "tool.call").length;
		if (toolCalls === 0) return false;
		return true;
	}

	private async _isSimilarToExisting(skill: SynthesizedSkill): Promise<boolean> {
		if (!this.skillRegistry) return false;
		return isSimilarToExistingSkills(skill, this.skillRegistry.list(), this.similarityThreshold);
	}

	private _isWithinDurableCooldown(completedTurns: number): boolean {
		if (!this.skillRegistry) return false;
		const learnedThrough = this.skillRegistry
			.list()
			.filter((skill) => skill.source === "auto")
			.map((skill) => skill.metadata?.learnedThroughTurns)
			.filter((value): value is number => value !== undefined);
		if (learnedThrough.length === 0) return false;
		return completedTurns - Math.max(...learnedThrough) <= this.synthesisCooldownEvents;
	}

	private async _loadSkill(filePath: string): Promise<Skill | undefined> {
		if (!this.skillRegistry) return undefined;
		const skill = await this.skillRegistry.registerSkill(filePath, "auto");
		if (!skill) throw new Error(`Generated skill failed runtime loading: ${filePath}`);
		if (skill && this.toolRegistry) {
			this.toolRegistry.register(createSkillTool(skill), {
				origin: "skill",
				ownerId: skill.source,
				accesses: noAccess(),
			});
		}
		return skill;
	}
}
