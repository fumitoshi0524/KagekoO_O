export { KagekoClient } from "./client/kageko-client.js";
export type { InProcessHandler, InProcessRequestContext } from "./transport/in-process-transport.js";
export type { Event } from "./types/events.js";
export type {
	SessionSummary,
	SessionSnapshot,
	CreateSessionInput,
	SessionListQuery,
	SessionTimelineEntry,
	SessionRestoreResult,
} from "./types/sessions.js";
export type { PromptInput, PromptPart } from "./types/prompts.js";
export type { Configuration, ConfigurationPatch, ConfigurationScope } from "./types/configuration.js";
export type {
	ApprovalRequest,
	ApprovalDecision,
	ApprovalHandler,
	QuestionRequest,
	QuestionAnswer,
	QuestionHandler,
	PendingInteraction,
} from "./types/approvals.js";
export { KagekoHarness } from "./harness.js";
export type { DiagnosticEvent, LocalHarnessOptions } from "./harness.js";
export { SessionClient } from "./session.js";
export { EventStreamOverflowError } from "./session.js";
export type { EventStreamOptions } from "./session.js";
export type {
	ActivityKind,
	ActivityStatus,
	ActivitySummary,
	ActivityOutputChunk,
	TaskSummary,
	CapabilitySummary,
	CronSummary,
	McpAuthResult,
} from "./types/tasks.js";
export type { GoalBudgetData } from "@kageko/protocol";
export type { MemoryStatus } from "./types/memory.js";
export type { WorkspaceTrustStatus } from "./types/trust.js";
export type {
	DiscoveredModel,
	ModelAuthMode,
	ModelRoute,
	ModelSwitchInput,
	OAuthLoginCallbacks,
	OAuthLoginEvent,
	OAuthPrompt,
	OAuthLoginResult,
	ModelMetadataOrigin,
	ModelMetadataProvenance,
	ModelMetadataSource,
} from "./types/models.js";
