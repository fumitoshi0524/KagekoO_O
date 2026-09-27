import type { Transport, TransportRequestOptions } from "../transport/transport.js";
import type { CreateSessionInput, SessionListQuery, SessionSummary } from "../types/sessions.js";
import type { Configuration, ConfigurationPatch, ConfigurationScope } from "../types/configuration.js";
import type { ActivitySummary, CapabilitySummary, CronSummary, McpAuthResult } from "../types/tasks.js";
import type { MemoryStatus } from "../types/memory.js";
import type { WorkspaceTrustStatus } from "../types/trust.js";
import type {
	DiscoveredModel,
	ModelRoute,
	ModelSwitchInput,
	OAuthLoginCallbacks,
	OAuthLoginResult,
} from "../types/models.js";
import type { Event } from "../types/events.js";
import type { ApprovalDecision, PendingInteraction, QuestionAnswer } from "../types/approvals.js";
import { createSessionClient, SessionClient } from "../session.js";
const KAGEKO_CLIENT_TOKEN: unique symbol = Symbol("KagekoClient.internal");
export class KagekoClient {
	constructor(
		private readonly transport: Transport,
		token: typeof KAGEKO_CLIENT_TOKEN,
	) {
		if (token !== KAGEKO_CLIENT_TOKEN) throw new Error("KagekoClient must be created by KagekoHarness");
	}
	listSessions(query: SessionListQuery = {}, options?: TransportRequestOptions): Promise<readonly SessionSummary[]> {
		return this.transport.request("sessions.list", query, options);
	}
	resumeSession(sessionId: string, options?: TransportRequestOptions): Promise<SessionSummary> {
		return this.transport.request("sessions.resume", { sessionId }, options);
	}
	async createSession(input: CreateSessionInput, options?: TransportRequestOptions): Promise<SessionClient> {
		const summary = await this.transport.request("sessions.create", input, options);
		return this.session(summary.sessionId);
	}
	/** Opens an SDK session handle without exposing the underlying transport. */
	session(sessionId: string): SessionClient {
		return createSessionClient(this.transport, sessionId);
	}
	renameSession(sessionId: string, title: string, options?: TransportRequestOptions): Promise<void> {
		return this.transport.request("sessions.rename", { sessionId, title }, options);
	}
	archiveSession(sessionId: string, archived = true, options?: TransportRequestOptions): Promise<void> {
		return this.transport.request("sessions.archive", { sessionId, archived }, options);
	}
	deleteSession(sessionId: string, options?: TransportRequestOptions): Promise<void> {
		return this.transport.request("sessions.delete", { sessionId }, options);
	}
	async forkSession(sessionId: string, forkId?: string, options?: TransportRequestOptions): Promise<SessionClient> {
		const summary = await this.transport.request("sessions.fork", { sessionId, forkId }, options);
		return this.session(summary.sessionId);
	}
	getConfiguration(options?: TransportRequestOptions): Promise<Configuration> {
		return this.transport.request("config.get", options ?? {});
	}
	configurationPath(scope: ConfigurationScope = "project", options: TransportRequestOptions = {}): Promise<string> {
		return this.transport.request("config.path", { scope }, options);
	}
	updateConfiguration(
		patch: ConfigurationPatch,
		scope?: ConfigurationScope,
		options?: TransportRequestOptions,
	): Promise<Configuration> {
		return this.transport.request("config.update", { patch, scope: scope ?? "project" }, options ?? {});
	}
	discoverModels(
		providerId: string,
		options: {
			readonly baseUrl?: string;
			readonly authMode?: "api" | "oauth";
			readonly includeProvenance?: boolean;
			readonly signal?: AbortSignal;
		} = {},
	): Promise<readonly DiscoveredModel[]> {
		const { signal, ...payload } = options;
		return this.transport.request("models.discover", { providerId, ...payload }, { signal });
	}
	switchModel(input: ModelSwitchInput, options?: TransportRequestOptions): Promise<ModelRoute> {
		return this.transport.request("models.switch", input, options ?? {});
	}
	hasCredential(providerId: string, authMode?: "api" | "oauth", options?: TransportRequestOptions): Promise<boolean> {
		return this.transport.request("auth.status", { providerId, authMode }, options ?? {});
	}
	setApiKey(providerId: string, apiKey: string, options?: TransportRequestOptions): Promise<void> {
		return this.transport.request("auth.set", { providerId, apiKey }, options ?? {});
	}
	removeCredential(providerId: string, options?: TransportRequestOptions): Promise<void> {
		return this.transport.request("auth.remove", { providerId }, options ?? {});
	}
	loginOAuth(
		providerId: string,
		promptResponses?: readonly string[],
		callbacks?: OAuthLoginCallbacks,
		options?: TransportRequestOptions,
	): Promise<OAuthLoginResult> {
		return this.transport.request("oauth.login", { providerId, promptResponses, callbacks }, options ?? {});
	}
	logoutOAuth(providerId: string, options?: TransportRequestOptions): Promise<void> {
		return this.transport.request("oauth.logout", { providerId }, options ?? {});
	}
	installPlugin(source: string, options?: TransportRequestOptions): Promise<string> {
		return this.transport.request("plugins.install", { source }, options ?? {});
	}
	inspectWorkspaceTrust(options?: TransportRequestOptions): Promise<WorkspaceTrustStatus> {
		return this.transport.request("trust.inspect", options ?? {});
	}
	grantWorkspaceTrust(options?: TransportRequestOptions): Promise<WorkspaceTrustStatus> {
		return this.transport.request("trust.grant", options ?? {});
	}
	revokeWorkspaceTrust(options?: TransportRequestOptions): Promise<void> {
		return this.transport.request("trust.revoke", options ?? {});
	}
	listActivities(
		input: { readonly sessionId?: string; readonly activeOnly?: boolean } = {},
		options: TransportRequestOptions = {},
	): Promise<readonly ActivitySummary[]> {
		return this.transport.request("activities.list", input, options);
	}
	watchActivities(listener: (event: Event) => void): () => void {
		return this.transport.subscribeAll(listener);
	}
	listCapabilities(
		sessionId: string,
		kind?: "plugin" | "skill" | "mcp",
		options: TransportRequestOptions = {},
	): Promise<readonly CapabilitySummary[]> {
		return this.transport.request("capabilities.list", { sessionId, kind }, options);
	}
	reloadCapabilities(sessionId: string, options: TransportRequestOptions = {}): Promise<void> {
		return this.transport.request("capabilities.reload", { sessionId }, options);
	}
	listTools(
		sessionId: string,
		options: TransportRequestOptions = {},
	): Promise<
		readonly { readonly name: string; readonly provenance: { readonly kind: string; readonly ownerId: string } }[]
	> {
		return this.transport.request("capabilities.list-tools", { sessionId }, options);
	}
	uninstallPlugin(pluginId: string, options: TransportRequestOptions = {}): Promise<void> {
		return this.transport.request("plugins.uninstall", { id: pluginId }, options);
	}
	removeSkill(name: string, options: TransportRequestOptions = {}): Promise<void> {
		return this.transport.request("skills.remove", { id: name }, options);
	}
	authenticateMcpServer(serverName: string, options: TransportRequestOptions = {}): Promise<McpAuthResult> {
		return this.transport.request("mcp.auth", { id: serverName }, options);
	}
	listCron(sessionId: string, options: TransportRequestOptions = {}): Promise<readonly CronSummary[]> {
		return this.transport.request("cron.list", { sessionId }, options);
	}
	createCron(
		sessionId: string,
		input: { readonly cron: string; readonly prompt: string; readonly recurring?: boolean },
		options?: TransportRequestOptions,
	): Promise<{
		readonly id: string;
		readonly cron: string;
		readonly humanSchedule: string;
		readonly recurring: boolean;
		readonly nextFireAt: string | null;
	}> {
		return this.transport.request("cron.create", { sessionId, ...input }, options);
	}
	deleteCron(sessionId: string, id: string, options?: TransportRequestOptions): Promise<boolean> {
		return this.transport.request("cron.delete", { sessionId, id }, options);
	}
	memoryStatus(sessionId: string, options?: TransportRequestOptions): Promise<MemoryStatus> {
		return this.transport.request("memory.status", { sessionId }, options);
	}
	queryMemory(sessionId: string, text: string, options?: TransportRequestOptions): Promise<unknown> {
		return this.transport.request("memory.query", { sessionId, text }, options);
	}
	rememberFact(
		sessionId: string,
		fact: string,
		scope?: string,
		options?: TransportRequestOptions,
	): Promise<unknown> {
		return this.transport.request("memory.remember", { sessionId, fact, scope }, options);
	}
	recallProfile(
		sessionId: string,
		query?: string,
		options?: TransportRequestOptions,
	): Promise<readonly unknown[]> {
		return this.transport.request("memory.recall", { sessionId, query }, options);
	}
	indexRepository(sessionId: string, options?: TransportRequestOptions): Promise<unknown> {
		return this.transport.request("memory.index", { sessionId }, options);
	}
	generateSessionSkill(sessionId: string, options?: TransportRequestOptions): Promise<unknown> {
		return this.transport.request("memory.generate-skill", { sessionId }, options);
	}
	listLearningPending(sessionId: string, options: TransportRequestOptions = {}): Promise<readonly unknown[]> {
		return this.transport.request("learning.list", { sessionId }, options);
	}
	resolveLearning(
		sessionId: string,
		eventId: string,
		action: "approve" | "reject",
		options?: TransportRequestOptions,
	): Promise<unknown> {
		return this.transport.request("learning.resolve", { sessionId, id: eventId, action }, options);
	}
	listPendingInteractions(sessionId?: string): Promise<readonly PendingInteraction[]> {
		return this.transport.request("interactions.list", sessionId === undefined ? {} : { sessionId });
	}
	respondToInteraction(input: {
		readonly sessionId: string;
		readonly requestId: string;
		readonly kind: "approval";
		readonly decision: ApprovalDecision;
		readonly feedback?: string;
	}): Promise<boolean>;
	respondToInteraction(input: {
		readonly sessionId: string;
		readonly requestId: string;
		readonly kind: "question";
		readonly answer: QuestionAnswer;
	}): Promise<boolean>;
	respondToInteraction(input: {
		readonly sessionId: string;
		readonly requestId: string;
		readonly kind: "approval" | "question";
		readonly decision?: ApprovalDecision;
		readonly answer?: QuestionAnswer;
		readonly feedback?: string;
	}): Promise<boolean> {
		return this.transport.request("interactions.respond", input);
	}
	async close(): Promise<void> {
		await this.transport.close();
	}
}

/** @internal SDK construction path; callers enter through KagekoHarness. */
export function createKagekoClient(transport: Transport): KagekoClient {
	return new KagekoClient(transport, KAGEKO_CLIENT_TOKEN);
}
