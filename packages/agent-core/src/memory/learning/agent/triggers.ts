import type { LearningEvent } from "../event.js";
import type { JournalEventStore } from "../types.js";
import type { SkillRegistryLike } from "../learners/skill.js";
import type { SessionEvent } from "../../types.js";

export const DEFAULT_SKILL_MIN_EVENTS = 3;
export const DEFAULT_SKILL_MIN_COMPLETED_TURNS = 3;
export const DEFAULT_SKILL_SYNTHESIS_COOLDOWN_EVENTS = 5;

export interface LearningTriggersOptions {
	/** Durable session journal; the same store the legacy SkillLearner reads. */
	recordStore: JournalEventStore;
	/** Skill registry for the durable cooldown watermark (auto skills only). */
	skillRegistry?: SkillRegistryLike;
	minEvents?: number;
	minCompletedTurns?: number;
	/**
	 * Minimum number of gated events between learner runs. Mirrors
	 * `SkillLearner.synthesisCooldownEvents`: counted in events, deterministic
	 * and time-free. Default: 5.
	 */
	synthesisCooldownEvents?: number;
}

/**
 * Deterministic trigger gate for resident learner runs.
 *
 * Extracted from the `SkillLearner.handle` preamble with identical numbers and
 * semantics: the event-count cooldown (starting cooled-in so the first
 * eligible event passes), the minimum journal history, the completed-turn and
 * tool-call value checks for `session_record` events, and the durable cooldown
 * watermark via `learnedThroughTurns` on auto skills. The agent run this gate
 * admits replaces the legacy direct synthesis call; the gate itself is
 * unchanged.
 */
export class LearningTriggers {
	private readonly recordStore: JournalEventStore;
	private readonly skillRegistry?: SkillRegistryLike;
	readonly minEvents: number;
	readonly minCompletedTurns: number;
	readonly synthesisCooldownEvents: number;
	private _eventsSinceAttempt: number;

	constructor({
		recordStore,
		skillRegistry,
		minEvents = DEFAULT_SKILL_MIN_EVENTS,
		minCompletedTurns = DEFAULT_SKILL_MIN_COMPLETED_TURNS,
		synthesisCooldownEvents = DEFAULT_SKILL_SYNTHESIS_COOLDOWN_EVENTS,
	}: LearningTriggersOptions) {
		this.recordStore = recordStore;
		this.skillRegistry = skillRegistry;
		this.minEvents = minEvents;
		this.minCompletedTurns = Number.isFinite(minCompletedTurns)
			? Math.max(1, Math.floor(minCompletedTurns))
			: DEFAULT_SKILL_MIN_COMPLETED_TURNS;
		// Malformed values (NaN/Infinity) must not silently disable the cooldown.
		this.synthesisCooldownEvents = Number.isFinite(synthesisCooldownEvents)
			? Math.max(0, Math.floor(synthesisCooldownEvents))
			: DEFAULT_SKILL_SYNTHESIS_COOLDOWN_EVENTS;
		// Start cooled-in so the first eligible event may trigger a run.
		this._eventsSinceAttempt = this.synthesisCooldownEvents;
	}

	/**
	 * Skill-review gate. Consumes the cooldown counter on every call, exactly
	 * like the legacy learner, even when the later checks decline the trigger.
	 */
	async shouldTriggerSkillReview(event: LearningEvent): Promise<boolean> {
		// Cooldown BEFORE the journal load: the load is the expensive part and
		// must not run per event.
		this._eventsSinceAttempt += 1;
		if (this._eventsSinceAttempt <= this.synthesisCooldownEvents) return false;
		this._eventsSinceAttempt = 0;

		const events = await this.recordStore.load();
		if (events.length < this.minEvents) return false;
		// DurableEvent is a superset of SessionEvent at runtime; the checks only
		// read fields common to both types.
		const sessionEvents = events as SessionEvent[];
		// Eligibility describes the durable session, not the bounded prompt.
		if (!this._hasEnoughValue(event, sessionEvents)) return false;
		const completedTurns = sessionEvents.filter((candidate) => candidate.type === "turn.end").length;
		if (this._isWithinDurableCooldown(completedTurns)) return false;
		return true;
	}

	private _hasEnoughValue(event: LearningEvent, events: SessionEvent[]): boolean {
		if (event.source !== "session_record") return true;
		const completedTurns = events.filter((candidate) => candidate.type === "turn.end").length;
		if (completedTurns < this.minCompletedTurns) return false;
		const toolCalls = events.filter((candidate) => candidate.type === "tool.call").length;
		if (toolCalls === 0) return false;
		return true;
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
}
