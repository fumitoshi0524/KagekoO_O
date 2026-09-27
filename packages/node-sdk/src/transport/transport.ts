import type { Event } from "../types/events.js";
import type { Configuration, ConfigurationPatch, ConfigurationScope } from "../types/configuration.js";
import type { PromptInput } from "../types/prompts.js";
import type {
	CreateSessionInput,
	SessionListQuery,
	SessionRestoreResult,
	SessionSnapshot,
	SessionSummary,
	SessionTimelineEntry,
} from "../types/sessions.js";
import type {
	ActivityOutputChunk,
	ActivitySummary,
	CapabilitySummary,
	CronSummary,
	McpAuthResult,
} from "../types/tasks.js";
import type { GoalBudgetData } from "@kageko/protocol";
import type { ApprovalDecision, PendingInteraction, QuestionAnswer } from "../types/approvals.js";
import type { MemoryStatus } from "../types/memory.js";
import type { WorkspaceTrustStatus } from "../types/trust.js";
import type {
	DiscoveredModel,
	ModelRoute,
	ModelSwitchInput,
	OAuthLoginCallbacks,
	OAuthLoginResult,
} from "../types/models.js";

/**
 * The SDK's complete in-process RPC contract. This is the single typed bridge
 * between the public client methods and an application host; method strings
 * never cross that boundary with an `unknown` payload any more.
 */
export interface ApplicationRequestMap {
	"sessions.list": { readonly input: SessionListQuery; readonly output: readonly SessionSummary[] };
	"sessions.create": { readonly input: CreateSessionInput; readonly output: SessionSummary };
	"sessions.resume": { readonly input: { readonly sessionId: string }; readonly output: SessionSummary };
	"sessions.rename": { readonly input: { readonly sessionId: string; readonly title: string }; readonly output: void };
	"sessions.archive": {
		readonly input: { readonly sessionId: string; readonly archived: boolean };
		readonly output: void;
	};
	"sessions.delete": { readonly input: { readonly sessionId: string }; readonly output: void };
	"sessions.fork": {
		readonly input: { readonly sessionId: string; readonly forkId?: string };
		readonly output: SessionSummary;
	};
	"sessions.snapshot": { readonly input: { readonly sessionId: string }; readonly output: SessionSnapshot };
	"sessions.prompt": {
		readonly input: { readonly sessionId: string; readonly prompt: PromptInput };
		readonly output: { readonly turnId: string };
	};
	"sessions.close": { readonly input: { readonly sessionId: string }; readonly output: void };
	"sessions.cancel": {
		readonly input: { readonly sessionId: string; readonly turnId?: string };
		readonly output: void;
	};
	"sessions.compact": {
		readonly input: { readonly sessionId: string; readonly instruction?: string };
		readonly output: unknown;
	};
	"sessions.timeline": {
		readonly input: { readonly sessionId: string };
		readonly output: readonly SessionTimelineEntry[];
	};
	"sessions.restore": {
		readonly input: { readonly sessionId: string; readonly sequence: number; readonly timelineId?: string };
		readonly output: SessionRestoreResult;
	};
	"goals.get": { readonly input: { readonly sessionId: string }; readonly output: unknown };
	"goals.create": {
		readonly input: {
			readonly sessionId: string;
			readonly objective: string;
			readonly completionCriterion?: string;
			readonly budget?: GoalBudgetData | null;
		};
		readonly output: unknown;
	};
	"goals.update": {
		readonly input: {
			readonly sessionId: string;
			readonly status: "active" | "paused" | "completed" | "blocked";
			readonly note?: string;
		};
		readonly output: unknown;
	};
	"sessions.shell": {
		readonly input: { readonly sessionId: string; readonly command: string; readonly background?: boolean };
		readonly output: { readonly taskId: string; readonly status: string };
	};
	"activities.list": {
		readonly input: { readonly sessionId?: string; readonly activeOnly?: boolean };
		readonly output: readonly ActivitySummary[];
	};
	"activities.output": {
		readonly input: {
			readonly sessionId: string;
			readonly taskId: string;
			readonly offset?: number;
			readonly limit?: number;
		};
		readonly output: ActivityOutputChunk;
	};
	"activities.stop": { readonly input: { readonly sessionId: string; readonly taskId: string }; readonly output: void };
	"capabilities.list": {
		readonly input: { readonly sessionId: string; readonly kind?: "plugin" | "skill" | "mcp" };
		readonly output: readonly CapabilitySummary[];
	};
	"capabilities.reload": { readonly input: { readonly sessionId: string }; readonly output: void };
	"capabilities.list-tools": {
		readonly input: { readonly sessionId: string };
		readonly output: readonly {
			readonly name: string;
			readonly provenance: { readonly kind: string; readonly ownerId: string };
		}[];
	};
	"cron.list": { readonly input: { readonly sessionId: string }; readonly output: readonly CronSummary[] };
	"cron.create": {
		readonly input: {
			readonly sessionId: string;
			readonly cron: string;
			readonly prompt: string;
			readonly recurring?: boolean;
		};
		readonly output: {
			readonly id: string;
			readonly cron: string;
			readonly humanSchedule: string;
			readonly recurring: boolean;
			readonly nextFireAt: string | null;
		};
	};
	"cron.delete": { readonly input: { readonly sessionId: string; readonly id: string }; readonly output: boolean };
	"memory.status": { readonly input: { readonly sessionId: string }; readonly output: MemoryStatus };
	"memory.query": { readonly input: { readonly sessionId: string; readonly text: string }; readonly output: unknown };
	"memory.remember": {
		readonly input: { readonly sessionId: string; readonly fact: string; readonly scope?: string };
		readonly output: unknown;
	};
	"memory.recall": {
		readonly input: { readonly sessionId: string; readonly query?: string };
		readonly output: readonly unknown[];
	};
	"memory.index": { readonly input: { readonly sessionId: string }; readonly output: unknown };
	"memory.generate-skill": { readonly input: { readonly sessionId: string }; readonly output: unknown };
	"learning.list": { readonly input: { readonly sessionId: string }; readonly output: readonly unknown[] };
	"learning.resolve": {
		readonly input: { readonly sessionId: string; readonly id: string; readonly action: "approve" | "reject" };
		readonly output: unknown;
	};
	"interactions.list": {
		readonly input: { readonly sessionId?: string };
		readonly output: readonly PendingInteraction[];
	};
	"interactions.respond": {
		readonly input: {
			readonly sessionId: string;
			readonly requestId: string;
			readonly kind: "approval" | "question";
			readonly decision?: ApprovalDecision;
			readonly answer?: QuestionAnswer;
			readonly feedback?: string;
		};
		readonly output: boolean;
	};
	"trust.inspect": { readonly input: undefined; readonly output: WorkspaceTrustStatus };
	"trust.grant": { readonly input: undefined; readonly output: WorkspaceTrustStatus };
	"trust.revoke": { readonly input: undefined; readonly output: void };
	"config.get": { readonly input: undefined; readonly output: Configuration };
	"config.path": { readonly input: { readonly scope: ConfigurationScope }; readonly output: string };
	"config.update": {
		readonly input: { readonly patch: ConfigurationPatch; readonly scope: ConfigurationScope };
		readonly output: Configuration;
	};
	"models.discover": {
		readonly input: {
			readonly providerId: string;
			readonly baseUrl?: string;
			readonly authMode?: "api" | "oauth";
			readonly includeProvenance?: boolean;
		};
		readonly output: readonly DiscoveredModel[];
	};
	"models.switch": { readonly input: ModelSwitchInput; readonly output: ModelRoute };
	"auth.status": {
		readonly input: { readonly providerId: string; readonly authMode?: "api" | "oauth" };
		readonly output: boolean;
	};
	"auth.set": { readonly input: { readonly providerId: string; readonly apiKey: string }; readonly output: void };
	"auth.remove": { readonly input: { readonly providerId: string }; readonly output: void };
	"oauth.login": {
		readonly input: {
			readonly providerId: string;
			readonly promptResponses?: readonly string[];
			readonly callbacks?: OAuthLoginCallbacks;
		};
		readonly output: OAuthLoginResult;
	};
	"oauth.logout": { readonly input: { readonly providerId: string }; readonly output: void };
	"plugins.install": { readonly input: { readonly source: string }; readonly output: string };
	"plugins.uninstall": { readonly input: { readonly id: string }; readonly output: void };
	"skills.remove": { readonly input: { readonly id: string }; readonly output: void };
	"mcp.auth": { readonly input: { readonly id: string }; readonly output: McpAuthResult };
}

export type ApplicationMethod = keyof ApplicationRequestMap;
export type ApplicationRequestInput<K extends ApplicationMethod> = ApplicationRequestMap[K]["input"];
export type ApplicationRequestOutput<K extends ApplicationMethod> = ApplicationRequestMap[K]["output"];
export type ApplicationMethodWithoutInput = {
	[K in ApplicationMethod]: ApplicationRequestInput<K> extends undefined ? K : never;
}[ApplicationMethod];
export type ApplicationMethodWithInput = Exclude<ApplicationMethod, ApplicationMethodWithoutInput>;

export interface TransportRequestOptions {
	readonly signal?: AbortSignal;
}

export interface Transport {
	request<K extends ApplicationMethodWithoutInput>(
		method: K,
		options?: TransportRequestOptions,
	): Promise<ApplicationRequestOutput<K>>;
	request<K extends ApplicationMethodWithInput>(
		method: K,
		payload: ApplicationRequestInput<K>,
		options?: TransportRequestOptions,
	): Promise<ApplicationRequestOutput<K>>;
	subscribe(sessionId: string, listener: (event: Event) => void): () => void;
	subscribeAll(listener: (event: Event) => void): () => void;
	openEventStream(
		sessionId: string,
		fromSequence: number,
		listener: (event: Event) => void,
	): Promise<{ readonly history: readonly Event[]; readonly dispose: () => void }>;
	onClose(listener: () => void): () => void;
	close(): Promise<void>;
}
