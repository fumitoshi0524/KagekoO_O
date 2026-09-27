export { LearningBus } from "./bus.js";
export type { LearningBusOptions, LearningBusSubscriber } from "./bus.js";
export { LearningTriage } from "./triage.js";
export type { LearningTriageOptions, LearningTriageConfig } from "./triage.js";
export { LearningProcessor } from "./processor.js";
export type { LearningProcessorOptions, LearningOutputInfo } from "./processor.js";
export {
	LEARNING_SOURCES,
	createLearningEvent,
	createToolResultEvent,
	createFileChangeEvent,
	createUserFeedbackEvent,
	createSessionJournalEvent,
	createExternalFetchEvent,
	createPluginEvent,
	createCapabilityGapEvent,
} from "./event.js";
export type {
	LearningEvent,
	LearningEventContext,
	LearningSource,
	ToolCallLike,
	CapabilityGapPayload,
} from "./event.js";
export type {
	TriageAction,
	TriageDecision,
	TriageTarget,
	Learner,
	PendingEntry,
	JournalEventStore,
	ResolvePendingResult,
} from "./types.js";
export { ToolResultLearner } from "./learners/tool-result.js";
export { FileChangeLearner } from "./learners/file-change.js";
export { UserFeedbackLearner } from "./learners/user-feedback.js";
export { SkillLearner } from "./learners/skill.js";
export { ErrorPatternLearner } from "./learners/error-pattern.js";
export { McpLearner } from "./learners/mcp.js";
export { PluginLearner } from "./learners/plugin.js";
export { CapabilityGapLearner } from "./learners/capability-gap.js";
export { trimEventsForSynthesis, MAX_EVENTS_FOR_SYNTHESIS, MAX_TRANSCRIPT_BYTES } from "./agent/event-trim.js";
export type { TrimEventsForSynthesisOptions } from "./agent/event-trim.js";
export {
	validateSkillProposal,
	validateCapabilityProposal,
	isSimilarToExistingSkills,
	DEFAULT_SKILL_SIMILARITY_THRESHOLD,
} from "./agent/proposals.js";
export type { CapabilityProposalInput, ExistingSkillSummary } from "./agent/proposals.js";
export { createLearnerTools } from "./agent/learner-tools.js";
export type {
	LearnerToolsDeps,
	LearnerCapabilityProposal,
	SubmitSkillProposalResult,
	SubmitCapabilityProposalResult,
} from "./agent/learner-tools.js";
export { createLearnerRunScope } from "./agent/learner-session.js";
export type { LearnerRunScope } from "./agent/learner-session.js";
export {
	LearningTriggers,
	DEFAULT_SKILL_MIN_EVENTS,
	DEFAULT_SKILL_MIN_COMPLETED_TURNS,
	DEFAULT_SKILL_SYNTHESIS_COOLDOWN_EVENTS,
} from "./agent/triggers.js";
export type { LearningTriggersOptions } from "./agent/triggers.js";
export { LearnerAgentRunner, LEARNER_SYSTEM_PROMPT, buildTriggerPrompt } from "./agent/learner-agent.js";
export type {
	LearnerTrigger,
	LearnerRunResult,
	LearnerRunContext,
	LearnerProposalSinks,
	LearnerAgentRunnerOptions,
} from "./agent/learner-agent.js";
export { LearnerAgentBridge } from "./agent/learner-bridge.js";
export type { LearnerAgentBridgeOptions } from "./agent/learner-bridge.js";
