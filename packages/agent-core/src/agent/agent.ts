import { TurnFlow } from "../turn/turn-runner.js";
import type {
	AgentLlm,
	HookEngineLike,
	HookPayload,
	SessionLike,
	ToolExecution,
	ToolResult,
	TurnFlowHooks,
	TurnMessage,
	TurnRunOptions,
	TurnRunResult,
} from "../turn/turn-runner.js";
import { ContextMemory, type CompactResult } from "../context/memory.js";
import { replayGoalEvents } from "../tools/builtins/goal.js";
import type { JournalPort as JournalWriter } from "../ports/repository.js";
import type { GoalStore, GoalData } from "./injection/injectors.js";
import type { TodoState } from "../planning/todo-state.js";
import type { InjectedMessage } from "./injection/manager.js";
import type { ToolRegistry } from "../tools/registry.js";
import type { ProcessTrackerPort } from "../ports/process.js";
import type { PermissionManager } from "../permissions/index.js";
import type { McpManager } from "../capabilities/mcp/mcp-manager.js";
import type { TelemetryClient } from "../telemetry/index.js";
import type { MessageContent, ToolCall } from "../context/projector.js";
import type { LlmContentPart as ContentPart, LlmToolCall, ChatOptions } from "../ports/llm.js";
import type { DurableEvent, DurableEventInput, PromptPart as RecordedPromptPart, RuntimeEvent } from "@kageko/protocol";

export type PromptPart = ContentPart;

function promptRecord(content: string | PromptPart[], origin?: string): DurableEventInput<"user.prompt"> {
	if (typeof content === "string") {
		return {
			type: "user.prompt",
			meta: { occurredAt: Date.now() },
			data: { content, ...(origin === undefined ? {} : { origin }) },
		};
	}
	const parts: RecordedPromptPart[] = content
		.filter((part) => part.type === "text" || part.type === "image_url")
		.flatMap((part): RecordedPromptPart[] => {
			if (part.type === "image_url") {
				// Tool-emitted image parts use camelCase imageUrl; user attachments use
				// snake_case image_url. Preserve both, and never journal an empty url:
				// a replayed empty image url is rejected by providers on every
				// subsequent request, permanently poisoning the session.
				const url =
					part.image_url?.url ?? (part as { imageUrl?: { url?: string } }).imageUrl?.url ?? "";
				return url ? [{ type: "image_url" as const, image_url: { url } }] : [];
			}
			return [{ type: "text" as const, text: part.text ?? "" }];
		});
	const text = parts
		.filter((part) => part.type === "text")
		.map((part) => ("text" in part ? part.text : ""))
		.join("\n");
	return {
		type: "user.prompt",
		meta: { occurredAt: Date.now() },
		data: { content: text, parts, ...(origin === undefined ? {} : { origin }) },
	};
}

export interface AgentSession {
	/** Session-owned capabilities the agent may use; the agent never mutates or installs them. */
	goalStore?: GoalStore;
	todoStore?: { todos: TodoState[] };
	taskBudgetStore?: {
		active?: { startedAt: number; tokenBaseline: number; costUsd?: number; checkpointReason?: string };
		save(): Promise<void>;
	};
	isClosed?: () => boolean;
	/** Session-owned turn serializer; the sole turn lock lives behind this. */
	runTurn?: <T>(fn: () => Promise<T>) => Promise<T>;
	turnAbortController?: AbortController | null;
	injectionManager?: { inject(messages: InjectedMessage[]): Promise<void> };
	hookEngine?: HookEngineLike;
	flushSteerBuffer?: (memory: ContextMemory, journal?: JournalWriter) => Promise<unknown>;
}

export interface TurnOrigin {
	kind?: string;
	[key: string]: unknown;
}

export interface PromptOptions {
	onEvent?: (event: RuntimeEvent) => void;
	signal?: AbortSignal;
	/** Caller-assigned turn id propagated to turn events; generated when omitted. */
	turnId?: string;
	onTextDelta?: (delta: string) => void;
	onThinkingDelta?: (delta: string) => void;
	onToolCallDelta?: (delta: { id: string; name: string; argumentsPartial: string }) => void;
	onToolProgress?: (progress: { call: ToolCall; progress: unknown }) => void;
	budgetToolResult?: number;
}

export interface KagekoAgentOptions {
	llm: AgentLlm;
	registry: ToolRegistry;
	kaos: unknown;
	tracker: ProcessTrackerPort;
	permission: PermissionManager;
	telemetry: TelemetryClient;
	mcp?: McpManager;
	session?: AgentSession;
	systemPrompt?: string;
	maxContextSize?: number;
	maxContextSizeSource?: "authoritative" | "catalog" | "configured" | "estimated" | "unknown";
	recordStore?: JournalWriter;
	replayEvents?: DurableEvent[];
	maxSteps?: number;
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
	/** Maximum simultaneously running tool executions per step; defaults to the ToolScheduler default. */
	toolConcurrency?: number;
	/** Per-tool-result character budget applied to model-facing output; a per-call budgetToolResult still wins. */
	budgetToolResult?: number;
	compactThreshold?: number;
	compactionTargetRatio?: number;
	compactionInputRatio?: number;
	compactionMinHistoryEvents?: number;
	onDiagnostic?: (message: string, error?: unknown) => void | Promise<void>;
}

/**
 * Kageko agent: holds conversation memory and executes one turn at a time as
 * directed by its caller. Turn serialization, idle-turn scheduling, and abort
 * plumbing belong to the session owner (the application AgentRuntime); the
 * agent never installs them onto the session.
 */
export class KagekoAgent {
	readonly llm: AgentLlm;
	readonly registry: ToolRegistry;
	readonly kaos: unknown;
	readonly tracker: ProcessTrackerPort;
	readonly permission: PermissionManager;
	readonly mcp?: McpManager;
	readonly session?: AgentSession;
	readonly telemetry: TelemetryClient;
	readonly systemPrompt?: string;
	readonly recordStore?: JournalWriter;
	readonly budgetToolResult?: number;
	readonly maxWallClockMs?: number;
	readonly maxTokens?: number;
	readonly maxCostUsd?: number;
	readonly inputTokenCostUsd?: number;
	readonly outputTokenCostUsd?: number;
	readonly memory: ContextMemory;
	readonly loop: TurnFlow;
	overflowCompactionAttempts = 0;
	maxOverflowCompactionAttempts = 3;
	goalStartTime: number | null = null;
	inOutcomeReminderTurn = false;
	private _lastGoalObjective: string | null | undefined = null;
	private _lastGoalStatus: string | undefined = undefined;
	private _currentSignal: AbortSignal | null = null;
	private readonly onDiagnostic?: (message: string, error?: unknown) => void | Promise<void>;

	constructor({
		llm,
		registry,
		kaos,
		tracker,
		permission,
		telemetry,
		mcp,
		session,
		systemPrompt,
		maxContextSize,
		maxContextSizeSource,
		recordStore,
		replayEvents,
		maxSteps,
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
		toolConcurrency,
		budgetToolResult,
		compactThreshold,
		compactionTargetRatio,
		compactionInputRatio,
		compactionMinHistoryEvents,
		onDiagnostic,
	}: KagekoAgentOptions) {
		this.llm = llm;
		this.registry = registry;
		this.kaos = kaos;
		this.tracker = tracker;
		this.permission = permission;
		this.telemetry = telemetry;
		this.mcp = mcp;
		this.session = session;
		this.systemPrompt = systemPrompt;
		this.recordStore = recordStore;
		this.budgetToolResult = budgetToolResult;
		this.maxWallClockMs = maxWallClockMs;
		this.maxTokens = maxTokens;
		this.maxCostUsd = maxCostUsd;
		this.inputTokenCostUsd = inputTokenCostUsd;
		this.outputTokenCostUsd = outputTokenCostUsd;
		this.memory = new ContextMemory({
			maxContextSize: maxContextSize ?? 128000,
			maxContextSizeSource,
			systemPrompt,
			llm,
			compactThreshold,
			compactionTargetRatio,
			compactionInputRatio,
			minHistoryEvents: compactionMinHistoryEvents,
		});
		this.loop = new TurnFlow({
			maxSteps,
			toolConcurrency,
			maxToolExecutionMs,
			maxToolRetries,
			maxRepeatedToolCalls,
			maxNoProgressSteps,
			maxConsecutiveToolFailures,
			maxToolFailureLoop,
			onDiagnostic,
		});
		this.onDiagnostic = onDiagnostic;
		if (replayEvents?.length) {
			this.replay(replayEvents);
		}
		if (this.session?.goalStore) {
			replayGoalEvents(replayEvents, this.session.goalStore);
		}
	}

	/**
	 * Replay recorded events into context memory so the conversation can continue.
	 */
	replay(events: DurableEvent[]): void {
		let pendingAssistantText: string | null = null;
		const pendingToolCalls: ToolCall[] = [];
		const flushAssistant = () => {
			if (pendingAssistantText !== null || pendingToolCalls.length > 0) {
				this.memory.appendAssistant(pendingAssistantText ?? "", [...pendingToolCalls]);
				pendingAssistantText = null;
				pendingToolCalls.length = 0;
			}
		};

		for (const event of events) {
			switch (event.type) {
				case "usage.updated":
					this.memory.restoreUsage(event.data);
					break;
				case "user.prompt":
					flushAssistant();
					this.memory.appendUser(
						(Array.isArray(event.data.parts) ? event.data.parts : event.data.content) as MessageContent,
						// Preserve the recorded origin (goal lifecycle, steer, idle) so
						// replayed memory matches the live history.
						event.data.origin ?? "user",
					);
					break;
				case "assistant.text":
					flushAssistant();
					pendingAssistantText = event.data.content;
					break;
				case "tool.call":
					pendingToolCalls.push(event.data.call as ToolCall);
					break;
				case "tool.result": {
					flushAssistant();
					const call = event.data.call as ToolCall;
					const result = event.data.result;
					this.memory.appendToolResult(
						call.id,
						result.output as import("../context/projector.js").MessageContent,
						result.isError,
					);
					break;
				}
				case "turn.end":
					flushAssistant();
					break;
			}
		}
		flushAssistant();
	}

	async prompt(
		text: string | PromptPart[],
		{
			onEvent,
			signal: externalSignal,
			turnId,
			onTextDelta,
			onThinkingDelta,
			onToolCallDelta,
			onToolProgress,
			budgetToolResult,
		}: PromptOptions = {},
	): Promise<TurnRunResult> {
		if (this.session?.isClosed?.()) {
			throw new Error("Session is closed");
		}

		// Turn serialization is owned by the session (AgentRuntime.runTurn);
		// the agent only executes the turn it was asked to run.
		const abortController = new AbortController();
		if (externalSignal?.aborted) {
			abortController.abort(externalSignal.reason);
		}
		const onExternalAbort = () => abortController.abort(externalSignal?.reason);
		if (externalSignal) {
			externalSignal.addEventListener("abort", onExternalAbort, { once: true });
		}
		const session = this.session;
		if (session) {
			session.turnAbortController = abortController;
		}
		this._currentSignal = abortController.signal;

		const runTurn = async (): Promise<TurnRunResult> => {
			try {
				const taskBudget = await this._beginTaskBudget();
				await session?.flushSteerBuffer?.(this.memory, this.recordStore);
				await this.recordStore?.append(promptRecord(text));
				this.memory.appendUser(text as MessageContent);
				await this.memory.maybeCompact({ signal: this._currentSignal ?? undefined });

				const messages = this.memory.history;
				await session?.injectionManager?.inject(messages as InjectedMessage[]);

				const hooks = this._buildTurnHooks();
				const result = await this.loop.run({
					llm: this._llmRecordingUsage(),
					registry: this.registry,
					messages,
					// Compaction replaces memory.history mid-turn; the turn must
					// re-read the live array instead of the snapshot above.
					getMessages: () => this.memory.history as TurnMessage[],
					kaos: this.kaos,
					tracker: this.tracker,
					permission: this.permission,
					mcp: this.mcp,
					session,
					telemetry: this.telemetry,
					systemPrompt: this.systemPrompt,
					onEvent: (event: RuntimeEvent) => {
						onEvent?.(event);
					},
					recordStore: this.recordStore,
					hooks,
					signal: abortController.signal,
					turnId,
					onTextDelta,
					onThinkingDelta,
					onToolCallDelta,
					onToolProgress,
					budgetToolResult: budgetToolResult ?? this.budgetToolResult,
					maxWallClockMs: taskBudget?.remainingWallClockMs,
					maxTokens: taskBudget?.remainingTokens,
					maxCostUsd: taskBudget?.remainingCostUsd,
					inputTokenCostUsd: this.inputTokenCostUsd,
					outputTokenCostUsd: this.outputTokenCostUsd,
				} as unknown as TurnRunOptions);
				await this._finishTaskBudget(result);
				return result;
			} catch (err) {
				// A user-initiated abort is a normal end of the turn, not a goal
				// failure: never pause the goal for it (T-m11).
				const goal = abortController.signal.aborted ? undefined : session?.goalStore?.activeGoal;
				if (goal && goal.status === "active") {
					const reason = String((err as Error).message ?? err);
					const goalId = requireGoalId(goal);
					// Best-effort like the other goal appends: a journal fault here
					// must not mask the original turn error (Task 4.2 review).
					await this._tryJournalGoalEvent({
						type: "goal.paused",
						data: { goalId, reason },
					});
					goal.status = "paused";
					goal.pauseReason = reason;
				}
				throw err;
			}
		};

		try {
			if (session?.runTurn) {
				return await session.runTurn(runTurn);
			}
			return await runTurn();
		} finally {
			if (externalSignal) {
				externalSignal.removeEventListener("abort", onExternalAbort);
			}
			if (session?.turnAbortController === abortController) {
				session.turnAbortController = null;
			}
			if (this._currentSignal === abortController.signal) {
				this._currentSignal = null;
			}
		}
	}

	private async _beginTaskBudget(): Promise<{ remainingWallClockMs?: number; remainingTokens?: number; remainingCostUsd?: number } | undefined> {
		if (this.maxWallClockMs === undefined && this.maxTokens === undefined) return undefined;
		const store = this.session?.taskBudgetStore;
		if (!store) return { remainingWallClockMs: this.maxWallClockMs, remainingTokens: this.maxTokens, remainingCostUsd: this.maxCostUsd };
		if (!store.active?.checkpointReason) {
			store.active = { startedAt: Date.now(), tokenBaseline: this.memory.totalTokensUsed, costUsd: 0 };
			await store.save();
		}
		const active = store.active;
		return {
			remainingWallClockMs: this.maxWallClockMs === undefined ? undefined : Math.max(0, this.maxWallClockMs - (Date.now() - active.startedAt)),
			remainingTokens: this.maxTokens === undefined ? undefined : Math.max(0, this.maxTokens - (this.memory.totalTokensUsed - active.tokenBaseline)),
			remainingCostUsd: this.maxCostUsd === undefined ? undefined : Math.max(0, this.maxCostUsd - (active.costUsd ?? 0)),
		};
	}

	private async _finishTaskBudget(result: TurnRunResult): Promise<void> {
		const store = this.session?.taskBudgetStore;
		if (!store?.active) return;
		store.active.costUsd = (store.active.costUsd ?? 0) + result.costUsd;
		const stopReason = result.stopReason;
		if (stopReason === "slice_exhausted" || stopReason === "stalled" || stopReason === "budget_exhausted") {
			store.active.checkpointReason = stopReason;
			await store.save();
			return;
		}
		store.active = undefined;
		await store.save();
	}

	/**
	 * Execute one idle (system-triggered) turn prepared by the session owner.
	 * The caller owns the closed-session check, turn serialization, and abort
	 * plumbing; the agent only runs the turn against its own memory.
	 */
	async runIdleTurn(prompt: string, origin?: TurnOrigin, signal?: AbortSignal): Promise<TurnRunResult> {
		this._currentSignal = signal ?? null;
		try {
			await this.recordStore?.append(promptRecord(prompt, origin?.kind));
			this.memory.appendUser(prompt, origin?.kind ?? "system_trigger");
			await this.memory.maybeCompact({ signal: this._currentSignal ?? undefined });
			const messages = this.memory.history;
			await this.session?.injectionManager?.inject(messages as InjectedMessage[]);
			const hooks = this._buildTurnHooks();
			return await this.loop.run({
				llm: this._llmRecordingUsage(),
				registry: this.registry,
				messages,
				// See prompt(): the turn re-reads the live history so mid-turn
				// compaction is not invisible to it.
				getMessages: () => this.memory.history as TurnMessage[],
				kaos: this.kaos,
				tracker: this.tracker,
				permission: this.permission,
				mcp: this.mcp,
				session: this.session,
				telemetry: this.telemetry,
				systemPrompt: this.systemPrompt,
				recordStore: this.recordStore,
				hooks,
				onEvent: (event: RuntimeEvent) => {
					this.telemetry.record(event);
				},
				signal,
				budgetToolResult: this.budgetToolResult,
				maxWallClockMs: this.maxWallClockMs,
				maxTokens: this.maxTokens,
				maxCostUsd: this.maxCostUsd,
				inputTokenCostUsd: this.inputTokenCostUsd,
				outputTokenCostUsd: this.outputTokenCostUsd,
			} as unknown as TurnRunOptions);
		} finally {
			if (this._currentSignal === (signal ?? null)) {
				this._currentSignal = null;
			}
		}
	}

	/** User-triggered compaction; the caller guarantees the session is idle. */
	async requestCompact(instruction?: string): Promise<CompactResult> {
		return this.memory.compact({ signal: this._currentSignal ?? undefined, instruction });
	}

	/**
	 * Default tool-execution hooks wiring the session hook engine and the
	 * permission service into the turn flow. The agent owns these services,
	 * so the wiring lives here rather than inside the turn runner.
	 */
	private _buildDefaultHooks(): TurnFlowHooks {
		const session = this.session as unknown as SessionLike | undefined;
		const permission = this.permission;
		return {
			prepareToolExecution: async (payload: HookPayload) => {
				const { toolCall, args } = payload as HookPayload & { toolCall: LlmToolCall; args: Record<string, unknown> };
				const block = await session?.hookEngine?.triggerBlock?.("PreToolUse", {
					toolName: toolCall.name,
					args,
				});
				if (block) {
					return {
						block: true,
						reason: `Blocked by hook: ${block.reason || block.message}`,
					};
				}
				return undefined;
			},
			authorizeToolExecution: async (payload: HookPayload) => {
				const { toolCall, args, execution, signal } = payload as HookPayload & {
					toolCall: LlmToolCall;
					args: Record<string, unknown>;
					execution?: ToolExecution;
					signal?: AbortSignal;
				};
				const decision = await permission.authorize(toolCall.name, args, { session, execution, signal });
				if (!decision.approved) {
					return { block: true, reason: decision.reason };
				}
				return decision.feedback ? { approvalFeedback: decision.feedback } : undefined;
			},
			finalizeToolResult: async (payload: HookPayload) => {
				const { toolCall, args, result, signal } = payload as HookPayload & {
					toolCall: LlmToolCall;
					args: Record<string, unknown>;
					result?: ToolResult;
					signal?: AbortSignal;
				};
				await session?.hookEngine?.trigger("PostToolUse", {
					toolName: toolCall.name,
					args,
					result,
					signal,
				});
				if (result?.isError) {
					await session?.hookEngine?.trigger("PostToolUseFailure", {
						toolName: toolCall.name,
						args,
						result,
						signal,
					});
				}
				return undefined;
			},
		};
	}

	private _buildTurnHooks(): TurnFlowHooks {
		// Invariant: the default hook keys (prepareToolExecution /
		// authorizeToolExecution / finalizeToolResult) and the agent-level keys
		// below (beforeStep / afterStep / shouldContinueAfterStop /
		// handleOverflowError) never overlap, so spreading composes the two
		// sets semantically instead of overriding either one.
		return {
			...this._buildDefaultHooks(),
			beforeStep: async ({ step: _step }) => {
				this.overflowCompactionAttempts = 0;

				await this.memory.maybeCompact({ signal: this._currentSignal ?? undefined });
				await this.session?.flushSteerBuffer?.(this.memory, this.recordStore);
				const messages = this.memory.history;
				await this.session?.injectionManager?.inject(messages as InjectedMessage[]);

				const goal = this.session?.goalStore?.activeGoal;
				if (!goal || goal.status !== "active") {
					this.goalStartTime = null;
				}
				if (goal && goal.status === "active") {
					if (
						this.goalStartTime === null ||
						goal.objective !== this._lastGoalObjective ||
						this._lastGoalStatus === "paused"
					) {
						this.goalStartTime = Date.now();
						this._lastGoalObjective = goal.objective;
						this.inOutcomeReminderTurn = false;
					}

					if (goal.budget?.maxTokens && this.memory.totalTokensUsed >= goal.budget.maxTokens) {
						const reason = "Token budget exceeded";
						const goalId = requireGoalId(goal);
						await this._tryJournalGoalEvent({
							type: "goal.blocked",
							data: { goalId, reason },
						});
						goal.status = "blocked";
						goal.blockReason = reason;
						await this._journalGoalMessage(`Goal blocked: ${reason}`, "goal_blocked");
						return { block: true, reason };
					}

					if (goal.budget?.maxWallClockMs && this.goalStartTime) {
						const elapsed = Date.now() - this.goalStartTime;
						if (elapsed > goal.budget.maxWallClockMs) {
							const reason = "Wall-clock budget exceeded";
							const goalId = requireGoalId(goal);
							await this._tryJournalGoalEvent({
								type: "goal.blocked",
								data: { goalId, reason },
							});
							goal.status = "blocked";
							goal.blockReason = reason;
							await this._journalGoalMessage(`Goal blocked: ${reason}`, "goal_blocked");
							return { block: true, reason };
						}
					}
				}
				this._lastGoalStatus = goal?.status;
			},
			handleOverflowError: async ({ error }) => {
				if (!isContextOverflowError(error)) return { recovered: false };
				this.overflowCompactionAttempts += 1;
				if (this.overflowCompactionAttempts > this.maxOverflowCompactionAttempts) {
					return { recovered: false };
				}
				await this.session?.hookEngine?.trigger("PreCompact", { reason: "context_overflow" });
				const compacted = await this.memory.compact({ signal: this._currentSignal ?? undefined });
				await this.session?.hookEngine?.trigger("PostCompact", { reason: "context_overflow" });
				this.telemetry?.record({
					type: "compaction_finished",
					reason: "context_overflow",
					outcome: compacted.outcome,
					tokensBefore: compacted.tokensBefore,
					tokensAfter: compacted.tokensAfter,
				});
				return { recovered: compacted.outcome === "compacted" && compacted.tokensAfter < compacted.tokensBefore };
			},
			afterStep: async () => {
				// Usage is recorded into memory the moment each chat call
				// resolves (see _llmRecordingUsage); an abort mid-tool-batch
				// must not lose the completed call's cumulative usage (T-m8).
				this.overflowCompactionAttempts = 0;
			},
			shouldContinueAfterStop: async () => {
				const goal = this.session?.goalStore?.activeGoal;
				// TurnFlow only calls this hook with a model stop reason
				// (end_turn/unknown/filtered/max_tokens/paused) — never
				// max_steps, which the runner applies after this hook returns.
				if (!goal || goal.status !== "active") {
					// If goal reached a terminal state this turn, give one outcome-reminder step.
					if (
						goal &&
						(goal.status === "completed" || goal.status === "blocked" || goal.status === "failed") &&
						!this.inOutcomeReminderTurn
					) {
						this.inOutcomeReminderTurn = true;
						const origin = goal.status === "completed" ? "goal_completion" : "goal_blocked";
						await this._journalGoalMessage(
							`Goal reached: ${goal.objective}. Please provide a concise final summary for the user.`,
							origin,
						);
						return { continue: true };
					}
					return { continue: false };
				}

				if (goal.budget?.maxTurns && (goal.turnsUsed ?? 0) >= goal.budget.maxTurns) {
					const reason = "A configured budget was reached";
					const goalId = requireGoalId(goal);
					await this._tryJournalGoalEvent({
						type: "goal.blocked",
						data: { goalId, reason },
					});
					goal.status = "blocked";
					goal.blockReason = reason;
					await this._journalGoalMessage(`Goal blocked: ${reason}`, "goal_blocked");
					return { continue: false };
				}

				// Count from 0 for goals whose counter was never recorded;
				// create_goal initializes turnsUsed to 1 for the creating turn,
				// so maxTurns=N allows exactly N counted turns (T-m1).
				goal.turnsUsed = (goal.turnsUsed ?? 0) + 1;
				// Journal the incremented counter so replay restores the budget
				// spend instead of resetting it on restart.
				await this._tryJournalGoalEvent({
					type: "goal.updated",
					data: {
						goal: {
							id: requireGoalId(goal),
							description: goal.objective,
							status: goal.status,
							budget: goal.budget,
							turnsUsed: goal.turnsUsed,
							createdAt: goal.createdAt,
						},
					},
				});
				await this._journalGoalMessage("Continue working toward the goal.", "goal_continue");
				return { continue: true };
			},
		};
	}

	/**
	 * Goal lifecycle messages must survive restart: journal them as
	 * `user.prompt` events with an origin (the established pattern for
	 * non-user prompt injections) in addition to appending them to memory,
	 * so `replay()` reconstructs the same history. The journal append is
	 * best-effort: a faulted journal must not turn goal continuation into a
	 * turn error (review follow-up to T-M5) — memory always gets the message.
	 */
	private async _journalGoalMessage(content: string, origin: string): Promise<void> {
		try {
			await this.recordStore?.append(promptRecord(content, origin));
		} catch (err) {
			this._reportDiagnostic("Goal lifecycle message failed to journal.", err);
		}
		this.memory.appendUser(content, origin);
	}

	/**
	 * Goal bookkeeping (`goal.updated` / `goal.blocked` / `goal.paused`) is
	 * in-memory first; the durable record is best-effort. A journal fault must
	 * not convert a continuation, budget decision, or pause into a turn error.
	 */
	private async _tryJournalGoalEvent(
		event: DurableEventInput<"goal.updated"> | DurableEventInput<"goal.blocked"> | DurableEventInput<"goal.paused">,
	): Promise<void> {
		try {
			await this.recordStore?.append(event);
		} catch (err) {
			this._reportDiagnostic("Goal bookkeeping event failed to journal.", err);
		}
	}

	/**
	 * Wrap the LLM so per-response usage lands in memory the moment a chat
	 * call resolves — not in afterStep, which an abort mid-tool-batch would
	 * never reach (T-m8). The turn runner emits the durable `usage.updated`
	 * event at the same point.
	 */
	private _llmRecordingUsage(): AgentLlm {
		const llm = this.llm;
		const wrapped: AgentLlm = {
			chat: async (options: ChatOptions) => {
				const response = await llm.chat(options);
				if (response?.usage) {
					this.memory.recordUsage(response.usage);
				}
				return response;
			},
		};
		if (llm.isRetryableError) {
			wrapped.isRetryableError = llm.isRetryableError.bind(llm);
		}
		if (llm.recoverAfterError) {
			wrapped.recoverAfterError = llm.recoverAfterError.bind(llm);
		}
		return wrapped;
	}

	private _reportDiagnostic(message: string, error?: unknown): void {
		try {
			void Promise.resolve(this.onDiagnostic?.(message, error)).catch(() => {});
		} catch {
			// Diagnostics are observational.
		}
	}
}

/** Adapter used by application services; keeps prompt execution on the real agent path. */
export function createPromptExecutor(
	agent: Pick<KagekoAgent, "prompt">,
): (input: { readonly parts: readonly { readonly type: string; readonly text?: string }[] }) => Promise<void> {
	return async (input) => {
		const text = input.parts
			.filter((part) => part.type === "text")
			.map((part) => part.text ?? "")
			.join("\n");
		await agent.prompt(text);
	};
}

function requireGoalId(goal: GoalData): string {
	if (!goal.id) {
		throw new Error("Active goal is missing its durable id");
	}
	return goal.id;
}

function isContextOverflowError(error: unknown): boolean {
	if (!error || typeof error !== "object") return false;
	const err = error as { code?: unknown; status?: unknown; message?: unknown };
	if (err.code === "CONTEXT_OVERFLOW") return true;
	if (err.status === 413) return true;
	const message = String(err.message ?? error).toLowerCase();
	const codes = [
		"context length",
		"maximum context",
		"context_overflow",
		"context window",
		"token limit",
		"max tokens",
		"request too large",
		"payload too large",
		"413",
	];
	return codes.some((c) => message.includes(c));
}
