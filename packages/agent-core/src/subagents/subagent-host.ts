import { AsyncLocalStorage } from "node:async_hooks";
import { randomUUID } from "node:crypto";
import type { KaosPort } from "../ports/workspace.js";
import { KagekoAgent, type AgentSession } from "../agent/agent.js";
import { ToolRegistry } from "../tools/registry.js";
import { PermissionManager } from "../permissions/index.js";
import { PluginManager } from "../capabilities/plugins/plugin-loader.js";
import { SkillRegistry } from "../capabilities/skills/skill-loader.js";
import { PlanMode } from "../agent/plan/plan-mode.js";
import type { ProcessTrackerPort } from "../ports/process.js";
import { noopTelemetryClient, type TelemetryClient } from "../telemetry/index.js";
import {
	isLiveEventType,
	type DurableEvent,
	type DurableEventInput,
	type DurableEventType,
	type RuntimeEvent,
} from "@kageko/protocol";
import type { JournalPort as JournalWriter } from "../ports/repository.js";
import type { AgentLlm } from "../turn/turn-runner.js";
import type { McpManager } from "../capabilities/mcp/mcp-manager.js";
import type { InteractionMode, PermissionProfile } from "../permissions/types.js";
import type { AgentGraph, AgentGraphNode, AgentGraphNodeConfiguration } from "./agent-graph.js";

export interface SubagentCronScheduler {
	/** Write-only callback; child hosts may detach persistence but never invoke it. */
	onPersist?: (...args: never[]) => void | Promise<void>;
	stopAll(): Promise<void>;
}

export const DEFAULT_MAX_CONCURRENT_SUBAGENTS = 4;
export const DEFAULT_SUBAGENT_TIMEOUT_MS = 1_800_000;
const MAX_SUBAGENT_DEPTH = 4;
const MAX_RETRIES = 3;
const RETRY_BASE_DELAY_MS = 50;
const RESERVED_SYSTEM_PROFILE_IDS = new Set(["coordinator", "learner"]);

interface SubagentContextStore {
	depth: number;
	releaseForHost?: Map<SubagentHost, () => void>;
}

const subagentContext = new AsyncLocalStorage<SubagentContextStore>();

export interface SubagentProfile {
	id?: string;
	/** Short worker summary shown to the coordinator when selecting a profile. */
	description?: string;
	/** Explicit delegation guidance, following KimiCode's profile contract. */
	whenToUse?: string;
	systemPrompt?: string;
	model?: SubagentModelSpec;
	permissionProfile?: PermissionProfile;
	interactionMode?: InteractionMode;
	tools?: string[];
	maxSteps?: number;
	/** Wall-clock bound for runs of this profile; a per-call timeoutMs still wins. */
	timeoutMs?: number;
	/** Subagents are executable workers; the learner is never spawned here. */
	role?: "executor";
	[key: string]: unknown;
}
export type SubagentModelSpec = string | Record<string, unknown> | "faux";
export type SubagentLlmResolver = (
	spec: SubagentModelSpec,
	parent: AgentLlm,
	maxContextSize?: number,
) => Promise<AgentLlm> | AgentLlm;

export interface SubagentRunOptions {
	prompt: string;
	/** Optional profile with systemPrompt, model, mode, tools (allow-list), and maxSteps. */
	profile?: SubagentProfile;
	/** Return a matching prior result from the record store instead of re-running (default: false). */
	resume?: boolean;
	/** @deprecated use profile.systemPrompt. */
	systemPrompt?: string;
	/** @deprecated use profile.tools. */
	tools?: string[];
	/** @deprecated use profile.maxSteps. */
	maxSteps?: number;
	signal?: AbortSignal;
	timeoutMs?: number;
	/** Lineage supplied by the invoking turn/tool; never inferred from prompt text. */
	parentActivityId?: string;
	parentToolCallId?: string;
}

export interface SubagentResult {
	content: string;
	toolCalls: unknown[];
	events: unknown[];
	error?: unknown;
}

export interface SubagentHostSession {
	cwd: string;
	registry: ToolRegistry;
	llm?: AgentLlm;
	kaos: KaosPort;
	permission?: PermissionManager;
	planMode?: PlanMode;
	tracker?: ProcessTrackerPort;
	mcp?: McpManager;
	systemPrompt?: string;
	maxContextSize?: number;
	telemetry?: TelemetryClient;
	cron: SubagentCronScheduler;
	plugins: PluginManager;
	skills: SkillRegistry;
	subagentHost?: SubagentHost;
	recordStore?: JournalWriter;
	/** Application-owned live dispatch for child events; core never imports application. */
	onSubagentEvent?: (event: RuntimeEvent) => void | Promise<void>;
	agentGraph?: AgentGraph;
	/** Default executor route; an explicit profile.model still wins. */
	executorModel?: SubagentModelSpec;
	/** Default executor policy; a per-call profile overrides individual fields. */
	executorProfile?: SubagentProfile;
	/** Named, application-composed worker profiles addressable through profile.id. */
	subagentProfiles?: ReadonlyMap<string, SubagentProfile>;
}

/**
 * Mutable services deliberately isolated for one child run.  The host asks
 * the composition root to construct this runtime; it never reflects on a
 * parent Session constructor.
 */
export interface SubagentChildSessionOptions {
	cwd: string;
	registry: ToolRegistry;
	llm: AgentLlm;
	kaos: KaosPort;
	permission: PermissionManager;
	planMode: PlanMode;
	tracker: ProcessTrackerPort;
	mcp?: McpManager;
	systemPrompt?: string;
	maxContextSize?: number;
	telemetry: TelemetryClient;
	cron: SubagentCronScheduler;
	plugins: PluginManager;
	skills: SkillRegistry;
	subagentHost: SubagentHost;
}

export type SubagentChildSession = Omit<SubagentHostSession, "tracker" | "permission" | "telemetry"> &
	AgentSession & {
		tracker: ProcessTrackerPort;
		permission: PermissionManager;
		telemetry: TelemetryClient;
		close?(): Promise<void>;
	};

export type SubagentChildSessionFactory = (options: SubagentChildSessionOptions) => SubagentChildSession;

export interface SubagentHostOptions {
	session: SubagentHostSession;
	createChildSession: SubagentChildSessionFactory;
	resolveLlm?: SubagentLlmResolver;
	maxConcurrent?: number;
}

/**
 * Host for spawning child agents (subagents) from a parent session.
 *
 * Each subagent gets a fresh {@link KagekoAgent} that shares the parent
 * {@link SubagentHostSession} (tools, MCP, plugins, permissions, telemetry) but
 * has its own isolated context memory. Runs are limited to `maxConcurrent`
 * concurrent executions per host to avoid resource races.
 */
export class SubagentHost {
	readonly session: SubagentHostSession;
	readonly createChildSession: SubagentChildSessionFactory;
	readonly maxConcurrent: number;
	readonly semaphore: Semaphore;
	private readonly resolveLlm?: SubagentLlmResolver;
	private _running = new Map<string, Promise<SubagentResult>>();

	constructor(options: SubagentHostOptions) {
		// Fail fast: without a session (or child-session factory) the host only
		// explodes deep inside `_execute` with an opaque TypeError.
		if (!options?.session) {
			throw new TypeError("SubagentHost requires options.session");
		}
		if (typeof options.createChildSession !== "function") {
			throw new TypeError("SubagentHost requires options.createChildSession");
		}
		const { session, createChildSession, resolveLlm, maxConcurrent = DEFAULT_MAX_CONCURRENT_SUBAGENTS } = options;
		this.session = session;
		this.createChildSession = createChildSession;
		this.resolveLlm = resolveLlm;
		this.maxConcurrent = clampMaxConcurrent(maxConcurrent);
		this.semaphore = new Semaphore(this.maxConcurrent);
	}

	/**
	 * Run a single subagent task.
	 *
	 * Dedup semantics (G-m1): a second concurrent call with an identical
	 * prompt+profile shares the FIRST caller's in-flight promise. The later
	 * caller's `signal`, `timeoutMs`, and lineage are ignored — the first
	 * caller's signal governs the shared execution and both callers receive the
	 * same result object.
	 */
	async run(options: SubagentRunOptions): Promise<SubagentResult> {
		const store = subagentContext.getStore();
		const parentDepth = store?.depth ?? 0;
		const depth = parentDepth + 1;
		if (depth > MAX_SUBAGENT_DEPTH) {
			throw new Error(`Subagent recursion limit (${MAX_SUBAGENT_DEPTH}) exceeded`);
		}
		// Reuse the same host's semaphore for nested subagents so a child session
		// that receives `subagentHost: this` does not deadlock.
		const heldReleases = store?.releaseForHost ?? new Map<SubagentHost, () => void>();
		if (heldReleases.has(this)) {
			return await subagentContext.run({ depth, releaseForHost: heldReleases }, () => this._run(options));
		}
		const release = await this.semaphore.acquire();
		const childReleases = new Map(heldReleases);
		childReleases.set(this, release);
		try {
			return await subagentContext.run({ depth, releaseForHost: childReleases }, () => this._run(options));
		} finally {
			childReleases.delete(this);
			release();
		}
	}

	static get DEFAULT_TIMEOUT_MS(): number {
		return DEFAULT_SUBAGENT_TIMEOUT_MS;
	}

	private async _run({
		prompt,
		profile,
		resume = false,
		systemPrompt,
		tools,
		maxSteps,
		signal,
		timeoutMs,
		parentActivityId,
		parentToolCallId,
	}: SubagentRunOptions): Promise<SubagentResult> {
		const normalizedProfile = normalizeProfile(profile);
		// Backwards-compatible top-level options override profile values.
		const requestedProfile = {
			...normalizedProfile,
			systemPrompt: systemPrompt ?? normalizedProfile.systemPrompt,
			tools: tools ?? normalizedProfile.tools,
			maxSteps: maxSteps ?? normalizedProfile.maxSteps,
		};
		const profileId = requestedProfile.id;
		if (profileId && RESERVED_SYSTEM_PROFILE_IDS.has(profileId)) {
			throw new Error(
				`${JSON.stringify(profileId)} is a fixed Kageko system role and cannot be spawned as a subagent.`,
			);
		}
		const configuredProfile = profileId ? this.session.subagentProfiles?.get(profileId) : undefined;
		if (profileId && this.session.subagentProfiles?.size && !configuredProfile) {
			throw new Error(`Unknown subagent profile ${JSON.stringify(profileId)}.`);
		}
		// A named profile is a declared worker type, not a bag of per-call
		// overrides. This mirrors KimiCode's subagent_type contract and keeps
		// its tool and permission boundary stable. Profile-less legacy calls keep
		// the configurable default executor behavior.
		const effectiveProfile =
			configuredProfile ?? mergeSubagentProfiles(this.session.executorProfile, requestedProfile) ?? {};
		// Per-call timeout wins over the profile default, which wins over the
		// host default. The resume/dedup key is unaffected: timeout bounds a run,
		// it does not identify one.
		const effectiveTimeoutMs = timeoutMs ?? effectiveProfile.timeoutMs ?? SubagentHost.DEFAULT_TIMEOUT_MS;

		const runKey = makeRunKey(prompt, effectiveProfile);
		let promise = this._running.get(runKey);
		if (promise) {
			return promise;
		}

		promise = (async (): Promise<SubagentResult> => {
			const subagentId = randomUUID();
			if (resume === true) {
				const prior = await this._findPriorResult(prompt, effectiveProfile);
				if (prior) {
					// A resume hit is a real run from the observer's perspective:
					// register+finish a graph node and journal the same
					// started/completed pair a fresh execution would emit, so
					// dashboards and replay do not see an invisible hit (G-m9a).
					// The protocol event shapes carry no resume marker, so the hit
					// stays within the existing `subagent.started/completed` shape.
					await this._appendRecord({
						type: "subagent.started",
						meta: { activityId: subagentId, parentActivityId, parentToolCallId, actorId: subagentId },
						data: { subagentId, parentToolCallId, prompt, profile: effectiveProfile },
					});
					// The node is registered only after the started record is
					// durable (matching the fresh-run ordering); a failed
					// completed-append marks it failed instead of leaving it
					// `running` forever.
					const graphNode = this._startGraphNode(effectiveProfile);
					try {
						await this._appendRecord({
							type: "subagent.completed",
							meta: { activityId: subagentId, parentActivityId, parentToolCallId, actorId: subagentId },
							data: {
								subagentId,
								parentToolCallId,
								prompt,
								profile: effectiveProfile,
								result: capSubagentResult(prior),
							},
						});
					} catch (error) {
						if (graphNode)
							this.session.agentGraph?.finish(graphNode.id, "failed", {
								message: error instanceof Error ? error.message : String(error),
							});
						throw error;
					}
					if (graphNode) this.session.agentGraph?.finish(graphNode.id, "completed", { resumed: true });
					return prior;
				}
			}

			await this._appendRecord({
				type: "subagent.started",
				meta: { activityId: subagentId, parentActivityId, parentToolCallId, actorId: subagentId },
				data: { subagentId, parentToolCallId, prompt, profile: effectiveProfile },
			});

			try {
				const result = await this._runWithRetry({
					prompt,
					profile: effectiveProfile,
					signal,
					timeoutMs: effectiveTimeoutMs,
					subagentId,
					parentActivityId,
					parentToolCallId,
				});
				await this._appendRecord({
					type: "subagent.completed",
					meta: { activityId: subagentId, parentActivityId, parentToolCallId, actorId: subagentId },
					data: { subagentId, parentToolCallId, prompt, profile: effectiveProfile, result: capSubagentResult(result) },
				});
				return result;
			} catch (err) {
				const error = err instanceof Error ? err : new Error(String(err));
				try {
					await this._appendRecord({
						type: "subagent.failed",
						meta: { activityId: subagentId, parentActivityId, parentToolCallId, actorId: subagentId },
						data: {
							subagentId,
							prompt,
							parentToolCallId,
							profile: effectiveProfile,
							error: { name: error.name, message: error.message },
						},
					});
				} catch (journalError) {
					// A journaling failure must not mask the real execution error.
					throw new AggregateError([err, journalError], "Subagent execution and failure journaling failed");
				}
				throw err;
			}
		})();

		this._running.set(runKey, promise);
		try {
			return await promise;
		} finally {
			this._running.delete(runKey);
		}
	}

	private async _runWithRetry(options: {
		prompt: string;
		profile: SubagentProfile;
		signal?: AbortSignal;
		timeoutMs: number;
		subagentId: string;
		parentActivityId?: string;
		parentToolCallId?: string;
	}): Promise<SubagentResult> {
		const errors: unknown[] = [];
		for (let attempt = 0; attempt <= MAX_RETRIES; attempt += 1) {
			try {
				return await this._execute(options);
			} catch (err: unknown) {
				if (isAbortError(err) || isSubagentTimeout(err)) {
					throw err;
				}
				errors.push(err);
				if (attempt >= MAX_RETRIES || !this._isRetryable(err)) {
					throw err;
				}
				const delayMs = RETRY_BASE_DELAY_MS * 2 ** attempt;
				await sleep(delayMs);
			}
		}
		// Unreachable, but keeps lint happy.
		throw errors[errors.length - 1];
	}

	private async _execute({
		prompt,
		profile,
		signal,
		timeoutMs = SubagentHost.DEFAULT_TIMEOUT_MS,
		subagentId,
		parentActivityId,
		parentToolCallId,
	}: {
		prompt: string;
		profile?: SubagentProfile;
		signal?: AbortSignal;
		timeoutMs?: number;
		subagentId: string;
		parentActivityId?: string;
		parentToolCallId?: string;
	}): Promise<SubagentResult> {
		if (signal?.aborted) {
			throw signal.reason ?? new Error("subagent aborted");
		}

		const abortController = new AbortController();
		const effectiveTimeoutMs = clampTimeoutMs(timeoutMs);
		// Dedicated error type so the subagent's OWN timeout is identifiable by
		// AbortSignal.reason identity, never by message substring matching.
		const timeoutError = new SubagentTimeoutError();
		const timer = setTimeout(() => abortController.abort(timeoutError), effectiveTimeoutMs);
		const onParentAbort = () => abortController.abort(signal!.reason);
		if (signal) {
			signal.addEventListener("abort", onParentAbort, { once: true });
		}
		// The profile arrives already merged with the session executor defaults
		// (merged in `_run` before the run key / resume match are computed).

		let childSession: SubagentChildSession | undefined;
		const graphNode = this._startGraphNode(profile);
		// Live-event sink deliveries are tracked so the run only finishes after
		// every forwarded event has settled (G-m4). Each delivery handles its own
		// rejection at push time (recorded via telemetry, never propagated), so
		// these promises never reject.
		const sinkDeliveries: Promise<void>[] = [];
		let executionError: unknown;
		try {
			const llm = await this._resolveLLM(profile?.model ?? this.session.executorModel);
			if (abortController.signal.aborted) {
				throw abortController.signal.reason;
			}
			const registry = profile?.tools ? this._filterRegistry(profile.tools) : this.session.registry;

			// Run the subagent against a child session that shares the parent's
			// workspace and read-only services but has its own mutable state. This
			// prevents a subagent from adding cron jobs, invoking plugins, mutating
			// skills, changing goals, or otherwise leaking side effects back into
			// the parent.
			const parentPermission = this.session.permission;
			// The child plan mode reuses the parent session's injected plans
			// directory; agent-core never derives project directories itself.
			const childPlanMode = new PlanMode({ cwd: this.session.cwd, plansDir: this.session.planMode?.plansDir });
			const childPermission = new PermissionManager({
				profile: narrowPermissionProfile(parentPermission?.profile ?? "manual", profile?.permissionProfile),
				interaction: narrowInteractionMode(parentPermission?.interaction ?? "interactive", profile?.interactionMode),
				cwd: this.session.cwd,
				// kagekoDir only feeds safeDirs; when the parent session carries no
				// permission manager, the workspace root is the safe fallback.
				kagekoDir: parentPermission?.kagekoDir ?? this.session.cwd,
				safeDirs: parentPermission?.safeDirs ? [...parentPermission.safeDirs] : [],
				allowList: parentPermission?.allowList ? [...parentPermission.allowList] : [],
				denyList: parentPermission?.denyList ? [...parentPermission.denyList] : [],
				askList: parentPermission?.askList ? [...parentPermission.askList] : [],
				config: parentPermission?.config ? { ...parentPermission.config } : {},
				approvalHandler: parentPermission?.approvalHandler,
				planMode: childPlanMode,
			});

			childSession = this.createChildSession({
				cwd: this.session.cwd,
				registry,
				llm,
				kaos: this.session.kaos,
				permission: childPermission,
				planMode: childPlanMode,
				tracker:
					this.session.tracker?.fork() ??
					(() => {
						throw new Error("Subagent execution requires an injected process tracker");
					})(),
				mcp: this.session.mcp,
				systemPrompt: profile?.systemPrompt ?? this.session.systemPrompt,
				maxContextSize: this.session.maxContextSize,
				telemetry: noopTelemetryClient,
				cron: this.session.cron,
				// Capability registries are application-owned and shared read-only
				// with child agents; children must not create a second plugin/skill
				// universe that can diverge from the composed session.
				plugins: this.session.plugins,
				skills: this.session.skills,
				subagentHost: this,
			});
			// Prevent the child from overwriting the parent's persisted cron jobs.
			childSession.cron.onPersist = () => {};

			const recordStore = this.childJournal(subagentId, parentActivityId, parentToolCallId);
			const agent = new KagekoAgent({
				llm,
				registry,
				kaos: childSession.kaos,
				tracker: childSession.tracker,
				permission: childSession.permission,
				mcp: childSession.mcp,
				session: childSession,
				systemPrompt: childSession.systemPrompt,
				maxContextSize: childSession.maxContextSize,
				telemetry: childSession.telemetry,
				maxSteps: profile?.maxSteps,
				recordStore,
			});

			const events: unknown[] = [];
			const toolCalls: unknown[] = [];
			const result = await agent.prompt(prompt, {
				onEvent: (event: RuntimeEvent) => {
					events.push(event);
					if (isLiveEventType(event.type))
						sinkDeliveries.push(
							Promise.resolve(
								this.session.onSubagentEvent?.({
									...event,
									meta: {
										...event.meta,
										activityId: subagentId,
										parentActivityId,
										parentToolCallId,
										actorId: subagentId,
									},
								} as RuntimeEvent),
							).then(
								() => undefined,
								(reason: unknown) => {
									// Handled at push time: a sink that rejects mid-run must
									// never surface as an unhandled rejection (G-m4). The
									// failure is recorded via telemetry, never propagated.
									this._recordDiagnostic("subagent.event_sink.error", reason);
								},
							),
						);
					if (event.type === "tool.call") {
						toolCalls.push(event.data.call);
					}
				},
				signal: abortController.signal,
			});

			return {
				content: result.content ?? "",
				toolCalls,
				events,
			};
		} catch (error) {
			// If our own timeout fired, surface the dedicated timeout error even
			// when the child runtime wrapped the abort reason in another error.
			const timedOut = abortController.signal.aborted && abortController.signal.reason === timeoutError;
			executionError = timedOut ? timeoutError : error;
			if (graphNode)
				this.session.agentGraph?.finish(graphNode.id, "failed", {
					message: executionError instanceof Error ? executionError.message : String(executionError),
				});
			throw executionError;
		} finally {
			clearTimeout(timer);
			if (signal) {
				signal.removeEventListener("abort", onParentAbort);
			}
			// Every sink delivery carries its own rejection handler (attached at
			// push time), so these promises never reject. The wait is unbounded
			// by design: the run's timeout timer is already cleared, and composed
			// sinks do not await their listeners (G-m4).
			await Promise.all(sinkDeliveries);
			if (childSession) {
				try {
					if (childSession.close) {
						await childSession.close();
					} else {
						const results = await Promise.allSettled([childSession.cron.stopAll(), childSession.tracker?.stopAll?.()]);
						const failures = results.filter((result): result is PromiseRejectedResult => result.status === "rejected");
						if (failures.length)
							throw new AggregateError(
								failures.map((failure) => failure.reason),
								"Subagent fallback cleanup failed",
							);
					}
				} catch (cleanupError) {
					// A cleanup failure after a successful run must not leave the
					// graph node `completed` while the run throws (G-m2c).
					if (graphNode)
						this.session.agentGraph?.finish(graphNode.id, "failed", {
							message: cleanupError instanceof Error ? cleanupError.message : String(cleanupError),
						});
					if (executionError !== undefined) {
						throw new AggregateError([executionError, cleanupError], "Subagent execution and cleanup failed");
					}
					throw new AggregateError([cleanupError], "Subagent cleanup failed");
				}
			}
			// `finish` is idempotent: a node already marked `failed` stays failed.
			if (graphNode) this.session.agentGraph?.finish(graphNode.id, "completed");
		}
	}

	/**
	 * Registers the executor node for a run. When the graph has no coordinator
	 * the node is registered WITHOUT a dispatch edge — linking to a
	 * non-existent endpoint would orphan the node (G-m2b).
	 */
	private _startGraphNode(profile: SubagentProfile | undefined): AgentGraphNode | undefined {
		const graph = this.session.agentGraph;
		if (!graph) return undefined;
		const coordinatorId = graph.snapshot().nodes.find((node) => node.role === "coordinator")?.id;
		const label = profile?.id ?? "executor";
		const configuration = graphConfiguration(profile, profile?.model ?? this.session.executorModel);
		if (!coordinatorId) {
			return graph.register({ id: randomUUID(), role: "executor", label, configuration, status: "running" });
		}
		return graph.start(profile?.role ?? "executor", coordinatorId, label, configuration);
	}

	private _recordDiagnostic(type: string, error: unknown): void {
		try {
			this.session.telemetry?.record({
				type,
				message: error instanceof Error ? error.message : String(error),
			});
		} catch {
			// Diagnostics are observational; they never affect the run.
		}
	}

	private async _resolveLLM(modelSpec?: SubagentModelSpec): Promise<AgentLlm> {
		const parentLlm = this.session.llm;
		if (!parentLlm) {
			throw new Error("Cannot start a subagent without a parent LLM");
		}
		if (!modelSpec) {
			return parentLlm;
		}
		if (!this.resolveLlm) throw new Error("Subagent model resolution must be provided by the application boundary");
		return this.resolveLlm(modelSpec, parentLlm, this.session.maxContextSize);
	}

	private _filterRegistry(toolNames: string[]): ToolRegistry {
		const filtered = new ToolRegistry();
		const register = (name: string) => {
			const registered = this.session.registry.getRegistration(name);
			if (!registered || filtered.get(name)) return;
			filtered.register(registered.tool, {
				origin: registered.provenance.kind,
				ownerId: registered.provenance.ownerId,
				accesses: registered.staticAccesses,
			});
		};
		for (const name of toolNames) {
			register(name);
		}
		return filtered;
	}

	private _isRetryable(err: unknown): boolean {
		if (
			err &&
			typeof err === "object" &&
			typeof (err as { isRetryableError?: unknown }).isRetryableError === "function"
		) {
			return (err as { isRetryableError: () => boolean }).isRetryableError();
		}
		const llm = this.session.llm;
		if (llm && typeof llm.isRetryableError === "function") {
			return llm.isRetryableError(err);
		}
		return isRetryableErrorFallback(err);
	}

	private async _appendRecord<K extends DurableEventType>(event: DurableEventInput<K>): Promise<void> {
		await this.session.recordStore?.append(event);
	}

	private childJournal(
		subagentId: string,
		parentActivityId?: string,
		parentToolCallId?: string,
	): JournalWriter | undefined {
		const parent = this.session.recordStore;
		if (!parent) return undefined;
		return {
			sessionId: parent.sessionId,
			append: async <K extends DurableEventType>(event: DurableEventInput<K>): Promise<DurableEvent<K>> =>
				(await parent.append({
					...event,
					meta: { ...event.meta, activityId: subagentId, parentActivityId, parentToolCallId, actorId: subagentId },
				})) as DurableEvent<K>,
			load: () => parent.load(),
		};
	}

	private async _findPriorResult(prompt: string, profile: SubagentProfile): Promise<SubagentResult | undefined> {
		const recordStore = this.session.recordStore;
		if (!recordStore) {
			return undefined;
		}
		// A persistence failure is not equivalent to an empty history.  Treating
		// it as one would rerun a completed subagent and can duplicate its tool
		// side effects.  Session-store already gives "missing" journals an empty
		// result, so every error reaching this port is actionable.
		const events = await recordStore.load();

		const profileId = profile?.id;
		const starts: Array<DurableEvent<"subagent.started">> = [];
		const ends: Array<DurableEvent<"subagent.completed">> = [];
		for (const event of events) {
			if (event.type === "subagent.started") {
				starts.push(event);
			} else if (event.type === "subagent.completed") {
				ends.push(event);
			}
		}

		// Return the most recent completed pair. Pairs are matched by
		// `subagentId` (never by prompt text — identical prompts must not cross
		// results), and the journaled result shape is validated before it is
		// trusted (G-m6).
		for (let i = ends.length - 1; i >= 0; i -= 1) {
			const endEvent = ends[i]!;
			if (!isSubagentResult(endEvent.data.result)) {
				continue;
			}
			const matchingStart = findMatchingStart(starts, endEvent, prompt, profile, profileId);
			if (matchingStart) {
				return endEvent.data.result;
			}
		}
		return undefined;
	}
}

function graphConfiguration(
	profile: SubagentProfile | undefined,
	model: SubagentModelSpec | undefined,
): AgentGraphNodeConfiguration | undefined {
	const modelRecord = model && typeof model === "object" ? (model as Record<string, unknown>) : undefined;
	const graphModel = modelRecord
		? {
				provider: typeof modelRecord["provider"] === "string" ? modelRecord["provider"] : undefined,
				modelName:
					typeof modelRecord["modelName"] === "string"
						? modelRecord["modelName"]
						: typeof modelRecord["model"] === "string"
							? modelRecord["model"]
							: undefined,
				authMode:
					modelRecord["authMode"] === "oauth"
						? ("oauth" as const)
						: modelRecord["authMode"] === "api"
							? ("api" as const)
							: undefined,
				contextLength: typeof modelRecord["contextLength"] === "number" ? modelRecord["contextLength"] : undefined,
				maxContextSize: typeof modelRecord["maxContextSize"] === "number" ? modelRecord["maxContextSize"] : undefined,
				maxOutputTokens:
					typeof modelRecord["maxOutputTokens"] === "number" ? modelRecord["maxOutputTokens"] : undefined,
			}
		: undefined;
	if (
		!graphModel &&
		!profile?.systemPrompt &&
		!profile?.permissionProfile &&
		!profile?.interactionMode &&
		!profile?.tools &&
		profile?.maxSteps === undefined
	)
		return undefined;
	return {
		...(graphModel ? { model: graphModel } : {}),
		...(profile?.systemPrompt ? { systemPrompt: profile.systemPrompt } : {}),
		...(profile?.permissionProfile ? { permissionProfile: profile.permissionProfile } : {}),
		...(profile?.interactionMode ? { interactionMode: profile.interactionMode } : {}),
		...(profile?.tools ? { tools: profile.tools } : {}),
		...(profile?.maxSteps === undefined ? {} : { maxSteps: profile.maxSteps }),
	};
}

function mergeSubagentProfiles(
	defaultProfile: SubagentProfile | undefined,
	requested: SubagentProfile | undefined,
): SubagentProfile | undefined {
	if (!defaultProfile) return requested;
	if (!requested) return defaultProfile;
	// Explicit `undefined` values (normalizeProfile emits them for unset
	// fields) must not clobber the session defaults.
	const merged: SubagentProfile = { ...defaultProfile };
	for (const [key, value] of Object.entries(requested)) {
		if (value !== undefined) {
			(merged as Record<string, unknown>)[key] = value;
		}
	}
	return merged;
}

const PROFILE_RANK: Record<PermissionProfile, number> = { manual: 0, workspace: 1, unrestricted: 2 };

function narrowPermissionProfile(parent: PermissionProfile, requested?: PermissionProfile): PermissionProfile {
	if (!requested) return parent;
	return PROFILE_RANK[requested] <= PROFILE_RANK[parent] ? requested : parent;
}

function narrowInteractionMode(parent: InteractionMode, requested?: InteractionMode): InteractionMode {
	if (parent === "unattended") return "unattended";
	return requested ?? parent;
}

function normalizeProfile(profile?: SubagentProfile | null): SubagentProfile {
	if (!profile || typeof profile !== "object") {
		return {};
	}
	return {
		id: profile.id,
		description: profile.description,
		whenToUse: profile.whenToUse,
		systemPrompt: profile.systemPrompt ?? (profile["system_prompt"] as string | undefined),
		model: profile.model,
		permissionProfile: profile.permissionProfile,
		interactionMode: profile.interactionMode,
		tools: profile.tools,
		maxSteps: profile.maxSteps ?? (profile["max_steps"] as number | undefined),
		timeoutMs: profile.timeoutMs,
	};
}

function makeRunKey(prompt: string, profile: SubagentProfile): string {
	try {
		return JSON.stringify({ prompt, profile: sanitizeForKey(normalizeProfile(profile)) });
	} catch {
		return JSON.stringify({ prompt, profile: "[unserializable]" });
	}
}

function sanitizeForKey(value: unknown, seen = new WeakSet<object>()): unknown {
	if (value === null) {
		return null;
	}
	const type = typeof value;
	if (type === "function" || type === "symbol") {
		return undefined;
	}
	if (type === "bigint") {
		return String(value);
	}
	if (type !== "object") {
		return value;
	}
	if (seen.has(value as object)) {
		return "[circular]";
	}
	seen.add(value as object);
	if (Array.isArray(value)) {
		const out: unknown[] = [];
		for (const item of value) {
			const serialized = sanitizeForKey(item, seen);
			if (serialized !== undefined) {
				out.push(serialized);
			}
		}
		return out;
	}
	const out: Record<string, unknown> = {};
	for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
		const serialized = sanitizeForKey(v, seen);
		if (serialized !== undefined) {
			out[k] = serialized;
		}
	}
	return out;
}

function findMatchingStart(
	starts: Array<DurableEvent<"subagent.started">>,
	endEvent: DurableEvent<"subagent.completed">,
	prompt: string,
	profile: SubagentProfile,
	profileId?: string,
): DurableEvent | undefined {
	// Match the pair by subagentId; prompt text is only a compatibility check
	// on the matched pair, never the join key (G-m6).
	const subagentId = endEvent.data.subagentId;
	if (!subagentId) return undefined;
	for (let i = starts.length - 1; i >= 0; i -= 1) {
		const start = starts[i]!;
		if (start.data.subagentId !== subagentId) {
			continue;
		}
		if (start.data.prompt !== prompt || endEvent.data.prompt !== prompt) {
			return undefined;
		}
		const startProfile = normalizeProfile(start.data.profile as SubagentProfile | undefined);
		// An explicit profile id selects exactly that profile's runs; without
		// one, fall back to structural profile equality.
		if (profileId) {
			return startProfile.id === profileId ? start : undefined;
		}
		if (profilesMatch(startProfile, profile)) {
			return start;
		}
		return undefined;
	}
	return undefined;
}

/** Journaled result content is capped at 64 KiB so a chatty subagent cannot
 * bloat the journal without bound (G-m5). Resume only reads `content`, so the
 * cap does not break the resume path. */
const MAX_JOURNALED_CONTENT_LENGTH = 64 * 1024;
const TRUNCATION_MARKER = "\n…[truncated]";

function capSubagentResult(result: SubagentResult): SubagentResult {
	const content =
		result.content.length > MAX_JOURNALED_CONTENT_LENGTH
			? result.content.slice(0, MAX_JOURNALED_CONTENT_LENGTH) + TRUNCATION_MARKER
			: result.content;
	// Tool-call payloads and the per-event transcript are not read back by
	// resume; they are dropped from the journaled record to bound its size.
	return {
		content,
		toolCalls: [],
		events: [],
		...(result.error !== undefined ? { error: result.error } : {}),
	};
}

/** Structural validation for a journaled `subagent.completed` result (G-m6). */
function isSubagentResult(value: unknown): value is SubagentResult {
	if (!value || typeof value !== "object" || Array.isArray(value)) return false;
	const record = value as Record<string, unknown>;
	return typeof record["content"] === "string" && Array.isArray(record["toolCalls"]) && Array.isArray(record["events"]);
}

function profilesMatch(a: SubagentProfile, b: SubagentProfile): boolean {
	if (a === b) return true;
	if (!a || !b) return false;
	const keys = new Set([...Object.keys(a), ...Object.keys(b)]);
	for (const key of keys) {
		if (key === "id") continue;
		if (!deepEqual((a as Record<string, unknown>)[key], (b as Record<string, unknown>)[key])) {
			return false;
		}
	}
	return true;
}

function deepEqual(a: unknown, b: unknown): boolean {
	if (a === b) return true;
	if (a == null || b == null) return a === b;
	if (typeof a !== typeof b) return false;
	if (Array.isArray(a) !== Array.isArray(b)) return false;
	if (Array.isArray(a) && Array.isArray(b)) {
		if (a.length !== b.length) return false;
		for (let i = 0; i < a.length; i += 1) {
			if (!deepEqual(a[i], b[i])) return false;
		}
		return true;
	}
	if (typeof a === "object" && typeof b === "object") {
		const aRecord = a as Record<string, unknown>;
		const bRecord = b as Record<string, unknown>;
		const keys = new Set([...Object.keys(aRecord), ...Object.keys(bRecord)]);
		for (const key of keys) {
			if (!deepEqual(aRecord[key], bRecord[key])) return false;
		}
		return true;
	}
	return false;
}

function isRetryableErrorFallback(err: unknown): boolean {
	if (!err) return false;
	const message = String((err as { message?: unknown }).message ?? err).toLowerCase();
	const retryableCodes = [
		"econnreset",
		"etimedout",
		"timeout",
		"429",
		"too many requests",
		"rate limit",
		"temporarily unavailable",
		"service unavailable",
		"503",
		"502",
		"500",
		"internal server error",
	];
	return retryableCodes.some((code) => message.includes(code));
}

function isAbortError(err: unknown): boolean {
	return err !== null && typeof err === "object" && (err as { name?: unknown }).name === "AbortError";
}

/**
 * The subagent's own timeout. Classified by a dedicated error type (set as the
 * AbortSignal.reason when the host's timeout fires), never by matching the
 * message substring — transient provider errors containing "timeout" must
 * stay retryable via {@link isRetryableErrorFallback}.
 */
class SubagentTimeoutError extends Error {
	constructor() {
		super("subagent timeout");
		this.name = "SubagentTimeoutError";
	}
}

function isSubagentTimeout(err: unknown): boolean {
	return err instanceof SubagentTimeoutError;
}

function sleep(ms: number): Promise<void> {
	return new Promise((resolve) => setTimeout(resolve, ms));
}

const MAX_SAFE_TIMEOUT_MS = 2 ** 31 - 1;

function clampMaxConcurrent(value: number): number {
	const n = Number(value);
	if (!Number.isFinite(n) || n < 1) {
		throw new TypeError("maxConcurrent must be a finite positive number");
	}
	return Math.floor(n);
}

function clampTimeoutMs(value: number): number {
	const n = Number(value);
	if (!Number.isFinite(n) || n < 1) {
		throw new TypeError("timeoutMs must be a finite positive number");
	}
	return Math.min(n, MAX_SAFE_TIMEOUT_MS);
}

class Semaphore {
	readonly max: number;
	private current = 0;
	private queue: Array<(release: () => void) => void> = [];

	constructor(max: number) {
		this.max = max;
	}

	acquire(): Promise<() => void> {
		if (this.current < this.max) {
			this.current += 1;
			return Promise.resolve(() => this._release());
		}
		return new Promise((resolve) => {
			this.queue.push(resolve);
		});
	}

	private _release(): void {
		if (this.queue.length > 0) {
			const next = this.queue.shift()!;
			next(() => this._release());
		} else {
			this.current -= 1;
		}
	}
}
