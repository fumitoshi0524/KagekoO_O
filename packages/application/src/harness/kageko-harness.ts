import { randomUUID } from "node:crypto";
import { effectiveSessionEvents, type GoalBudgetData, type RuntimeEvent } from "@kageko/protocol";
import { FileSessionRepository, SessionPaths } from "@kageko/session-store";
import type { HarnessOptions } from "./harness-options.js";
import { composeApplication, type CompositionRoot } from "./composition-root.js";
import { projectActivities } from "../events/activity-projection.js";
import type { SessionStartOverrides } from "../sessions/runtime-session.js";
import type { ApprovalHandler } from "../interactions/approval-service.js";
import type { QuestionHandler } from "../interactions/question-service.js";
import type { AuthLoginCallbacks } from "@kageko/oauth";
import type { DiscoveredModel } from "@kageko/kosong";

/**
 * SDK-only local composition contract. It deliberately omits CompositionRoot
 * and every application implementation type.
 */
export interface LocalApplicationHandler {
	handle(method: string, payload: unknown, context: { readonly signal: AbortSignal }): Promise<unknown>;
	subscribe(sessionId: string, listener: (event: RuntimeEvent) => void): () => void;
	subscribeAll(listener: (event: RuntimeEvent) => void): () => void;
	openEventStream(
		sessionId: string,
		fromSequence: number,
		listener: (event: RuntimeEvent) => void,
		context: { readonly signal: AbortSignal },
	): Promise<{ readonly history: readonly RuntimeEvent[]; readonly dispose: () => void }>;
	close(): Promise<void>;
}

export class ApplicationHarness {
	private readonly composition: CompositionRoot;
	constructor(
		options: HarnessOptions,
		private readonly runtimeOverrides: SessionStartOverrides = {},
	) {
		this.composition = composeApplication(options);
	}
	async handle(method: string, payload: unknown = {}, context?: { readonly signal: AbortSignal }): Promise<unknown> {
		const input = payload as {
			sessionId?: string;
			turnId?: string;
			prompt?: Parameters<import("../sessions/runtime-session.js").RuntimeSession["prompt"]>[0];
			title?: string;
			archived?: boolean;
			forkId?: string;
			cwd?: string;
			scope?: "user" | "project" | "session";
			patch?: Record<string, unknown>;
			providerId?: string;
			apiKey?: string;
			command?: string;
			background?: boolean;
			taskId?: string;
			offset?: number;
			limit?: number;
			activeOnly?: boolean;
			kind?: "plugin" | "skill" | "mcp";
			cron?: string;
			recurring?: boolean;
			id?: string;
			requestId?: string;
			decision?: "once" | "session" | "deny";
			feedback?: string;
			answer?: string | readonly string[];
			text?: string;
			fact?: string;
			query?: string;
			instruction?: string;
			sequence?: number;
			timelineId?: string;
			provider?: string;
			modelName?: string;
			discoveredModel?: DiscoveredModel;
			maxContextSize?: number;
			maxOutputTokens?: number;
			reasoningConfig?: Readonly<Record<string, unknown>>;
			baseUrl?: string;
			authMode?: "api" | "oauth";
			includeProvenance?: boolean;
			includeArchived?: boolean;
			search?: string;
			promptResponses?: readonly string[];
			callbacks?: AuthLoginCallbacks;
		};
		const run = <T>(operation: () => T | Promise<T>): Promise<T> => this.runRequest(context?.signal, operation);
		const requiredSessionId = (): string => {
			if (typeof input.sessionId !== "string" || !input.sessionId.trim())
				throw new Error(`${method} requires sessionId`);
			return input.sessionId;
		};
		if (requiresSessionId(method)) requiredSessionId();
		switch (method) {
			case "sessions.list":
				return run(() =>
					this.composition.sessions.list({
						includeArchived: input.includeArchived,
						cwd: input.cwd,
						search: input.search,
					}),
				);
			case "sessions.create": {
				return run(
					async () =>
						(
							await this.composition.sessions.create({
								sessionId: input.sessionId ?? randomUUID(),
								cwd: input.cwd ?? this.composition.cwd,
								title: input.title,
							})
						).summary,
				);
			}
			case "sessions.resume":
				return run(async () => (await this.composition.sessions.resume(requiredSessionId())).summary);
			case "sessions.rename":
				return run(() => this.composition.sessions.rename(requiredSessionId(), input.title ?? ""));
			case "sessions.archive":
				return run(() => this.composition.sessions.archive(requiredSessionId(), input.archived ?? true));
			case "sessions.delete":
				return run(() => this.composition.sessions.delete(requiredSessionId()));
			case "sessions.fork":
				return run(async () => (await this.composition.sessions.fork(requiredSessionId(), input.forkId)).summary);
			case "sessions.snapshot": {
				return run(async () => {
					const summary = await this.composition.sessionRepository.get(requiredSessionId());
					if (!summary) throw new Error(`Unknown session: ${input.sessionId}`);
					const snapshot = this.composition.sessions.activeSnapshot(requiredSessionId()) ?? {
						sessionId: summary.sessionId,
						status: "ready",
						queuedPrompts: 0,
					};
					const status = this.composition.sessionDisplayStatus(requiredSessionId()) ?? snapshot.status;
					return { ...summary, ...snapshot, status };
				});
			}
			case "sessions.prompt": {
				if (!input.prompt || typeof input.prompt !== "object") throw new Error("sessions.prompt requires a prompt");
				const prompt = input.prompt;
				return run(async () => {
					await this.composition.ensureAgentRuntime(requiredSessionId(), this.runtimeOverrides);
					return this.composition.startPrompt(requiredSessionId(), {
						...prompt,
						turnId: prompt.turnId ?? randomUUID(),
					});
				});
			}
			case "sessions.close":
				return run(() => this.composition.sessions.close(requiredSessionId()));
			case "sessions.cancel":
				return run(() => this.composition.cancelPrompt(requiredSessionId(), input.turnId));
			case "sessions.shell": {
				if (!input.command?.trim()) throw new Error("Shell command is required");
				return run(() =>
					this.composition.runShellCommand(requiredSessionId(), input.command!, input.background === true),
				);
			}
			case "activities.list":
				return run(async () => {
					const summaries = await this.composition.sessions.list();
					const target = input.sessionId
						? summaries.filter((summary) => summary.sessionId === input.sessionId)
						: summaries;
					const activities = (
						await Promise.all(
							target.map(async (summary) =>
								projectActivities(
									effectiveSessionEvents(await this.composition.sessionRepository.read(summary.sessionId)),
								),
							),
						)
					).flat();
					return input.activeOnly
						? activities.filter((activity) => activity.status === "running" || activity.status === "queued")
						: activities;
				});
			case "activities.output":
				return run(() =>
					this.composition.readTaskOutput(requiredSessionId(), input.taskId!, input.offset, input.limit),
				);
			case "activities.stop":
				return run(() => this.composition.stopTask(requiredSessionId(), input.taskId!));
			case "capabilities.list":
				return run(async () => {
					await this.composition.ensureAgentRuntime(requiredSessionId());
					return this.composition.capabilities.list(requiredSessionId(), input.kind);
				});
			case "capabilities.reload":
				return run(() => this.composition.capabilitiesReload(requiredSessionId()));
			case "capabilities.list-tools":
				return run(() => this.composition.capabilitiesListTools(requiredSessionId()));
			case "cron.list":
				return run(() => this.composition.listCron(requiredSessionId()));
			case "cron.create": {
				const cronPayload = payload as {
					readonly cron?: unknown;
					readonly prompt?: unknown;
					readonly recurring?: unknown;
				};
				if (typeof cronPayload.cron !== "string" || typeof cronPayload.prompt !== "string")
					throw new Error("cron and prompt are required");
				const cronExpression: string = cronPayload.cron;
				const cronPrompt: string = cronPayload.prompt;
				return run(() =>
					this.composition.createCron(requiredSessionId(), {
						cron: cronExpression,
						prompt: cronPrompt,
						recurring: cronPayload.recurring === true,
					}),
				);
			}
			case "cron.delete":
				return run(() => this.composition.deleteCron(requiredSessionId(), input.id!));
			case "memory.status":
				return run(() => this.composition.memoryStatus(requiredSessionId()));
			case "memory.query": {
				if (!input.text) throw new Error("memory.query requires text");
				return run(() => this.composition.memoryQuery(requiredSessionId(), input.text!));
			}
			case "memory.remember": {
				if (!input.fact) throw new Error("memory.remember requires fact");
				return run(() => this.composition.memoryRemember(requiredSessionId(), input.fact!, input.scope));
			}
			case "memory.recall":
				return run(() => this.composition.memoryRecall(requiredSessionId(), input.query ?? ""));
			case "memory.index":
				return run(() => this.composition.memoryIndexRepo(requiredSessionId()));
			case "memory.generate-skill":
				return run(() => this.composition.memoryGenerateSkill(requiredSessionId()));
			case "goals.get":
				return run(() => this.composition.goalGet(requiredSessionId()));
			case "goals.create": {
				const objective = (payload as { objective?: unknown }).objective;
				if (typeof objective !== "string" || !objective.trim()) throw new Error("goals.create requires an objective");
				return run(() =>
					this.composition.goalCreate(requiredSessionId(), {
						objective,
						completionCriterion: (payload as { completionCriterion?: unknown }).completionCriterion as
							string | undefined,
						budget: (payload as { budget?: unknown }).budget as GoalBudgetData | null | undefined,
					}),
				);
			}
			case "goals.update": {
				const status = (payload as { status?: unknown }).status;
				if (status !== "active" && status !== "paused" && status !== "completed" && status !== "blocked")
					throw new Error("goals.update status must be active|paused|completed|blocked");
				return run(() =>
					this.composition.goalUpdate(requiredSessionId(), {
						status,
						note: (payload as { note?: unknown }).note as string | undefined,
					}),
				);
			}
			case "sessions.compact":
				return run(() => this.composition.sessionCompact(requiredSessionId(), input.instruction));
			case "sessions.timeline":
				return run(() => this.composition.listSessionTimeline(requiredSessionId()));
			case "sessions.restore":
				return run(() => {
					if (!Number.isSafeInteger(input.sequence) || input.sequence! < 1)
						throw new Error("sessions.restore requires a positive sequence");
					return this.composition.restoreSessionTimeline(requiredSessionId(), {
						sequence: input.sequence!,
						...(input.timelineId ? { timelineId: input.timelineId } : {}),
					});
				});
			case "learning.list":
				return run(() => this.composition.learningListPending(requiredSessionId()));
			case "learning.resolve": {
				if (!input.id) throw new Error("learning.resolve requires id");
				const action = (payload as { action?: unknown }).action;
				if (action !== "approve" && action !== "reject")
					throw new Error("learning.resolve action must be approve or reject");
				return run(() => this.composition.learningResolve(requiredSessionId(), input.id!, action));
			}
			case "interactions.list":
				return run(() =>
					[
						...this.composition.approvals.listDetails(input.sessionId),
						...this.composition.questions.listDetails(input.sessionId),
					].sort((left, right) => left.createdAt - right.createdAt),
				);
			case "interactions.respond":
				return run(() => {
					if (!input.sessionId || !input.requestId) throw new Error("sessionId and requestId are required");
					const kind = (payload as { readonly kind?: unknown }).kind;
					if (kind === "approval") {
						if (input.decision !== "once" && input.decision !== "session" && input.decision !== "deny")
							throw new Error("A valid approval decision is required");
						return this.composition.approvals.respond(input.sessionId, input.requestId, input.decision, input.feedback);
					}
					if (kind === "question") {
						if (typeof input.answer !== "string" && !Array.isArray(input.answer))
							throw new Error("A question answer is required");
						return this.composition.questions.respond(input.sessionId, input.requestId, input.answer);
					}
					throw new Error("Interaction kind must be approval or question");
				});
			case "trust.inspect":
				return run(() => this.composition.workspaceTrust.inspect(this.composition.cwd));
			case "trust.grant":
				return run(() => this.composition.workspaceTrust.grant(this.composition.cwd));
			case "trust.revoke":
				return run(() => this.composition.workspaceTrust.revoke(this.composition.cwd));
			case "config.get":
				return run(() => this.composition.config.inspect());
			case "config.path": {
				const scope = input.scope ?? "project";
				if (scope !== "project" && scope !== "user") throw new Error("Config scope must be project, user or session");
				return run(() => this.composition.config.pathFor(scope));
			}
			case "config.update": {
				const scope = input.scope ?? "project";
				if (scope !== "project" && scope !== "user") throw new Error("Config scope must be project or user");
				return run(async () => {
					const patch = input.patch ?? {};
					const updated = await this.composition.config.update(patch, scope);
					if (patch["agentGraph"] !== undefined) await this.composition.rebuildAgentRuntimes();
					return updated;
				});
			}
			case "models.discover": {
				if (!input.providerId) throw new Error("models.discover requires providerId");
				return run(() =>
					this.composition.discoverModels({
						providerId: input.providerId!,
						baseUrl: input.baseUrl,
						authMode: input.authMode,
						includeProvenance: input.includeProvenance,
						signal: context?.signal,
					}),
				);
			}
			case "models.switch": {
				if (!(input.provider ?? input.providerId) || !input.modelName)
					throw new Error(
						"models.switch requires provider and modelName; context is read from model discovery or may be supplied explicitly",
					);
				const scope = input.scope ?? "project";
				if (scope !== "project" && scope !== "user" && scope !== "session")
					throw new Error("Config scope must be project, user or session");
				if (scope === "session" && !input.sessionId) throw new Error("Session model scope requires sessionId");
				return run(() =>
					this.composition.switchModel({
						provider: input.provider ?? input.providerId!,
						modelName: input.modelName!,
						discoveredModel: input.discoveredModel,
						maxContextSize: input.maxContextSize!,
						maxOutputTokens: input.maxOutputTokens,
						reasoningConfig: input.reasoningConfig,
						baseUrl: input.baseUrl,
						authMode: input.authMode,
						scope,
						sessionId: input.sessionId,
						signal: context?.signal,
					}),
				);
			}
			case "auth.status":
				return run(() => this.composition.hasCredential(input.providerId ?? "", input.authMode));
			case "auth.set": {
				if (!input.providerId || !input.apiKey) throw new Error("providerId and apiKey are required");
				return run(() => this.composition.auth.set(input.providerId!, { type: "api_key", key: input.apiKey! }));
			}
			case "auth.remove": {
				if (!input.providerId) throw new Error("providerId is required");
				return run(() => this.composition.auth.remove(input.providerId!));
			}
			case "oauth.login": {
				if (!input.providerId) throw new Error("providerId is required");
				return run(() =>
					this.composition.oauthLogin(input.providerId!, input.promptResponses, {
						...input.callbacks,
						signal: input.callbacks?.signal ?? context?.signal,
					}),
				);
			}
			case "oauth.logout": {
				if (!input.providerId) throw new Error("providerId is required");
				return run(() => this.composition.oauthLogout(input.providerId!));
			}
			case "plugins.install": {
				const source = (payload as { source?: unknown }).source;
				if (typeof source !== "string" || !source) throw new Error("Plugin source is required");
				return run(() => this.composition.installPlugin(source));
			}
			case "plugins.uninstall": {
				if (!input.id) throw new Error("plugins.uninstall requires id");
				return run(() => this.composition.pluginsUninstall(input.id!));
			}
			case "skills.remove": {
				if (!input.id) throw new Error("skills.remove requires id");
				return run(() => this.composition.skillsRemove(input.id!));
			}
			case "mcp.auth": {
				if (!input.id) throw new Error("mcp.auth requires id");
				return run(() => this.composition.mcpAuth(input.id!));
			}
			default:
				throw new Error(`Unknown application method: ${method}`);
		}
	}
	subscribe(sessionId: string, listener: (event: RuntimeEvent) => void | Promise<void>): () => void {
		return this.composition.events.subscribe(sessionId, listener).dispose;
	}
	subscribeAll(listener: (event: RuntimeEvent) => void | Promise<void>): () => void {
		return this.composition.events.subscribeAll(listener).dispose;
	}
	async openEventStream(
		sessionId: string,
		fromSequence: number,
		listener: (event: RuntimeEvent) => void,
		context?: { readonly signal: AbortSignal },
	): Promise<{ readonly history: readonly RuntimeEvent[]; readonly dispose: () => void }> {
		throwIfAborted(context?.signal);
		const stream = await this.composition.events.openStream(sessionId, fromSequence, listener);
		try {
			throwIfAborted(context?.signal);
		} catch (error) {
			stream.dispose();
			throw error;
		}
		return { history: stream.history, dispose: stream.dispose };
	}
	async close(): Promise<void> {
		await this.composition.close();
	}
	private async runRequest<T>(signal: AbortSignal | undefined, operation: () => T | Promise<T>): Promise<T> {
		throwIfAborted(signal);
		const result = await operation();
		throwIfAborted(signal);
		return result;
	}
}

function throwIfAborted(signal: AbortSignal | undefined): void {
	if (!signal?.aborted) return;
	throw signal.reason instanceof Error ? signal.reason : new Error("Application request was aborted");
}

function requiresSessionId(method: string): boolean {
	return method.startsWith("sessions.")
		? method !== "sessions.list" && method !== "sessions.create"
		: method.startsWith("goals.") ||
				method.startsWith("cron.") ||
				method.startsWith("memory.") ||
				method.startsWith("learning.") ||
				method.startsWith("capabilities.") ||
				method === "activities.output" ||
				method === "activities.stop";
}

export interface LocalHarnessOptions {
	readonly cwd?: string;
	readonly provider?: string;
	readonly model?: string;
	readonly apiKey?: string;
	readonly permission?: "manual" | "workspace" | "unrestricted";
	readonly interaction?: "interactive" | "unattended";
	readonly approvalHandler?: ApprovalHandler;
	readonly questionHandler?: QuestionHandler;
	readonly onDiagnostic?: (diagnostic: {
		code:
			| "event.delivery_failed"
			| "interaction.status_failed"
			| "cron.restore_skipped"
			| "event.forward_failed"
			| "learning"
			| "core.diagnostic";
		message: string;
		error?: unknown;
		sessionId?: string;
		eventType?: string;
	}) => void | Promise<void>;
}

/** Application-owned in-process composition used by the node-sdk local client. */
export function createLocalHarness(options: LocalHarnessOptions = {}): LocalApplicationHandler {
	const cwd = options.cwd ?? process.cwd();
	const model = {
		...(options.provider ? { provider: options.provider } : {}),
		...(options.model ? { modelName: options.model } : {}),
		...(options.apiKey ? { apiKey: options.apiKey } : {}),
	};
	return new ApplicationHarness(
		{
			sessionRepository: new FileSessionRepository(SessionPaths.sessionsRoot(cwd)),
			cwd,
			approvalHandler: options.approvalHandler,
			questionHandler: options.questionHandler,
			onDiagnostic: options.onDiagnostic,
		},
		{
			permission: options.permission,
			interaction: options.interaction,
			model: Object.keys(model).length ? model : undefined,
		},
	);
}
