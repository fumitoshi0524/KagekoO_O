import { LocalKaos } from "@kageko/kaos";
import { SessionProcessSupervisor } from "@kageko/process-supervisor";
import {
	CapabilitySynthesizer,
	createBuiltinRegistry,
	createSkillTool,
	filterMcpServers,
	InjectionManager,
	KagekoAgent,
	LearningBus,
	LearningProcessor,
	LearningTriage,
	McpLearner,
	McpManager,
	noAccess,
	noopTelemetryClient,
	PlanMode,
	PluginManager,
	PluginLearner,
	replayGoalEvents,
	SkillRegistry,
	SubagentHost,
	AgentGraph,
	type SubagentModelSpec,
	type SubagentProfile,
	ToolRegistry,
	ToolResultLearner,
	FileChangeLearner,
	UserFeedbackLearner,
	SkillLearner,
	ErrorPatternLearner,
	CapabilityGapLearner,
	type LearnerAgentRunner,
	type ApprovalHandler,
	type CompactResult,
	type InteractionMode,
	type AgentLlm,
	type McpServerConfig,
	type McpTokenStore,
	type PermissionProfile,
	type TelemetryClient,
	type ToolCallLike,
	type ToolProvenance,
	type JournalPort,
	type TodoState,
	type ToolResult,
} from "@kageko/agent-core";
import type { DurableEvent, GoalBudgetData, RuntimeEvent } from "@kageko/protocol";
import type { KaosPort, ProcessTrackerPort } from "@kageko/agent-core";
import { loadConfigRaw, pruneUndefined, validateConfig } from "../configuration/config-loader.js";
import { ConfigService } from "../configuration/config-service.js";
import { WorkspaceTrustService } from "../workspace/workspace-trust-service.js";
import type { ProviderCredentialStore } from "../configuration/config-service.js";
import { PermissionManager } from "@kageko/agent-core";
import { ProcessTracker } from "@kageko/process-supervisor";
import type { PiAiLLMConfig } from "@kageko/kosong";
import { CronManager } from "../tasks/cron-service.js";
import type { CronJobFireInfo, PromptCronJob, SerializedCronJob } from "../tasks/cron-service.js";
import { TelemetryCollector } from "@kageko/telemetry";
import { MemoryEngine } from "@kageko/agent-core";
import { HookEngine } from "../events/hook-engine.js";
import type { HookDefinition } from "../events/hook-engine.js";
import { RuntimeLease } from "@kageko/session-store";
import * as crypto from "node:crypto";
import * as path from "node:path";
import { kagekoHomeDir } from "@kageko/oauth";
import { SessionStateMachine } from "./session-state-machine.js";
import { PromptService } from "../prompts/prompt-service.js";
import type { PromptHandle, PromptInput } from "../prompts/prompt-parts.js";
import type { McpService } from "../capabilities/mcp-service.js";
import type { PluginService } from "../capabilities/plugin-service.js";
import type { SkillService } from "../capabilities/skill-service.js";
import type { TaskService } from "../tasks/task-service.js";
import type { QuestionService } from "../interactions/question-service.js";

const MAX_STEER_BUFFER = 100;
/**
 * Bound on the close-time learning drain. Sits below the CLI shutdown race
 * (150s) and matches the 120s capability-generation bound that race was sized
 * for; a learner run still in flight past this point is aborted, not awaited.
 */
const LEARNER_DRAIN_CLOSE_TIMEOUT_MS = 120_000;

export interface SteerOrigin {
	kind?: string;
	[key: string]: unknown;
}

export interface SteerEntry {
	prompt: string;
	origin?: SteerOrigin;
}

export type IdleTurnLauncher = (prompt: string, origin?: SteerOrigin) => Promise<unknown> | unknown;

/** Live goal shape held in the runtime goal store; mirrors agent-core's Goal. */
interface SessionGoal {
	id: string;
	objective: string;
	completionCriterion?: string;
	status: string;
	budget: GoalBudgetData | null;
	turnsUsed: number;
	createdAt: number;
	note?: string;
	terminalReason?: string;
}

/**
 * Fully composed execution dependencies. This is intentionally not an
 * options bag: the composition root must supply one coherent runtime graph.
 */
export interface AgentRuntimeDependencies {
	sessionId: string;
	cwd: string;
	kaos: KaosPort;
	registry: ToolRegistry;
	llm: AgentLlm;
	permission: PermissionManager;
	tracker: ProcessTrackerPort;
	mcp: McpManager;
	skills: SkillRegistry;
	plugins: PluginManager;
	cron: CronManager;
	telemetry: TelemetryClient;
	systemPrompt?: string;
	maxContextSize?: number;
	/** Coordinator turn bound from agentGraph.coordinator.maxSteps; absent keeps the TurnFlow default. */
	maxSteps?: number;
	/** Coordinator tool scheduler concurrency; absent keeps the ToolScheduler default. */
	toolConcurrency?: number;
	/** Coordinator per-tool-result character budget; absent keeps the TurnFlow default. */
	budgetToolResult?: number;
	maxWallClockMs?: number;
	maxTokens?: number;
	maxCostUsd?: number;
	inputTokenCostUsd?: number;
	outputTokenCostUsd?: number;
	maxToolExecutionMs?: number;
	maxToolRetries?: number;
	maxRepeatedToolCalls?: number;
	maxNoProgressSteps?: number;
	maxConsecutiveToolFailures?: number;
	maxToolFailureLoop?: number;
	/** Context compaction policy for the coordinator agent's ContextMemory. */
	compactThreshold?: number;
	compactionTargetRatio?: number;
	compactionInputRatio?: number;
	compactionMinHistoryEvents?: number;
	modelContextLength?: number;
	modelCapabilities?: readonly string[];
	modelProvenance?: {
		readonly contextLength: "authoritative" | "catalog" | "configured" | "estimated" | "unknown";
		readonly capabilities: "authoritative" | "catalog" | "configured" | "estimated" | "unknown";
		readonly maxContextSize: "authoritative" | "catalog" | "configured" | "estimated" | "unknown";
		readonly maxOutputTokens: "authoritative" | "catalog" | "configured" | "estimated" | "unknown";
	};
	authMode?: "api" | "oauth";
	recordStore: JournalPort;
	replayEvents?: DurableEvent[];
	subagentHost?: SubagentHost;
	executorProfile?: SubagentProfile;
	subagentProfiles?: ReadonlyMap<string, SubagentProfile>;
	agentGraph?: AgentGraph;
	memory?: MemoryEngine;
	rememberSessions?: boolean;
	planMode: PlanMode;
	todoStore?: { todos: TodoState[]; save?(): Promise<void> };
	idempotencyStore?: {
		reserve(key: string): Promise<{ state: "new" | "pending" | "completed"; result?: ToolResult }>;
		complete(key: string, result: ToolResult): Promise<void>;
		release?(key: string): Promise<void>;
	};
	taskBudgetStore?: {
		active?: { startedAt: number; tokenBaseline: number; costUsd?: number; checkpointReason?: string };
		save(): Promise<void>;
	};
	injectionManager?: InjectionManager;
	hookEngine?: HookEngine;
	idleTurnLauncher?: IdleTurnLauncher;
	learningBus?: LearningBus;
	learningProcessor?: LearningProcessor;
	runtimeLease: RuntimeLease;
	taskService: TaskService;
	questionService?: QuestionService;
	diagnosticReporter?: (diagnostic: {
		readonly code: string;
		readonly message: string;
		readonly error?: unknown;
	}) => void | Promise<void>;
	/** Application-provided event bridge used only for ephemeral subagent live events. */
	subagentEventSink?: (event: RuntimeEvent) => void | Promise<void>;
	childCron?: boolean;
	cronPersistence?: (jobs: readonly SerializedCronJob[]) => Promise<void> | void;
}

export interface SessionStartOverrides {
	sessionId?: string;
	model?: Partial<PiAiLLMConfig>;
	permission?: PermissionProfile;
	interaction?: InteractionMode;
	approvalHandler?: ApprovalHandler;
	credentialStore?: ProviderCredentialStore;
	workspaceTrust?: WorkspaceTrustService;
	configService?: ConfigService;
	processSupervisor?: SessionProcessSupervisor;
	mcpService?: McpService;
	pluginService?: PluginService;
	skillService?: SkillService;
	taskService?: TaskService;
	questionService?: QuestionService;
	diagnosticReporter?: (diagnostic: {
		readonly code: string;
		readonly message: string;
		readonly error?: unknown;
	}) => void | Promise<void>;
	subagentEventSink?: (event: RuntimeEvent) => void | Promise<void>;
	recordStore?: JournalPort;
	runtimeLease?: RuntimeLease;
}

export interface SessionSnapshot {
	readonly sessionId: string;
	readonly title: string | null;
	readonly cwd: string;
	readonly model: string;
	readonly permissionProfile: PermissionProfile;
	readonly interactionMode: InteractionMode;
	readonly turnActive: boolean;
	readonly activeProcesses: number;
}

export interface RuntimeCapabilitySnapshot {
	readonly registry: ToolRegistry;
	readonly mcp: McpManager;
	readonly skills: SkillRegistry;
	readonly plugins: PluginManager;
	readonly systemPrompt: string;
}

/**
 * A Kageko session bundles config, tools, MCP servers, and the agent.
 */
/** Internal agent execution runtime, constructed only by the application composition root. */
export class AgentRuntime {
	readonly sessionId: string;
	title: string | null;
	cwd: string;
	kaos: KaosPort;
	registry: ToolRegistry;
	llm?: AgentLlm;
	planMode: PlanMode;
	todoStore: { todos: TodoState[]; save?(): Promise<void> };
	idempotencyStore?: AgentRuntimeDependencies["idempotencyStore"];
	taskBudgetStore?: AgentRuntimeDependencies["taskBudgetStore"];
	permission: PermissionManager;
	tracker: ProcessTrackerPort;
	mcp?: McpManager;
	skills: SkillRegistry;
	plugins: PluginManager;
	cron: CronManager;
	steerBuffer: SteerEntry[];
	telemetry: TelemetryClient;
	systemPrompt?: string;
	maxContextSize: number;
	readonly maxSteps?: number;
	readonly toolConcurrency?: number;
	readonly budgetToolResult?: number;
	readonly maxWallClockMs?: number;
	readonly maxTokens?: number;
	readonly maxCostUsd?: number;
	readonly inputTokenCostUsd?: number;
	readonly outputTokenCostUsd?: number;
	readonly maxToolExecutionMs?: number;
	readonly maxToolRetries?: number;
	readonly maxRepeatedToolCalls?: number;
	readonly maxNoProgressSteps?: number;
	readonly maxConsecutiveToolFailures?: number;
	readonly maxToolFailureLoop?: number;
	readonly compactThreshold?: number;
	readonly compactionTargetRatio?: number;
	readonly compactionInputRatio?: number;
	readonly compactionMinHistoryEvents?: number;
	modelContextLength?: number;
	modelCapabilities?: readonly string[];
	modelProvenance?: AgentRuntimeDependencies["modelProvenance"];
	authMode?: "api" | "oauth";
	recordStore?: JournalPort;
	replayEvents: DurableEvent[];
	subagentHost?: SubagentHost;
	executorProfile?: SubagentProfile;
	subagentProfiles?: ReadonlyMap<string, SubagentProfile>;
	agentGraph?: AgentGraph;
	memory?: MemoryEngine;
	rememberSessions: boolean;
	injectionManager?: InjectionManager;
	hookEngine?: HookEngine;
	isTurnActive: boolean;
	idleTurnLauncher?: IdleTurnLauncher;
	idleTurnPromise: Promise<unknown> | null;
	idleTurnAbortController: AbortController | null;
	turnAbortController: AbortController | null;
	turnLock: Promise<unknown>;
	private _pendingTurns: number;
	/** Ordered resident-learner work scheduled after completed turns. */
	private learningWork: Promise<void>;
	private _closed: boolean;
	private closing = false;
	private closePromise: Promise<void> | undefined;
	goalStore: Record<string, unknown>;
	learningBus?: LearningBus;
	learningProcessor?: LearningProcessor;
	learnerAgentRunner?: LearnerAgentRunner;
	runtimeLease?: RuntimeLease;
	private readonly taskService?: TaskService;
	readonly interaction?: { ask(question: string, options?: readonly string[]): Promise<string | readonly string[]> };
	pluginOperations?: { install(source: string, pluginId?: string): Promise<string> };
	reportDiagnostic?: (diagnostic: {
		readonly code: string;
		readonly message: string;
		readonly error?: unknown;
	}) => void | Promise<void>;
	onSubagentEvent?: (event: RuntimeEvent) => void | Promise<void>;
	mcpTokenStore?: McpTokenStore;
	private readonly childCron: boolean;
	private readonly customIdleTurnLauncher?: IdleTurnLauncher;
	private closeSideEffectsDone = false;

	constructor({
		sessionId,
		cwd,
		kaos,
		registry,
		llm,
		permission,
		tracker,
		mcp,
		skills,
		plugins,
		cron,
		telemetry,
		systemPrompt,
		maxContextSize,
		maxSteps,
		toolConcurrency,
		budgetToolResult,
		maxWallClockMs,
		maxTokens,
		maxCostUsd,
		inputTokenCostUsd,
		outputTokenCostUsd,
		maxToolExecutionMs,
		maxToolRetries,
		maxRepeatedToolCalls,
		maxNoProgressSteps,
		maxConsecutiveToolFailures,
		maxToolFailureLoop,
		compactThreshold,
		compactionTargetRatio,
		compactionInputRatio,
		compactionMinHistoryEvents,
		modelContextLength,
		modelCapabilities,
		modelProvenance,
		authMode,
		recordStore,
		replayEvents,
		subagentHost,
		executorProfile,
		subagentProfiles,
		memory,
		rememberSessions = true,
		planMode,
		todoStore,
		idempotencyStore,
		taskBudgetStore,
		injectionManager,
		hookEngine,
		idleTurnLauncher,
		learningBus,
		learningProcessor,
		agentGraph,
		runtimeLease,
		taskService,
		questionService,
		diagnosticReporter,
		subagentEventSink,
		childCron = false,
		cronPersistence,
	}: AgentRuntimeDependencies) {
		this.sessionId = sessionId;
		this.title = null;
		this.cwd = path.resolve(cwd);
		this.kaos = kaos;
		this.registry = registry;
		this.llm = llm;
		this.planMode = planMode;
		this.todoStore = todoStore ?? { todos: [] };
		this.idempotencyStore = idempotencyStore;
		this.taskBudgetStore = taskBudgetStore;
		this.permission = permission;
		this.tracker = tracker;
		this.mcp = mcp;
		this.skills = skills;
		this.plugins = plugins;
		this.cron = cron;
		this.cron.onFire ??= (job, info) => this.steerCronJob(job, info);
		if (cronPersistence) this.cron.onPersist = (jobs) => cronPersistence(jobs);
		this.steerBuffer = [];
		this.telemetry = telemetry;
		this.systemPrompt = systemPrompt;
		this.maxContextSize = maxContextSize ?? 128000;
		this.maxSteps = maxSteps;
		this.toolConcurrency = toolConcurrency;
		this.budgetToolResult = budgetToolResult;
		this.maxWallClockMs = maxWallClockMs;
		this.maxTokens = maxTokens;
		this.maxCostUsd = maxCostUsd;
		this.inputTokenCostUsd = inputTokenCostUsd;
		this.outputTokenCostUsd = outputTokenCostUsd;
		this.maxToolExecutionMs = maxToolExecutionMs;
		this.maxToolRetries = maxToolRetries;
		this.maxRepeatedToolCalls = maxRepeatedToolCalls;
		this.maxNoProgressSteps = maxNoProgressSteps;
		this.maxConsecutiveToolFailures = maxConsecutiveToolFailures;
		this.maxToolFailureLoop = maxToolFailureLoop;
		this.compactThreshold = compactThreshold;
		this.compactionTargetRatio = compactionTargetRatio;
		this.compactionInputRatio = compactionInputRatio;
		this.compactionMinHistoryEvents = compactionMinHistoryEvents;
		this.modelContextLength = modelContextLength;
		this.modelCapabilities = modelCapabilities;
		this.modelProvenance = modelProvenance;
		this.authMode = authMode;
		this.recordStore = recordStore;
		this.replayEvents = replayEvents ?? [];
		this.subagentHost = subagentHost;
		this.executorProfile = executorProfile;
		this.subagentProfiles = subagentProfiles;
		this.memory = memory;
		this.rememberSessions = rememberSessions;
		this.injectionManager = injectionManager;
		this.hookEngine = hookEngine;
		this.isTurnActive = false;
		this.idleTurnLauncher = idleTurnLauncher;
		this.customIdleTurnLauncher = idleTurnLauncher;
		this.idleTurnPromise = null;
		this.idleTurnAbortController = null;
		this.turnAbortController = null;
		this.turnLock = Promise.resolve();
		this._pendingTurns = 0;
		this.learningWork = Promise.resolve();
		this._closed = false;
		this.goalStore = {};
		this.learningBus = learningBus;
		this.learningProcessor = learningProcessor;
		this.agentGraph = agentGraph;
		this.runtimeLease = runtimeLease;
		this.taskService = taskService;
		this.interaction = questionService
			? {
					ask: (question, options) =>
						questionService.requestForSession(this.sessionId, { id: crypto.randomUUID(), prompt: question, options }),
				}
			: undefined;
		this.reportDiagnostic = diagnosticReporter;
		this.onSubagentEvent = subagentEventSink;
		this.childCron = childCron;
		if (hookEngine) {
			this.permission.setHookEngine(hookEngine);
		}
	}

	/**
	 * Installs the core-owned contextual injector after the runtime itself has
	 * been composed.  This preserves the circular reference without letting a
	 * runtime construct an application graph on its own.
	 */
	attachInjectionManager(injectionManager: InjectionManager): void {
		if (this.injectionManager) {
			throw new Error("AgentRuntime injection manager is already attached");
		}
		this.injectionManager = injectionManager;
	}

	/** Replace a fully prepared extension snapshot between turns. */
	replaceCapabilities(snapshot: RuntimeCapabilitySnapshot): void {
		if (this._closed || this.closing || this.isTurnActive) {
			throw new Error(`Session ${this.sessionId} cannot reload capabilities during an active turn`);
		}
		this.registry = snapshot.registry;
		this.mcp = snapshot.mcp;
		this.skills = snapshot.skills;
		this.plugins = snapshot.plugins;
		this.systemPrompt = snapshot.systemPrompt;
	}

	createAgent(): KagekoAgent {
		if (!this.llm) {
			throw new Error("Agent runtime has no LLM. Construct it through the application composition root.");
		}
		const agent = new KagekoAgent({
			llm: this.llm,
			registry: this.registry,
			kaos: this.kaos,
			tracker: this.tracker,
			permission: this.permission,
			mcp: this.mcp,
			session: this,
			systemPrompt: this.systemPrompt,
			maxContextSize: this.maxContextSize,
			maxContextSizeSource: this.modelProvenance?.maxContextSize,
			maxSteps: this.maxSteps,
			maxWallClockMs: this.maxWallClockMs,
			maxTokens: this.maxTokens,
			maxCostUsd: this.maxCostUsd,
			inputTokenCostUsd: this.inputTokenCostUsd,
			outputTokenCostUsd: this.outputTokenCostUsd,
			maxToolExecutionMs: this.maxToolExecutionMs,
			maxToolRetries: this.maxToolRetries,
			maxRepeatedToolCalls: this.maxRepeatedToolCalls,
			maxNoProgressSteps: this.maxNoProgressSteps,
			maxConsecutiveToolFailures: this.maxConsecutiveToolFailures,
			maxToolFailureLoop: this.maxToolFailureLoop,
			toolConcurrency: this.toolConcurrency,
			budgetToolResult: this.budgetToolResult,
			compactThreshold: this.compactThreshold,
			compactionTargetRatio: this.compactionTargetRatio,
			compactionInputRatio: this.compactionInputRatio,
			compactionMinHistoryEvents: this.compactionMinHistoryEvents,
			telemetry: this.telemetry,
			onDiagnostic: (message, error) => this.reportDiagnostic?.({ code: "turn", message, error }),
			recordStore: this.recordStore,
			replayEvents: this.replayEvents,
		});
		// The runtime owns idle-turn scheduling: serialization flows through
		// runTurn/turnLock and abort plumbing through idleTurnAbortController.
		// The agent only executes the prepared turn.  A caller-supplied custom
		// launcher is never replaced; the built-in launcher always binds the
		// freshly created agent so a capability reload cannot leave cron/idle
		// turns running on a retired agent graph.
		if (!this.customIdleTurnLauncher) {
			this.idleTurnLauncher = (prompt, origin) => this.launchIdleTurn(agent, prompt, origin);
		}
		return agent;
	}

	/** Explicit host shell command: supervised and journaled, never an agent permission bypass. */
	async runUserShell(
		command: string,
		background = false,
	): Promise<{ readonly taskId: string; readonly status: string }> {
		if (this.isClosed()) throw new Error("Session is closed");
		if (!command.trim()) throw new Error("Shell command is required");
		const executable =
			process.platform === "win32" ? (process.env["ComSpec"] ?? "cmd.exe") : (process.env["SHELL"] ?? "/bin/sh");
		const args = process.platform === "win32" ? ["/d", "/s", "/c", command] : ["-lc", command];
		const task = await this.tracker.spawnDurable(executable, args, { cwd: this.cwd, background, command });
		return { taskId: task.taskId, status: this.tracker.getTask(task.taskId)?.status ?? "running" };
	}

	readTaskOutput(taskId: string, offset = 0, limit?: number) {
		return this.tracker.readOutput(taskId, offset, limit);
	}

	stopTask(taskId: string, reason = "Stopped by user"): Promise<unknown> {
		return this.tracker.stop(taskId, reason);
	}

	listCron() {
		return this.cron.list();
	}
	createCron(input: { readonly cron: string; readonly prompt: string; readonly recurring?: boolean }) {
		return this.cron.create(input);
	}
	deleteCron(id: string): boolean {
		return this.cron.remove(id);
	}

	private async launchIdleTurn(agent: KagekoAgent, prompt: string, origin?: SteerOrigin): Promise<unknown> {
		if (this.isClosed()) {
			throw new Error("Session is closed");
		}
		this.idleTurnAbortController?.abort();
		const abortController = new AbortController();
		this.idleTurnAbortController = abortController;
		try {
			return await this.runTurn(() => agent.runIdleTurn(prompt, origin, abortController.signal));
		} finally {
			// Only clear the controller if this is still the active idle turn; a
			// newer idle turn will have replaced it.
			if (this.idleTurnAbortController === abortController) {
				this.idleTurnAbortController = null;
			}
		}
	}

	snapshot(): SessionSnapshot {
		const source = this.llm as { modelName?: unknown; provider?: unknown; model?: { provider?: unknown } } | undefined;
		const modelName = typeof source?.modelName === "string" ? source.modelName : "unknown";
		const provider =
			typeof source?.model?.provider === "string"
				? source.model.provider
				: typeof source?.provider === "string"
					? source.provider
					: undefined;
		return {
			sessionId: this.sessionId,
			title: this.title,
			cwd: this.cwd,
			model: provider ? `${provider}/${modelName}` : modelName,
			permissionProfile: this.permission.profile,
			interactionMode: this.permission.interaction,
			turnActive: this.isTurnActive,
			activeProcesses: this.tracker.list(true).length,
		};
	}

	isClosed(): boolean {
		return this._closed || this.closing;
	}

	steerCronJob(job: PromptCronJob, info: CronJobFireInfo = {}): void {
		const coalescedCount = info.coalescedCount ?? 1;
		const stale = info.stale ?? false;

		if (coalescedCount > 1 && this.isTurnActive) {
			this.steer(`While you were away, ${coalescedCount} cron fires were coalesced.`, {
				kind: "cron_coalesced",
				jobId: job.id,
				coalescedCount,
			});
		}

		this.steer(job.prompt, {
			kind: "cron_job",
			jobId: job.id,
			cron: job.cron,
			recurring: job.recurring,
			coalescedCount,
			stale,
		});
	}

	steer(prompt: string, origin?: SteerOrigin): void {
		if (this._closed) return;
		if (this._pendingTurns > 0 || !this.idleTurnLauncher) {
			this.steerBuffer.push({ prompt, origin });
			if (this.steerBuffer.length > MAX_STEER_BUFFER) {
				this.steerBuffer.shift();
			}
			return;
		}
		const promise = Promise.resolve(this.idleTurnLauncher(prompt, origin));
		this.idleTurnPromise = promise;
		promise.catch(() => {});
		promise
			.finally(() => {
				if (this.idleTurnPromise === promise) {
					this.idleTurnPromise = null;
				}
			})
			.catch(() => {});
	}

	async flushSteerBuffer(
		memory?: { appendUser(prompt: string, origin: string): void },
		recordStore?: JournalPort,
	): Promise<SteerEntry[]> {
		const buffer = this.steerBuffer;
		this.steerBuffer = [];
		for (let index = 0; index < buffer.length; index += 1) {
			const { prompt, origin } = buffer[index]!;
			try {
				await recordStore?.append({
					type: "user.prompt",
					data: {
						content: prompt,
						...(origin?.kind === undefined ? {} : { origin: origin.kind }),
					},
				});
				memory?.appendUser(prompt, origin?.kind ?? "system_trigger");
			} catch (error) {
				// Preserve the failed and not-yet-processed entries ahead of any
				// steering requests that arrived while this flush was running.
				this.steerBuffer = [...buffer.slice(index), ...this.steerBuffer];
				throw error;
			}
		}
		return buffer;
	}

	setTurnActive(active: boolean): void {
		this.isTurnActive = active;
	}

	abortIdleTurn(): void {
		this.idleTurnAbortController?.abort();
		// Let the idle turn's finally block clear the controller and turn state.
	}

	abortTurn(): void {
		this.turnAbortController?.abort();
	}

	/**
	 * Serialize turn execution so that only one turn runs at a time on this
	 * session. This prevents cron idle turns and user prompts from racing on
	 * shared memory/session state.
	 */
	async withTurn<T>(fn: () => Promise<T>): Promise<T> {
		const run = async () => {
			return await fn();
		};
		const result = this.turnLock.then(run, run);
		this.turnLock = result;
		return result;
	}

	async runTurn<T>(fn: () => Promise<T>): Promise<T> {
		// The turn-active bookkeeping lives inside the turnLock callback so the
		// flag can only change while the lock is held.  Otherwise a capability
		// swap queued on the same lock could observe a false gap between one
		// turn's finally block and the next turn's start.
		return this.withTurn(async () => {
			this._pendingTurns += 1;
			this.setTurnActive(true);
			try {
				return await fn();
			} finally {
				this._pendingTurns -= 1;
				if (this._pendingTurns === 0) {
					this.setTurnActive(false);
					// Learning is a resident graph branch, not part of the user's
					// critical turn latency. Explicit learning reads synchronize on
					// the ordered work through waitForLearning().
					this.scheduleLearningFlush();
				}
			}
		});
	}

	private scheduleLearningFlush(): void {
		if (!this.learningBus) return;
		const flush = async () => {
			try {
				await this.learningBus?.flush();
			} catch (error) {
				try {
					await this.reportDiagnostic?.({
						code: "learning.turn_flush_failed",
						message: "Resident learner failed to process the completed turn",
						error,
					});
				} catch {
					// Diagnostics never change the user turn outcome.
				}
			}
		};
		this.learningWork = this.learningWork.then(flush, flush);
	}

	/** Wait until every learner observation scheduled before this call settles. */
	async waitForLearning(): Promise<void> {
		await this.learningWork;
	}

	/**
	 * Close-time learning drain with a deadline. A learner run is bounded at
	 * 300s, but the CLI shutdown race bounds the whole close at 150s; without a
	 * deadline + abort handle, a run started near close could hang the drain
	 * past that race and keep writing after shutdown was reported. The deadline
	 * matches the existing capability-generation bound (120s) the shutdown
	 * window was sized for. When it fires, the runner is closed: the in-flight
	 * run is aborted into a cancellation and queued triggers resolve without
	 * touching the pending queue.
	 */
	private async _drainLearningForClose(): Promise<void> {
		const runner = this.learnerAgentRunner;
		if (!runner) {
			await this.waitForLearning();
			return;
		}
		let timer: NodeJS.Timeout | undefined;
		const deadline = new Promise<void>((resolve) => {
			timer = setTimeout(resolve, LEARNER_DRAIN_CLOSE_TIMEOUT_MS);
			timer.unref?.();
		});
		try {
			const drained = await Promise.race([this.waitForLearning().then(() => true), deadline.then(() => false)]);
			if (!drained) runner.close();
		} finally {
			if (timer) clearTimeout(timer);
		}
	}

	async close(): Promise<void> {
		if (this._closed) return;
		if (this.closePromise) return this.closePromise;
		this.closing = true;
		this.closePromise = (async () => {
			const failures: Error[] = [];
			const attempt = async (label: string, operation: () => Promise<unknown> | unknown) => {
				try {
					await operation();
				} catch (error) {
					failures.push(
						new Error(`${label}: ${error instanceof Error ? error.message : String(error)}`, { cause: error }),
					);
				}
			};
			try {
				this.abortIdleTurn();
				this.turnAbortController?.abort();
				// Wait for any queued/pending turns to finish or abort.
				let drainTimer: NodeJS.Timeout | undefined;
				try {
					await Promise.race([
						this.turnLock,
						new Promise((_, reject) => {
							drainTimer = setTimeout(() => reject(new Error("turn drain timeout")), 5000);
						}),
					]);
				} catch {
					// Continue closing even if turns are slow.
				} finally {
					if (drainTimer) clearTimeout(drainTimer);
				}
				if (this.idleTurnPromise) {
					// Double insurance: the built-in idle launcher already runs
					// through runTurn/turnLock (drained above), but a custom
					// idleTurnLauncher may not, so wait on the tracked promise too.
					let timer: NodeJS.Timeout | undefined;
					try {
						await Promise.race([
							this.idleTurnPromise,
							new Promise((_, reject) => {
								timer = setTimeout(() => reject(new Error("idle turn close timeout")), 5000);
							}),
						]);
					} catch {
						// Continue closing even if idle turn is slow.
					} finally {
						if (timer) clearTimeout(timer);
					}
				}
				if (!this.closeSideEffectsDone) {
					// Session-end side effects fire exactly once per runtime, even
					// when a failed close is retried: hooks and memory summaries are
					// externally visible and must never run twice.
					this.closeSideEffectsDone = true;
					await attempt("SessionEnd hook failed", () => this.hookEngine?.trigger("SessionEnd", { cwd: this.cwd }));
					if (this.rememberSessions && this.memory && this.recordStore) {
						try {
							const events = await this.recordStore.load();
							const summary = await this.memory.summarizeSession(events);
							if (summary) {
								await this.memory.remember("project", `Session summary: ${summary}`);
							}
						} catch {
							// Best-effort session memory.
						}
					}
				}
				// Drain learning scheduled before close while the learner runner is
				// still live: for a headless one-shot process this close-time drain is
				// the only learning opportunity, and discarding it would lose durable
				// capability-gap events. The drain is bounded below the CLI shutdown
				// race (150s) by the learner drain deadline; on deadline the runner is
				// closed, which aborts the in-flight run (its trigger resolves
				// cancelled, touching nothing) and lets the drain settle immediately.
				await attempt("resident learner drain failed", () => this._drainLearningForClose());
				await attempt("learner agent runner close failed", () => this.learnerAgentRunner?.close());
				await attempt("learning bus flush failed", () => this.learningBus?.flush());
				if (this.learningProcessor) {
					await attempt("learning processor stop failed", () => this.learningProcessor?.stop());
					await attempt("learning processor flush failed", () => this.learningProcessor?.flush());
				}
				await Promise.all([
					attempt("learning bus close failed", () => this.learningBus?.close()),
					...(this.childCron
						? [attempt("child cron shutdown failed", () => this.taskService?.closeChildCron(this.cron))]
						: []),
					attempt("process supervisor shutdown failed", () => this.tracker.stopAll()),
					attempt("telemetry shutdown failed", () => this.telemetry?.close?.()),
				]);
			} finally {
				await attempt("runtime lease release failed", () => this.runtimeLease?.release());
			}
			if (failures.length) throw new AggregateError(failures, `Session ${this.sessionId} closed with cleanup failures`);
			this._closed = true;
		})();
		try {
			await this.closePromise;
		} catch (error) {
			// A rejected cleanup must retain this owner for a later close attempt.
			this.closing = false;
			this.closePromise = undefined;
			throw error;
		}
	}
}

export function runtimeSessionDirectory(cwd: string, sessionId: string): string {
	const workspaceId = crypto.createHash("sha256").update(path.resolve(cwd)).digest("hex").slice(0, 24);
	return path.join(kagekoHomeDir(), ".kageko", "runtime", "workspaces", workspaceId, "sessions", sessionId);
}

export type { RuntimeEvent } from "@kageko/protocol";

/** Application-owned repository runtime facade. */
export class RuntimeSession {
	readonly state = new SessionStateMachine();
	private readonly prompts: PromptService;
	private runtime?: AgentRuntime;
	private agent?: KagekoAgent;
	private closePromise: Promise<void> | undefined;
	constructor(
		readonly summary: import("@kageko/session-store").SessionSummary,
		prompts?: PromptService,
	) {
		this.prompts = prompts ?? new PromptService();
		this.state.transition("ready");
	}
	/** Bind the sole agent runtime for this repository session. */
	bindRuntime(runtime: AgentRuntime): void {
		if (runtime.sessionId !== this.summary.sessionId)
			throw new Error("Runtime session id does not match repository session");
		if (this.runtime && this.runtime !== runtime)
			throw new Error(`Session ${this.summary.sessionId} already has an agent runtime`);
		this.runtime = runtime;
		this.agent = runtime.createAgent();
		// AgentRuntime journals the user prompt as part of turn execution; the
		// repository facade must not append a duplicate event before dispatch.
		this.prompts.configure({
			onSubmit: undefined,
			executor: async (input, onEvent) => {
				await this.agent!.prompt([...input.parts], { onEvent, turnId: input.turnId });
			},
		});
	}
	/**
	 * Atomically switch to a prepared capability graph inside the runtime turn
	 * lock.  The graph swap, the agent rebuild, and the publication callback
	 * happen as one serialized step, so neither a cron idle turn nor a prompt
	 * can observe a published manager paired with the old runtime graph.
	 * Returns false when the session is not in a swappable state.
	 */
	async swapCapabilities(snapshot: RuntimeCapabilitySnapshot, publish: () => Promise<void>): Promise<boolean> {
		if (!this.runtime) throw new Error(`Session ${this.summary.sessionId} has no composed agent runtime`);
		const runtime = this.runtime;
		return runtime.withTurn(async () => {
			if (this.state.status !== "ready" || runtime.isClosed() || runtime.isTurnActive) return false;
			const previous: RuntimeCapabilitySnapshot = {
				registry: runtime.registry,
				mcp: runtime.mcp!,
				skills: runtime.skills,
				plugins: runtime.plugins,
				systemPrompt: runtime.systemPrompt ?? "",
			};
			const previousAgent = this.agent;
			try {
				runtime.replaceCapabilities(snapshot);
				this.agent = runtime.createAgent();
				await publish();
				return true;
			} catch (error) {
				// A candidate remains unpublished until this callback resolves. Restore
				// the exact executable graph before surfacing the failure, so the
				// caller can discard the candidate without closing the live runtime's
				// MCP manager or registry.
				runtime.replaceCapabilities(previous);
				this.agent = previousAgent ?? runtime.createAgent();
				throw error;
			}
		});
	}
	isIdle(): boolean {
		return this.state.status === "ready" && !this.runtime?.isTurnActive;
	}
	capabilityMemory(): MemoryEngine | undefined {
		return this.runtime?.memory;
	}
	/** Read-only worker declarations used when capabilities rebuild their prompt. */
	get subagentProfiles(): ReadonlyMap<string, SubagentProfile> | undefined {
		return this.runtime?.subagentProfiles;
	}
	learningProcessor(): LearningProcessor | undefined {
		return this.runtime?.learningProcessor;
	}
	async waitForLearning(): Promise<void> {
		await this.runtime?.waitForLearning();
	}
	goalSnapshot(): unknown {
		const store = this.runtime?.goalStore as { activeGoal?: unknown } | undefined;
		return store?.activeGoal ?? null;
	}
	async createGoal(input: {
		objective: string;
		completionCriterion?: string;
		budget?: GoalBudgetData | null;
	}): Promise<unknown> {
		if (!this.runtime) throw new Error(`Session ${this.summary.sessionId} has no composed agent runtime`);
		const goal = {
			id: crypto.randomUUID(),
			objective: input.objective,
			completionCriterion: input.completionCriterion,
			status: "active",
			budget: input.budget ?? null,
			turnsUsed: 0,
			createdAt: Date.now(),
		};
		await this.runtime.recordStore?.append({
			type: "goal.created",
			data: {
				goal: {
					id: goal.id,
					description: goal.objective,
					status: goal.status,
					budget: goal.budget,
					turnsUsed: goal.turnsUsed,
					createdAt: goal.createdAt,
				},
			},
		});
		const store = this.runtime.goalStore as { activeGoal?: unknown; goals?: unknown[] };
		store.activeGoal = goal;
		(store.goals ??= []).push(goal);
		return goal;
	}
	async updateGoal(input: { status: "active" | "paused" | "completed" | "blocked"; note?: string }): Promise<unknown> {
		if (!this.runtime) throw new Error(`Session ${this.summary.sessionId} has no composed agent runtime`);
		const store = this.runtime.goalStore as { activeGoal?: SessionGoal | null };
		if (!store.activeGoal) return null;
		// Completion is terminal. A pause is intentionally not terminal: callers
		// must be able to inspect and resume it after reopening the application.
		const nextGoal: SessionGoal = { ...store.activeGoal };
		let changed = false;
		if (nextGoal.status !== input.status) {
			nextGoal.status = input.status;
			changed = true;
		}
		if (input.note !== undefined && nextGoal.note !== input.note) {
			nextGoal.note = input.note;
			changed = true;
		}
		if (!changed) return store.activeGoal;
		if (nextGoal.status === "completed") {
			await this.runtime.recordStore?.append({
				type: "goal.completed",
				data: input.note === undefined ? { goalId: nextGoal.id } : { goalId: nextGoal.id, reason: input.note },
			});
			nextGoal.terminalReason = input.note;
			// The completion note is carried as terminalReason; note itself is not
			// durable, so keeping it would leave live state divergent from replay.
			delete nextGoal.note;
			Object.assign(store.activeGoal, nextGoal);
			delete store.activeGoal.note;
			store.activeGoal = null;
			// `null` is reserved for "there was no active goal". Returning the
			// terminal snapshot lets callers distinguish success from a soft failure.
			return nextGoal;
		}
		await this.runtime.recordStore?.append({
			type: "goal.updated",
			data: {
				goal: {
					id: nextGoal.id,
					description: nextGoal.objective,
					status: nextGoal.status,
					budget: nextGoal.budget ?? null,
					turnsUsed: nextGoal.turnsUsed,
					createdAt: nextGoal.createdAt,
				},
			},
		});
		Object.assign(store.activeGoal, nextGoal);
		return store.activeGoal;
	}
	listRegisteredTools(): readonly { name: string; provenance: Pick<ToolProvenance, "kind" | "ownerId"> }[] {
		const registry = this.runtime?.registry;
		if (!registry) return [];
		return registry
			.list()
			.map((tool) => ({ name: tool.name, provenance: registry.getRegistration(tool.name)!.provenance }));
	}
	async compactContext(instruction?: string): Promise<CompactResult> {
		if (!this.runtime) throw new Error(`Session ${this.summary.sessionId} has no composed agent runtime`);
		const runtime = this.runtime;
		return runtime.withTurn(async () => {
			// The idle check runs inside the turn lock so a prompt cannot slip in
			// between the check and the compaction.
			// Reconcile the facade state here as well: SDK callers can issue compact
			// immediately after a terminal turn event, before the asynchronous
			// completion publication callback has run.
			this.refreshPromptState();
			if (!this.isIdle()) throw new Error("Session is busy; compaction runs only while idle");
			return this.agent!.requestCompact(instruction);
		});
	}
	async prompt(input: PromptInput, onEvent?: (event: RuntimeEvent) => void): Promise<PromptHandle> {
		if (this.state.status === "closed" || this.state.status === "closing" || this.state.status === "failed")
			throw new Error("Session is closed");
		this.state.transition("running");
		try {
			return await this.prompts.submit(input, onEvent);
		} catch (error) {
			// A failed submission never reaches the queue, so the running state
			// staged above must be rolled back instead of stranding the session.
			if (this.state.status === "running" && this.prompts.queue.size === 0 && !this.runtime?.isTurnActive) {
				this.state.transition("ready");
			}
			throw error;
		}
	}
	// Draining one prompt only falls back to ready once the queue is empty;
	// with more prompts queued the session is still running.
	async drainNext(): Promise<PromptInput | undefined> {
		const next = await this.prompts.drain();
		if (next && this.prompts.queue.size === 0 && this.state.status === "running") this.state.transition("ready");
		return next;
	}
	snapshot(): {
		sessionId: string;
		status: string;
		queuedPrompts: number;
		provider?: string;
		modelName?: string;
		model?: {
			provider: string;
			modelName: string;
			contextLength?: number;
			capabilities?: readonly string[];
			maxContextSize?: number;
			maxOutputTokens?: number;
			reasoningConfig?: Readonly<Record<string, unknown>>;
			authMode?: "api" | "oauth";
			provenance?: AgentRuntimeDependencies["modelProvenance"];
			metadataSource?: {
				kind: "provider" | "catalog";
				providerId: string;
				endpoint?: string;
				authMode?: "api" | "oauth";
				source?: "provider-live" | "public-catalog" | "local-cache" | "static-fallback";
				authoritative?: boolean;
			};
		};
		contextUsed?: number;
		contextLength?: number;
		contextLimit?: number;
		contextRemaining?: number;
		contextRatio?: number;
		contextSource?: string;
		contextUsedSource?: "authoritative" | "catalog" | "configured" | "estimated" | "unknown";
		contextLimitSource?: "authoritative" | "catalog" | "configured" | "estimated" | "unknown";
		authMode?: "api" | "oauth";
	} {
		const budget = this.agent?.memory.budget();
		const source = this.runtime?.llm as
			| {
					modelName?: unknown;
					model?: {
						provider?: unknown;
						modelName?: unknown;
						contextLength?: unknown;
						capabilities?: unknown;
						maxContextSize?: unknown;
						maxOutputTokens?: unknown;
						reasoningConfig?: unknown;
						authMode?: unknown;
						provenance?: AgentRuntimeDependencies["modelProvenance"];
						metadataSource?: {
							kind: "provider" | "catalog";
							providerId: string;
							endpoint?: string;
							authMode?: "api" | "oauth";
							source?: "provider-live" | "public-catalog" | "local-cache" | "static-fallback";
							authoritative?: boolean;
						};
					};
			  }
			| undefined;
		const provider = typeof source?.model?.provider === "string" ? source.model.provider : undefined;
		const modelName =
			typeof source?.model?.modelName === "string"
				? source.model.modelName
				: typeof source?.modelName === "string"
					? source.modelName
					: undefined;
		const contextLength =
			typeof this.runtime?.modelContextLength === "number"
				? this.runtime.modelContextLength
				: typeof source?.model?.contextLength === "number"
					? source.model.contextLength
					: undefined;
		const authMode =
			this.runtime?.authMode ??
			(source?.model?.authMode === "oauth" ? "oauth" : source?.model?.authMode === "api" ? "api" : undefined);
		const capabilities =
			this.runtime?.modelCapabilities ??
			(Array.isArray(source?.model?.capabilities)
				? source.model.capabilities.filter((value): value is string => typeof value === "string")
				: undefined);
		const provenance = this.runtime?.modelProvenance ?? source?.model?.provenance;
		const metadataSource = source?.model?.metadataSource;
		const model =
			provider && modelName
				? {
						provider,
						modelName,
						...(contextLength === undefined ? {} : { contextLength }),
						...(capabilities === undefined ? {} : { capabilities }),
						...(typeof source?.model?.maxContextSize === "number"
							? { maxContextSize: source.model.maxContextSize }
							: budget
								? { maxContextSize: budget.limit }
								: {}),
						...(typeof source?.model?.maxOutputTokens === "number"
							? { maxOutputTokens: source.model.maxOutputTokens }
							: {}),
						...(source?.model?.reasoningConfig && typeof source.model.reasoningConfig === "object"
							? { reasoningConfig: source.model.reasoningConfig as Record<string, unknown> }
							: {}),
						...(authMode === undefined ? {} : { authMode }),
						...(provenance === undefined ? {} : { provenance }),
						...(metadataSource === undefined ? {} : { metadataSource }),
					}
				: undefined;
		return {
			sessionId: this.summary.sessionId,
			status: this.state.status,
			queuedPrompts: this.prompts.queue.size,
			...(provider === undefined ? {} : { provider }),
			...(modelName === undefined ? {} : { modelName }),
			...(model === undefined ? {} : { model }),
			contextUsed: budget?.used,
			contextLength,
			contextLimit: budget?.limit,
			contextRemaining: budget?.remaining,
			contextRatio: budget?.ratio,
			contextSource: budget?.source,
			contextUsedSource: budget?.usedSource,
			contextLimitSource: budget?.limitSource,
			authMode,
		};
	}
	cancelQueued(): number {
		const count = this.prompts.cancelQueued();
		this.refreshPromptState();
		return count;
	}
	/** Reconcile a removed queued handle without touching any other prompt. */
	refreshPromptState(): void {
		if (this.state.status === "running" && this.prompts.queue.size === 0 && !this.runtime?.isTurnActive) {
			this.state.transition("ready");
		}
	}
	abortActiveTurn(): void {
		this.runtime?.abortTurn();
	}
	abortIdleTurn(): void {
		this.runtime?.abortIdleTurn();
	}
	async runUserShell(
		command: string,
		background = false,
	): Promise<{ readonly taskId: string; readonly status: string }> {
		if (!this.runtime) throw new Error(`Session ${this.summary.sessionId} has no composed agent runtime`);
		return this.runtime.runUserShell(command, background);
	}
	readTaskOutput(taskId: string, offset = 0, limit?: number) {
		return this.runtime?.readTaskOutput(taskId, offset, limit);
	}
	async stopTask(taskId: string, reason?: string): Promise<unknown> {
		if (!this.runtime) throw new Error(`Session ${this.summary.sessionId} has no composed agent runtime`);
		return this.runtime.stopTask(taskId, reason);
	}
	listCron() {
		if (!this.runtime) throw new Error(`Session ${this.summary.sessionId} has no composed agent runtime`);
		return this.runtime.listCron();
	}
	createCron(input: { readonly cron: string; readonly prompt: string; readonly recurring?: boolean }) {
		if (!this.runtime) throw new Error(`Session ${this.summary.sessionId} has no composed agent runtime`);
		return this.runtime.createCron(input);
	}
	deleteCron(id: string): boolean {
		if (!this.runtime) throw new Error(`Session ${this.summary.sessionId} has no composed agent runtime`);
		return this.runtime.deleteCron(id);
	}
	async close(): Promise<void> {
		if (this.closePromise) return this.closePromise;
		if (this.state.status === "closed") return;
		this.closePromise = (async () => {
			this.state.transition("closing");
			this.prompts.cancelQueued();
			await this.runtime?.close();
			this.state.transition("closed");
		})();
		try {
			await this.closePromise;
		} catch (error) {
			// A partial shutdown is not runnable. Keep it owned in a retryable
			// failed state; the state machine permits failed -> closing for retry.
			this.state.transition("failed");
			this.closePromise = undefined;
			throw error;
		}
	}
}
