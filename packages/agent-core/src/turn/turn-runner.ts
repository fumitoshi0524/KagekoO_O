import * as crypto from "node:crypto";
import type { ChatMessage, ChatOptions, ChatResponse, LlmToolCall as ToolCall } from "../ports/llm.js";
import {
	EVENT_SCHEMA_VERSION,
	type DurableEvent,
	type DurableEventContext,
	type DurableEventDataMap,
	type DurableEventInput,
	type DurableEventType,
	type LiveEvent,
	type LiveEventDataMap,
	type LiveEventType,
	type RuntimeEvent,
} from "@kageko/protocol";
import { project } from "../context/projector.js";
import { ToolScheduler, ToolAccesses } from "./tool-scheduler.js";
import { createUserFeedbackEvent } from "../memory/learning/event.js";
import type { TelemetryClient } from "../telemetry/index.js";
import { canonicalizeFileAccesses } from "../tools/accesses.js";
import type { ToolExecution as RegistryToolExecution } from "../tools/types.js";
import { normalizeObservationText, ToolFailureGuardrail } from "./tool-guardrail.js";

export const DEFAULT_TOOL_RESULT_BUDGET = 100000;

function safeStringify(value: unknown): string | null {
	try {
		return JSON.stringify(value);
	} catch {
		return null;
	}
}

const SENSITIVE_ARG_KEYS = /key|token|password|secret|auth|credential|api[_-]?key/i;
const MAX_TELEMETRY_ARG_STRING = 1000;

/**
 * Errors that escaped `_chatWithRetry` after partial streamed output was
 * already published. Retrying the request — for any reason, including
 * context-overflow recovery — would duplicate the visible text, so the outer
 * overflow loop must refuse recovery for these too (T-m7).
 */
const partialOutputErrors = new WeakSet<object>();

function markPartialOutputError(error: unknown): void {
	if (error !== null && (typeof error === "object" || typeof error === "function")) {
		partialOutputErrors.add(error as object);
	}
}

function isPartialOutputError(error: unknown): boolean {
	return (
		error !== null &&
		(typeof error === "object" || typeof error === "function") &&
		partialOutputErrors.has(error as object)
	);
}

function sanitizeArgsForTelemetry(args: unknown): unknown {
	if (args === null || typeof args !== "object") {
		return args;
	}
	const out: Record<string, unknown> | unknown[] = Array.isArray(args) ? [] : {};
	for (const [k, v] of Object.entries(args as Record<string, unknown>)) {
		if (typeof v === "string") {
			let value = v;
			if (SENSITIVE_ARG_KEYS.test(k)) {
				value = "[redacted]";
			} else if (value.length > MAX_TELEMETRY_ARG_STRING) {
				value = value.slice(0, MAX_TELEMETRY_ARG_STRING) + "\n... (truncated)";
			}
			(out as Record<string, unknown>)[k] = value;
		} else if (typeof v === "object" && v !== null) {
			(out as Record<string, unknown>)[k] = sanitizeArgsForTelemetry(v);
		} else {
			(out as Record<string, unknown>)[k] = v;
		}
	}
	return out;
}

export type TurnMessage = ChatMessage & { origin?: string };

export interface ToolResult {
	output?: string | Array<Record<string, unknown>>;
	isError?: boolean;
	stopTurn?: boolean;
	skipped?: boolean;
	truncated?: boolean;
	[key: string]: unknown;
}

export type ToolExecution = RegistryToolExecution & {
	toolName?: string;
	accesses: ToolAccesses;
	execute: (args: Record<string, unknown>, ctx: ToolExecutionContext) => Promise<ToolResult> | ToolResult;
};

export interface ToolExecutionContext {
	kaos?: unknown;
	tracker?: { stopForeground?: () => Promise<unknown> };
	permission?: unknown;
	mcp?: unknown;
	session?: SessionLike;
	subagentHost?: unknown;
	executionMetadata?: unknown;
	signal?: AbortSignal;
	onProgress?: (progress: unknown) => void;
	/** Stable lineage available to tools that delegate work. */
	parentActivityId?: string;
	parentToolCallId?: string;
	[key: string]: unknown;
}

/**
 * Session-owned hook engine surface used by the turn runner and the agent's
 * default hooks. `triggerBlock` is optional: sessions without blocking hooks
 * only implement `trigger`.
 */
export interface HookEngineLike {
	triggerBlock?(
		event: string,
		args: Record<string, unknown>,
	): Promise<{ reason?: string; message?: string } | undefined>;
	trigger(event: string, args: Record<string, unknown>): Promise<unknown>;
}

export interface SessionLike {
	sessionId?: string;
	hookEngine?: HookEngineLike;
	learningBus?: { enqueue(event: unknown): void };
	subagentHost?: unknown;
	idempotencyStore?: {
		reserve(key: string): Promise<{ state: "new" | "pending" | "completed"; result?: ToolResult }>;
		complete(key: string, result: ToolResult): Promise<void>;
		release?(key: string): Promise<void>;
	};
	[key: string]: unknown;
}

export interface JournalWriterLike {
	readonly sessionId: string;
	readonly fault?: Error;
	append<K extends DurableEventType>(event: DurableEventInput<K>): Promise<DurableEvent<K>>;
}

/** Narrow provider port required by the turn runner. */
export interface AgentLlm {
	chat(options: ChatOptions): Promise<ChatResponse>;
	isRetryableError?: (error: unknown) => boolean;
	recoverAfterError?: (error: unknown, context: { attempt: number; signal: AbortSignal }) => Promise<boolean>;
}

export interface RegistryLike {
	asFunctions(): ChatOptions["tools"];
	validateArgs(name: string, args: Record<string, unknown>): void;
	resolveExecution(name: string, args: Record<string, unknown>, ctx: { kaos?: unknown }): ToolExecution;
}

export type HookPayload = Record<string, unknown> & { signal?: AbortSignal };
export type HookResultPayload =
	| {
			block?: boolean;
			reason?: string;
			syntheticResult?: ToolResult;
			updatedArgs?: Record<string, unknown>;
			executionMetadata?: unknown;
			approvalFeedback?: string;
	  }
	| undefined;

export interface TurnFlowHooks {
	beforeStep?: (payload: HookPayload) => Promise<{ block?: boolean; reason?: string } | undefined>;
	afterStep?: (payload: HookPayload) => Promise<{ stopTurn?: boolean; recovered?: boolean } | undefined>;
	prepareToolExecution?: (payload: HookPayload) => Promise<HookResultPayload>;
	authorizeToolExecution?: (payload: HookPayload) => Promise<HookResultPayload>;
	finalizeToolResult?: (payload: HookPayload) => Promise<ToolResult | undefined>;
	shouldContinueAfterStop?: (payload: HookPayload) => Promise<{ continue?: boolean } | undefined>;
	handleOverflowError?: (payload: HookPayload) => Promise<{ recovered?: boolean } | undefined>;
	[key: string]: ((payload: HookPayload) => Promise<unknown>) | undefined;
}

export interface TurnFlowOptions {
	maxSteps?: number;
	maxRetriesPerStep?: number;
	maxConsecutiveToolFailures?: number;
	/** Consecutive failures of one tool — with any arguments — before a stalled checkpoint. */
	maxToolFailureLoop?: number;
	/** A slice guard only. Hitting it checkpoints the turn; it is not task completion. */
	maxRepeatedToolCalls?: number;
	/** Consecutive identical successful observations before declaring no progress. */
	maxNoProgressSteps?: number;
	/** Hard cap for one tool execution; foreground work is stopped on expiry. */
	maxToolExecutionMs?: number;
	/** Extra attempts for a retryable, read-only tool failure. Mutating tools are never automatically retried. */
	maxToolRetries?: number;
	/** Maximum simultaneously running tool executions per step; defaults to the ToolScheduler default. */
	toolConcurrency?: number;
	onDiagnostic?: (message: string, error?: unknown) => void | Promise<void>;
}

export interface TurnRunOptions {
	llm?: AgentLlm;
	registry?: RegistryLike;
	messages?: TurnMessage[];
	/**
	 * Live accessor for the authoritative message list. When provided, the
	 * turn re-reads it at every step boundary and after overflow recovery, so
	 * mid-turn compaction (which replaces the memory history array) becomes
	 * visible to the in-flight turn instead of leaving it on an orphaned array.
	 */
	getMessages?: () => TurnMessage[];
	kaos?: unknown;
	tracker?: ToolExecutionContext["tracker"];
	permission?: unknown;
	mcp?: unknown;
	session?: SessionLike;
	telemetry?: TelemetryClient;
	systemPrompt?: string;
	onEvent?: (event: RuntimeEvent) => void;
	recordStore?: JournalWriterLike;
	hooks?: TurnFlowHooks;
	budgetToolResult?: number;
	signal?: AbortSignal;
	/** Caller-assigned turn id; a fresh one is generated when omitted. */
	turnId?: string;
	onTextDelta?: (delta: string) => void;
	onThinkingDelta?: (delta: string) => void;
	onToolCallDelta?: (delta: { id: string; name: string; argumentsPartial: string }) => void;
	onToolProgress?: (progress: { call: ToolCall; progress: unknown }) => void;
	toolGraceMs?: number;
	/** Task-level wall-clock budget for this invocation. */
	maxWallClockMs?: number;
	/** Task-level aggregate model-token budget for this invocation. */
	maxTokens?: number;
	/** Optional provider-price budget. Both per-token prices must be supplied with this cap. */
	maxCostUsd?: number;
	inputTokenCostUsd?: number;
	outputTokenCostUsd?: number;
}

export interface TurnRunResult {
	content: string;
	stopReason: string;
	tokensUsed: number;
	costUsd: number;
}

interface PendingResult {
	call: ToolCall;
	args: Record<string, unknown>;
	prepare: HookResultPayload;
	execution: ToolExecution;
	executionMetadata: unknown;
	idempotencyKey?: string;
	approvalFeedback?: string;
	key: string | null;
	promise: Promise<ToolResult>;
	/** Set when the primary's drain completes; duplicates read it at their own provider position. */
	finalResult?: ToolResult;
}

/**
 * One entry per provider tool call, in provider order. Outcomes that settle
 * during preparation (skip/abort/dedup hit, hook or validation failure,
 * synthetic result, denial) are collected here and journaled during the
 * drain — not inline — so the journal's tool.result sequence always matches
 * provider order even when settled and executed calls mix. Duplicate-key
 * calls share their primary's result but journal at their own position.
 */
type BatchEntry =
	| { kind: "settled"; call: ToolCall; result: ToolResult }
	| { kind: "duplicate"; call: ToolCall; initialArgs: Record<string, unknown>; primary: PendingResult }
	| { kind: "pending"; pending: PendingResult };

type EmitDurable = <K extends DurableEventType>(
	type: K,
	data: DurableEventDataMap[K],
	context?: DurableEventContext,
) => Promise<DurableEvent<K>>;

type EmitLive = <K extends LiveEventType>(
	type: K,
	data: LiveEventDataMap[K],
	context?: DurableEventContext,
) => Promise<LiveEvent<K>>;

/**
 * TurnFlow: a kimi-code-style turn runner.
 *
 * Each `run()` call executes a single logical turn; all per-turn state is
 * local to the call, so one TurnFlow instance is safely reused across turns
 * (KagekoAgent does exactly this). A turn provides:
 * - explicit step loop with `step.begin` / `step.end` events
 * - beforeStep / afterStep hooks
 * - prepareToolExecution / authorizeToolExecution / finalizeToolResult hooks
 * - shouldContinueAfterStop hook for autonomous continuation
 * - LLM retry with exponential backoff
 * - same-step tool-call deduplication
 * - context-overflow recovery via compaction hook
 */
export class TurnFlow {
	readonly maxSteps: number;
	readonly maxRetriesPerStep: number;
	readonly maxConsecutiveToolFailures: number;
	readonly maxToolFailureLoop: number;
	readonly maxRepeatedToolCalls: number;
	readonly maxNoProgressSteps: number;
	readonly maxToolExecutionMs?: number;
	readonly maxToolRetries: number;
	readonly toolConcurrency?: number;
	private readonly onDiagnostic?: (message: string, error?: unknown) => void | Promise<void>;

	constructor({
		maxSteps = 10,
		maxRetriesPerStep = 3,
		maxConsecutiveToolFailures = 3,
		maxToolFailureLoop = 8,
		maxRepeatedToolCalls = 12,
		maxNoProgressSteps = 8,
		maxToolExecutionMs,
		maxToolRetries = 2,
		toolConcurrency,
		onDiagnostic,
	}: TurnFlowOptions = {}) {
		this.maxSteps = clampPositiveInteger(maxSteps, 10);
		this.maxRetriesPerStep = clampPositiveInteger(maxRetriesPerStep, 3);
		this.maxConsecutiveToolFailures = clampPositiveInteger(maxConsecutiveToolFailures, 3);
		this.maxToolFailureLoop = clampPositiveInteger(maxToolFailureLoop, 8);
		this.maxRepeatedToolCalls = clampPositiveInteger(maxRepeatedToolCalls, 12);
		this.maxNoProgressSteps = clampPositiveInteger(maxNoProgressSteps, 8);
		this.maxToolExecutionMs = maxToolExecutionMs === undefined ? undefined : clampPositiveInteger(maxToolExecutionMs, 300_000);
		this.maxToolRetries = clampNonNegativeInteger(maxToolRetries, 2);
		this.toolConcurrency = toolConcurrency;
		this.onDiagnostic = onDiagnostic;
	}

	async run({
		llm,
		registry,
		messages: initialMessages,
		getMessages,
		kaos,
		tracker,
		permission,
		mcp,
		session,
		telemetry,
		systemPrompt,
		onEvent,
		recordStore,
		hooks = {},
		budgetToolResult,
		signal,
		onTextDelta,
		onThinkingDelta,
		onToolCallDelta,
		onToolProgress,
		toolGraceMs = 5000,
		maxWallClockMs,
		maxTokens,
		maxCostUsd,
		inputTokenCostUsd,
		outputTokenCostUsd,
		turnId: requestedTurnId,
	}: TurnRunOptions = {}): Promise<TurnRunResult> {
		if (!llm) {
			throw new TypeError("TurnFlow.run requires llm");
		}
		if (!registry) {
			throw new TypeError("TurnFlow.run requires registry");
		}
		let messages = initialMessages ?? getMessages?.();
		if (!messages) {
			throw new TypeError("TurnFlow.run requires messages or getMessages");
		}
		if (
			maxCostUsd !== undefined &&
			(inputTokenCostUsd === undefined || outputTokenCostUsd === undefined)
		) {
			throw new TypeError("TurnFlow.run requires inputTokenCostUsd and outputTokenCostUsd when maxCostUsd is set");
		}
		// Re-read the authoritative message list: compaction replaces the
		// history array wholesale, so a reference captured at turn start goes
		// stale mid-turn (overflow recovery would retry the same oversized
		// payload, and post-compaction messages would land in an orphaned array).
		const refreshMessages = (): void => {
			if (getMessages) {
				messages = getMessages();
			}
		};
		const tools = registry.asFunctions();
		const dedup = new ToolCallDedupTracker(this.maxRepeatedToolCalls);
		const progressGuardrail = new ToolProgressGuardrail(this.maxNoProgressSteps);
		const turnId = requestedTurnId ?? generateTurnId();
		const resultBudget = budgetToolResult ?? DEFAULT_TOOL_RESULT_BUDGET;
		const failureGuardrail = new ToolFailureGuardrail({
			maxConsecutiveFailures: this.maxConsecutiveToolFailures,
			maxFailureLoop: this.maxToolFailureLoop,
		});

		const turnAbort = new AbortController();
		const turnSignal = turnAbort.signal;
		const onExternalAbort = () => turnAbort.abort(signal?.reason);
		if (signal) {
			if (signal.aborted) {
				turnAbort.abort(signal.reason);
			} else {
				signal.addEventListener("abort", onExternalAbort, { once: true });
			}
		}

		let ephemeralSequence = 0;
		const sessionId = recordStore?.sessionId ?? session?.sessionId ?? `ephemeral-${turnId}`;
		const publish = (event: RuntimeEvent): void => {
			try {
				onEvent?.(event);
			} catch {
				// Observers do not control the turn or journal.
			}
		};

		const emitDurable: EmitDurable = async (type, data, context = {}) => {
			const input = {
				type,
				meta: { ...context, turnId: context.turnId ?? turnId, activityId: context.activityId ?? turnId },
				data,
			} as DurableEventInput<typeof type>;
			const event = recordStore
				? await recordStore.append(input)
				: ({
						type,
						meta: {
							schemaVersion: EVENT_SCHEMA_VERSION,
							eventId: crypto.randomUUID(),
							sequence: ++ephemeralSequence,
							sessionId,
							occurredAt: context.occurredAt ?? Date.now(),
							recordedAt: Date.now(),
							...context,
							turnId: context.turnId ?? turnId,
							activityId: context.activityId ?? turnId,
						},
						data,
					} as DurableEvent<typeof type>);
			publish(event);
			return event;
		};

		const emitLive: EmitLive = async (type, data, context = {}) => {
			const event = {
				type,
				meta: {
					schemaVersion: EVENT_SCHEMA_VERSION,
					eventId: crypto.randomUUID(),
					sessionId,
					occurredAt: context.occurredAt ?? Date.now(),
					...context,
					turnId: context.turnId ?? turnId,
					activityId: context.activityId ?? turnId,
				},
				data,
			} as LiveEvent<typeof type>;
			publish(event);
			return event;
		};

		let stopReason = "slice_exhausted";
		let checkpointReason: "budget_exhausted" | "stalled" | "slice_exhausted" | undefined;
		let lastError: unknown;
		let finalContent = "";
		let tokensUsed = 0;
		let costUsd = 0;
		const startedAt = Date.now();
		// Tracks whether turn.started was actually journaled; the finally below
		// must not emit an unmatched turn.end when it was not.
		let turnStarted = false;

		try {
			// Inside the try so a faulted journal here still runs the finally
			// below (external abort listener cleanup, turnAbort).
			await emitDurable("turn.started", {});
			turnStarted = true;

			for (let step = 1; step <= this.maxSteps; step++) {
				if (maxWallClockMs !== undefined && Date.now() - startedAt >= maxWallClockMs) {
					stopReason = "budget_exhausted";
					checkpointReason = "budget_exhausted";
					break;
				}
				if (maxTokens !== undefined && tokensUsed >= maxTokens) {
					stopReason = "budget_exhausted";
					checkpointReason = "budget_exhausted";
					break;
				}
				if (maxCostUsd !== undefined && costUsd >= maxCostUsd) {
					stopReason = "budget_exhausted";
					checkpointReason = "budget_exhausted";
					break;
				}
				// Set once the step spawns tool executions; invoked from the step
				// catch so a mid-prep/mid-drain throw (e.g. a journal fault on
				// tool.call) cannot leave scheduler executions parked on the
				// batch gate or rejected unobserved (kimi-code's
				// runToolCallBatch allSettled pattern).
				let settleSpawnedExecutions: (() => Promise<void>) | undefined;
				try {
					throwIfAborted(turnSignal);
					telemetry?.record({ type: "turn.step", step, turnId });

					// step.begin precedes the beforeStep hook so a blocking hook
					// still produces a matched begin/end pair in the journal.
					await emitDurable("step.begin", { step }, { stepId: String(step) });

					let before: { block?: boolean; reason?: string } | undefined;
					try {
						before = await hooks.beforeStep?.({ turnId, stepNumber: step, messages, llm, signal: turnSignal });
						if (before?.block) {
							throw new Error(before.reason ?? `Step ${step} blocked`);
						}
					} catch (err) {
						lastError = err;
						stopReason = "error";
						await emitDurable("step.end", { step, stopReason: "error" }, { stepId: String(step) });
						break;
					}

					// beforeStep hooks may compact or inject; pick up the live history.
					refreshMessages();

					let response!: ChatResponse;
					let overflowAttempts = 0;
					const maxOverflowAttempts = this.maxRetriesPerStep;
					while (true) {
						try {
							response = await this._chatWithRetry(
								llm,
								messages,
								tools,
								systemPrompt,
								step,
								turnSignal,
								emitLive,
								onTextDelta,
								onThinkingDelta,
								onToolCallDelta,
								Boolean(onEvent),
							);
							break;
						} catch (err) {
							lastError = err;
							if (isAbortError(err) || turnSignal.aborted) {
								throw err;
							}
							// Same guard as _chatWithRetry: once partial output was
							// published, replaying the request — even after overflow
							// compaction — would duplicate the visible text (T-m7).
							if (isPartialOutputError(err)) {
								throw err;
							}
							const recover = await hooks.handleOverflowError?.({
								turnId,
								stepNumber: step,
								error: err,
								messages,
								llm,
								signal: turnSignal,
							});
							if (recover?.recovered) {
								overflowAttempts += 1;
								if (overflowAttempts >= maxOverflowAttempts) {
									throw err;
								}
								// Overflow recovery compacts memory, replacing the
								// history array; retry against the compacted history.
								refreshMessages();
								await emitLive(
									"step.retrying",
									{
										step,
										reason: "context_overflow",
										attempt: overflowAttempts,
										maxAttempts: maxOverflowAttempts,
										delayMs: 0,
										errorName: (err as Error).name,
										errorMessage: (err as Error).message,
									},
									{ stepId: String(step) },
								);
								continue;
							}
							throw err;
						}
					}

					if (response.usage) {
						tokensUsed += (response.usage.promptTokens ?? 0) + (response.usage.completionTokens ?? 0);
						if (inputTokenCostUsd !== undefined && outputTokenCostUsd !== undefined) {
							costUsd += (response.usage.promptTokens ?? 0) * inputTokenCostUsd + (response.usage.completionTokens ?? 0) * outputTokenCostUsd;
						}
						telemetry?.record({ type: "usage", turnId, step, ...response.usage });
						await emitDurable(
							"usage.updated",
							{
								promptTokens: response.usage.promptTokens,
								completionTokens: response.usage.completionTokens,
							},
							{ stepId: String(step) },
						);
					}

					if (response.content) {
						await emitDurable("assistant.text", { content: response.content }, { stepId: String(step) });
					}

					const usage = response.usage;
					if (!response.toolCalls || response.toolCalls.length === 0) {
						stopReason = normalizeStopReason(response.finishReason);
						if (stopReason === "tool_use") {
							stopReason = "unknown";
						}
						await emitDurable("step.end", { step, stopReason }, { stepId: String(step) });
						messages.push({ role: "assistant", content: response.content ?? "" });
						finalContent = response.content ?? "";
						let after: { stopTurn?: boolean } | undefined;
						try {
							after = await hooks.afterStep?.({
								turnId,
								stepNumber: step,
								messages,
								llm,
								signal: turnSignal,
								stopReason,
								usage,
							});
						} catch (err) {
							this.reportDiagnostic("Turn afterStep hook failed.", err);
						}
						if (after?.stopTurn) {
							break;
						}
						const continuation = await hooks.shouldContinueAfterStop?.({
							turnId,
							stepNumber: step,
							stopReason,
							messages,
							llm,
							signal: turnSignal,
						});
						if (!continuation?.continue) {
							break;
						}
						if (step >= this.maxSteps) {
							stopReason = "max_steps";
							break;
						}
						continue;
					}

					// Execute tools only when the response shape represents a tool
					// step (kimi-code deriveStepStopReason): a normal stop or an
					// absent finish reason alongside tool calls still counts as a
					// tool step — OpenAI-compatible proxies are known to emit
					// "stop" with tool calls — but terminal (filtered, truncated,
					// paused) or unrecognized finish reasons are malformed shapes
					// and must not trigger side-effecting execution. Refuse and
					// end the turn with the mapped stop reason.
					const finishStopReason = normalizeStopReason(response.finishReason);
					if (!finishReasonAllowsToolExecution(response.finishReason)) {
						stopReason = finishStopReason;
						await emitDurable("step.end", { step, stopReason }, { stepId: String(step) });
						messages.push({ role: "assistant", content: response.content ?? "" });
						finalContent = response.content ?? "";
						try {
							await hooks.afterStep?.({
								turnId,
								stepNumber: step,
								messages,
								llm,
								signal: turnSignal,
								stopReason,
								usage,
							});
						} catch (err) {
							this.reportDiagnostic("Turn afterStep hook failed.", err);
						}
						break;
					}

					messages.push({
						role: "assistant",
						content: response.content ?? "",
						toolCalls: response.toolCalls,
					});
					// Text emitted alongside a tool batch is part of the turn's
					// output: a turn ending via tool_stop/error/interrupted must
					// not journal turn.end with content: "" (Task 4.2 review).
					if (response.content) {
						finalContent = finalContent ? `${finalContent}\n${response.content}` : response.content;
					}

					dedup.beginStep();
					let stopAfterBatch = false;
					let stopTurnAfterBatch = false;
					// Set when a tool result (executed, shared, or synthetic) asked
					// to stop the turn; reported as "tool_stop" so tool-initiated
					// stops stay distinguishable from model-initiated end_turn.
					let toolStopAfterBatch = false;
					const scheduler = new ToolScheduler<ToolResult>({ maxConcurrency: this.toolConcurrency });
					let releaseToolBatch!: () => void;
					const toolBatchReady = new Promise<void>((resolve) => {
						releaseToolBatch = resolve;
					});
					const pendingByKey = new Map<string | null, PendingResult>();
					const batchEntries: BatchEntry[] = [];
					settleSpawnedExecutions = async () => {
						// Release the batch gate first so parked executions can
						// start (aborting turns short-circuit them); allSettled
						// then waits for everything that was spawned.
						releaseToolBatch();
						await Promise.allSettled(
							batchEntries
								.filter((entry): entry is Extract<BatchEntry, { kind: "pending" }> => entry.kind === "pending")
								.map((entry) => entry.pending.promise),
						);
					};

					for (const call of response.toolCalls) {
						await emitDurable("tool.call", { call }, { stepId: String(step), toolCallId: call.id });
						telemetry?.record({ type: "tool.call", name: call.name, args: sanitizeArgsForTelemetry(call.arguments) });

						if (stopAfterBatch) {
							const skipped = truncateToolResultForModel(
								{ output: "Skipped: turn stopped by earlier tool result", isError: false, skipped: true },
								resultBudget,
							);
							batchEntries.push({ kind: "settled", call, result: skipped });
							continue;
						}

						if (turnSignal.aborted) {
							const abortedResult = truncateToolResultForModel(
								{ output: abortedToolOutput(call.name, turnSignal), isError: true },
								resultBudget,
							);
							batchEntries.push({ kind: "settled", call, result: abortedResult });
							continue;
						}

						const initialArgs = prepareUpdatedArgs(call, undefined);
						// Same-step duplicate results are shared via pendingByKey
						// below; the dedup tracker's per-step result map is only
						// populated during the drain — after this prep loop — so a
						// cached-result lookup here could never hit (T-m5). Keep
						// only the streak-tracking side effect it used to perform.
						dedup.trackCrossStep(call.name, initialArgs);

						const key = dedup.key(call.name, initialArgs);
						const existingPending = key ? pendingByKey.get(key) : undefined;
						if (existingPending) {
							// Same-step duplicate: shares the primary's result, but
							// journals at its own provider position during the drain.
							batchEntries.push({ kind: "duplicate", call, initialArgs, primary: existingPending });
							continue;
						}

						let prepare: HookResultPayload;
						try {
							prepare = await hooks.prepareToolExecution?.({
								turnId,
								stepNumber: step,
								toolCall: call,
								args: call.arguments ?? {},
								llm,
								signal: turnSignal,
								execution: { toolName: call.name },
							});
						} catch (err) {
							const hookError = truncateToolResultForModel({ output: String(err), isError: true }, resultBudget);
							batchEntries.push({ kind: "settled", call, result: hookError });
							continue;
						}
						if (turnSignal.aborted) {
							const abortedResult = truncateToolResultForModel(
								{ output: abortedToolOutput(call.name, turnSignal), isError: true },
								resultBudget,
							);
							batchEntries.push({ kind: "settled", call, result: abortedResult });
							continue;
						}
						if (prepare?.syntheticResult) {
							const truncatedSynthetic = truncateToolResultForModel(prepare.syntheticResult, resultBudget);
							batchEntries.push({ kind: "settled", call, result: truncatedSynthetic });
							dedup.trackCrossStep(call.name, prepareUpdatedArgs(call, prepare));
							if (truncatedSynthetic.stopTurn) {
								stopAfterBatch = true;
								toolStopAfterBatch = true;
							}
							continue;
						}
						if (prepare?.block) {
							const blocked = truncateToolResultForModel(
								{ output: prepare.reason ?? "Blocked by prepare hook", isError: true },
								resultBudget,
							);
							batchEntries.push({ kind: "settled", call, result: blocked });
							dedup.trackCrossStep(call.name, prepareUpdatedArgs(call, prepare));
							continue;
						}

						const effectiveArgs = prepare?.updatedArgs ?? call.arguments ?? {};

						let execution: ToolExecution;
						try {
							registry.validateArgs(call.name, effectiveArgs);
							execution = registry.resolveExecution(call.name, effectiveArgs, { kaos });
							// Undeclared accesses fail closed: a tool that says nothing
							// about its resource usage must not overlap writers.
							execution.accesses = (await canonicalizeFileAccesses(
								execution.accesses,
								kaos as { resolveForPolicy(filePath: string): Promise<string> },
							)) ?? [...ToolAccesses.all()];
							execution.toolName = call.name;
						} catch (err) {
							const setupError = truncateToolResultForModel({ output: String(err), isError: true }, resultBudget);
							batchEntries.push({ kind: "settled", call, result: setupError });
							continue;
						}

						if (turnSignal.aborted) {
							const abortedResult = truncateToolResultForModel(
								{ output: abortedToolOutput(call.name, turnSignal), isError: true },
								resultBudget,
							);
							batchEntries.push({ kind: "settled", call, result: abortedResult });
							continue;
						}

						let auth: HookResultPayload;
						try {
							auth = await hooks.authorizeToolExecution?.({
								turnId,
								stepNumber: step,
								toolCall: call,
								args: effectiveArgs,
								llm,
								signal: turnSignal,
								execution,
								executionMetadata: prepare?.executionMetadata,
							});
						} catch (err) {
							const hookError = truncateToolResultForModel({ output: String(err), isError: true }, resultBudget);
							batchEntries.push({ kind: "settled", call, result: hookError });
							continue;
						}
						if (turnSignal.aborted) {
							const abortedResult = truncateToolResultForModel(
								{ output: abortedToolOutput(call.name, turnSignal), isError: true },
								resultBudget,
							);
							batchEntries.push({ kind: "settled", call, result: abortedResult });
							continue;
						}
						if (auth?.block) {
							const denied = truncateToolResultForModel(
								{ output: auth.reason ?? `User denied ${call.name}`, isError: true },
								resultBudget,
							);
							batchEntries.push({ kind: "settled", call, result: denied });
							session?.learningBus?.enqueue(
								createUserFeedbackEvent("deny", { toolName: call.name, reason: auth.reason }, { turnId, step }),
							);
							dedup.trackCrossStep(call.name, effectiveArgs);
							continue;
						}

						const executionMetadata = auth?.executionMetadata ?? prepare?.executionMetadata;
						const idempotencyKey = isMutatingExecution(execution)
							? toolIdempotencyKey(recordStore?.sessionId ?? session?.sessionId ?? sessionId, call.name, effectiveArgs)
							: undefined;
						if (idempotencyKey && session?.idempotencyStore) {
							const reservation = await session.idempotencyStore.reserve(idempotencyKey);
							if (reservation.state === "completed" && reservation.result) {
								batchEntries.push({
									kind: "settled",
									call,
									result: {
										...reservation.result,
										output: `[Idempotent replay: this identical mutating call already completed; returning the recorded result without re-executing.]\n${reservation.result.output}`,
										idempotentReplay: true,
									},
								});
								continue;
							}
							if (reservation.state === "pending") {
								// Only a crash between dispatch and outcome recording leaves a
								// pending entry: the operation may already have taken effect.
								batchEntries.push({
									kind: "settled",
									call,
									result: {
										output: "A matching mutating operation may already have been sent but its outcome was never recorded (the process was interrupted mid-flight). Do not repeat it blindly; verify external state first, then continue or request review.",
										isError: true,
									},
								});
								continue;
							}
						}

						const pending: PendingResult = {
							call,
							args: effectiveArgs,
							prepare,
							execution,
							executionMetadata,
							...(idempotencyKey ? { idempotencyKey } : {}),
							...(auth?.approvalFeedback ? { approvalFeedback: auth.approvalFeedback } : {}),
							key,
							promise: scheduler.add({
								accesses: execution.accesses,
								start: async () => {
									await toolBatchReady;
									if (turnSignal.aborted) {
										return {
											result: Promise.resolve<ToolResult>({
												output: abortedToolOutput(call.name, turnSignal),
												isError: true,
											}),
										};
									}
									const onProgress = (progress: unknown) => {
										try {
											onToolProgress?.({ call, progress });
										} catch (err) {
											this.reportDiagnostic("Turn tool progress observer failed.", err);
										}
										emitLive("tool.progress", { call, progress }, { stepId: String(step), toolCallId: call.id }).catch(
											(err) => {
												this.reportDiagnostic("Turn tool progress event emission failed.", err);
											},
										);
									};
									return {
										result: (async (): Promise<ToolResult> => {
											try {
											return await executeToolWithRetry(
													{ execute: execution.execute },
													effectiveArgs,
													{
														kaos,
														tracker,
														permission,
														mcp,
														session,
														subagentHost: session?.subagentHost,
														executionMetadata,
														signal: turnSignal,
														onProgress,
														parentActivityId: turnId,
														parentToolCallId: call.id,
													},
													toolGraceMs,
													this.maxToolExecutionMs,
													isMutatingExecution(execution) ? 0 : this.maxToolRetries,
													async (retry) => {
														await emitLive(
															"tool.retrying",
															{ toolName: call.name, ...retry },
															{ stepId: String(step), toolCallId: call.id },
														);
													},
												);
											} catch (err) {
												if (isAbortError(err) || turnSignal.aborted) {
													return { output: abortedToolOutput(call.name, turnSignal), isError: true };
												}
												return { output: String(err), isError: true };
											}
										})(),
									};
								},
							}),
						};
						batchEntries.push({ kind: "pending", pending });
						pendingByKey.set(key, pending);

						if (execution.stopBatchAfterThis) {
							stopAfterBatch = true;
						}
					}

					releaseToolBatch();
					// Drain every outcome in provider order: results that settled
					// during preparation are journaled at their provider position,
					// interleaved with the executed calls they preceded or followed.
					for (const entry of batchEntries) {
						if (entry.kind === "settled") {
							pushToolResult(messages, entry.call, entry.result);
							await emitDurable(
								"tool.result",
								{ call: entry.call, result: entry.result },
								{ stepId: String(step), toolCallId: entry.call.id },
							);
							telemetry?.record({
								type: "tool.result",
								name: entry.call.name,
								isError: entry.result.isError ?? false,
								...(entry.result.skipped === true ? { skipped: true } : {}),
							});
							continue;
						}
						if (entry.kind === "duplicate") {
							// The primary always precedes its duplicates in provider
							// order, so it has already drained and finalized.
							const primaryResult = entry.primary.finalResult ?? normalizeToolResult(await entry.primary.promise);
							const dupResult = truncateToolResultForModel(primaryResult, resultBudget);
							pushToolResult(messages, entry.call, dupResult);
							await emitDurable(
								"tool.result",
								{ call: entry.call, result: dupResult },
								{ stepId: String(step), toolCallId: entry.call.id },
							);
							telemetry?.record({
								type: "tool.result",
								name: entry.call.name,
								isError: dupResult.isError ?? false,
							});
							dedup.trackCrossStep(entry.call.name, entry.initialArgs);
							if (dupResult.stopTurn) {
								toolStopAfterBatch = true;
							}
							continue;
						}
						const pending = entry.pending;
						const { call, args: effectiveArgs, prepare, execution, executionMetadata } = pending;
						const result = normalizeToolResult(await pending.promise);

						let finalized: ToolResult | undefined;
						try {
							finalized = await hooks.finalizeToolResult?.({
								turnId,
								stepNumber: step,
								toolCall: call,
								args: effectiveArgs,
								result,
								llm,
								signal: turnSignal,
								execution,
								executionMetadata,
							});
						} catch (err) {
							if (isAbortError(err) || turnSignal.aborted) {
								finalized = { output: abortedToolOutput(call.name, turnSignal), isError: true };
							} else {
								finalized = { output: String(err), isError: true };
							}
						}
						const finalResult = truncateToolResultForModel(normalizeToolResult(finalized ?? result), resultBudget);
						pending.finalResult = finalResult;
						if (pending.idempotencyKey) {
							if (!finalResult.isError) {
								// A successful mutating call is durably completed: an identical
								// later call replays this result instead of duplicating the effect.
								await session?.idempotencyStore?.complete(pending.idempotencyKey, finalResult);
							} else {
								const outputText = typeof finalResult.output === "string" ? finalResult.output : "";
								const outcomeUncertain =
									turnSignal.aborted ||
									outputText.startsWith(`Tool "${call.name}" was aborted`) ||
									outputText.startsWith("The user manually interrupted");
								if (!outcomeUncertain) {
									// The tool reported failure, so nothing was durably applied;
									// free the key so the model can correct and retry. An abort
									// or timeout leaves the outcome uncertain, so the reservation
									// stays pending and a later identical call must verify first.
									await session?.idempotencyStore?.release?.(pending.idempotencyKey);
								}
							}
						}

						pushToolResult(messages, call, finalResult);
						if (pending.approvalFeedback) {
							messages.push({
								role: "system",
								content: `User approval feedback for ${call.name}: ${pending.approvalFeedback}`,
								origin: "approval_feedback",
							});
						}
						await emitDurable(
							"tool.result",
							{ call, result: finalResult },
							{ stepId: String(step), toolCallId: call.id },
						);
						telemetry?.record({ type: "tool.result", name: call.name, isError: finalResult.isError ?? false });
						const failureDecision = failureGuardrail.observe({
							toolName: call.name,
							args: effectiveArgs,
							result: finalResult,
						});
						if (failureDecision.reminder) {
							messages.push({ role: "system", content: failureDecision.reminder, origin: "tool_failure_guardrail" });
							this.reportDiagnostic(failureDecision.reminder);
						}
						if (failureDecision.forceStop) {
							// Guardrail force stops are tool-initiated, not a model
							// end_turn — same label as a result-level stopTurn.
							stopTurnAfterBatch = true;
							toolStopAfterBatch = true;
							checkpointReason = "stalled";
						}
						const progressDecision = progressGuardrail.observe({ toolName: call.name, args: effectiveArgs, result: finalResult });
						if (progressDecision.reminder) {
							messages.push({ role: "system", content: progressDecision.reminder, origin: "no_progress_guardrail" });
							this.reportDiagnostic(progressDecision.reminder);
						}
						if (progressDecision.forceStop) {
							stopTurnAfterBatch = true;
							toolStopAfterBatch = true;
							checkpointReason = "stalled";
						}

						const finalArgs = prepare?.updatedArgs ?? call.arguments ?? {};
						dedup.trackCrossStep(call.name, finalArgs);

						if (finalResult.stopTurn) {
							toolStopAfterBatch = true;
						}
					}

					if (stopTurnAfterBatch || toolStopAfterBatch) {
						stopAfterBatch = true;
					}

					throwIfAborted(turnSignal);

					const crossStepAction = dedup.endStep(messages, { turnId, step });
					if (crossStepAction?.forceStop) {
						// A dedup-streak force stop is likewise not model-initiated.
						stopAfterBatch = true;
						toolStopAfterBatch = true;
						checkpointReason = "stalled";
					}
					if (crossStepAction?.remindersInjected) {
						telemetry?.record({ type: "tool_call_dedup_detected", turnId, step });
					}

					stopReason = "tool_use";
					await emitDurable("step.end", { step, stopReason }, { stepId: String(step) });
					let after: { stopTurn?: boolean } | undefined;
					try {
						after = await hooks.afterStep?.({
							turnId,
							stepNumber: step,
							messages,
							llm,
							signal: turnSignal,
							stopReason,
							usage,
						});
					} catch (err) {
						this.reportDiagnostic("Turn afterStep hook failed.", err);
					}
					if (after?.stopTurn || stopAfterBatch) {
						// A tool result that asked to stop the turn is not a
						// model-initiated end; keep the distinction (T-m9).
						stopReason = checkpointReason === "stalled" ? "stalled" : toolStopAfterBatch ? "tool_stop" : "end_turn";
						break;
					}
					if (step >= this.maxSteps) {
						stopReason = "slice_exhausted";
						checkpointReason = "slice_exhausted";
						break;
					}
				} catch (err) {
					lastError = err;
					// Settle spawned tool executions before this error leaves the
					// step; otherwise they would stay parked on the batch gate
					// forever (detached promises).
					try {
						await settleSpawnedExecutions?.();
					} catch (settleError) {
						this.reportDiagnostic("Turn tool batch settlement failed.", settleError);
					}
					if (isAbortError(err) || turnSignal.aborted) {
						stopReason = "interrupted";
						await emitDurable("turn.interrupted", { stopReason: "interrupted" });
						telemetry?.record({ type: "turn_interrupted", turnId });
					} else {
						stopReason = "error";
					}
					throw err;
				}
			}
		} catch (err) {
			lastError = err;
			this.reportDiagnostic("Turn failed.", err);
			if (stopReason !== "interrupted") {
				stopReason = "error";
			}
		} finally {
			if (signal) {
				signal.removeEventListener("abort", onExternalAbort);
			}
			turnAbort.abort();
			const result = { content: finalContent, stopReason, tokensUsed, costUsd };
			telemetry?.record({ type: "turn.end", result, turnId });
			if (!recordStore?.fault && turnStarted) {
				if (checkpointReason) {
					await emitDurable("turn.checkpointed", {
						reason: checkpointReason,
						elapsedMs: Date.now() - startedAt,
						tokensUsed,
						costUsd,
					});
				}
				await emitDurable("turn.end", { result });
			}
		}

		if (lastError && stopReason === "interrupted") {
			throw lastError;
		}

		if (lastError && stopReason === "error") {
			throw lastError;
		}

		return { content: finalContent, stopReason, tokensUsed, costUsd };
	}

	private async _chatWithRetry(
		llm: AgentLlm,
		messages: TurnMessage[],
		tools: ChatOptions["tools"],
		systemPrompt: string | undefined,
		step: number,
		signal: AbortSignal,
		emitLive: EmitLive,
		onTextDelta?: (delta: string) => void,
		onThinkingDelta?: (delta: string) => void,
		onToolCallDelta?: (delta: { id: string; name: string; argumentsPartial: string }) => void,
		publishLiveEvents = false,
	): Promise<ChatResponse> {
		const buildContext = (msgs: TurnMessage[]): ChatMessage[] => {
			const strict = project(msgs as unknown as Parameters<typeof project>[0], {
				synthesizeMissing: true,
				dropOrphanResults: true,
				dedupeDuplicateToolCalls: true,
				dropLeadingNonUser: true,
				mergeConsecutiveAssistants: true,
			});
			const chatMessages = strict as unknown as ChatMessage[];
			return systemPrompt ? [{ role: "system", content: systemPrompt }, ...chatMessages] : chatMessages;
		};
		const contextMessages = buildContext(messages);

		const shouldStreamText = Boolean(onTextDelta || publishLiveEvents);
		const shouldStreamThinking = Boolean(onThinkingDelta || publishLiveEvents);
		const shouldStreamToolCall = Boolean(onToolCallDelta || publishLiveEvents);
		const chatOptions: ChatOptions = { messages: contextMessages, tools, signal };
		if (shouldStreamText) {
			chatOptions.onTextDelta = (delta: string) => {
				try {
					onTextDelta?.(delta);
				} catch (err) {
					this.reportDiagnostic("Turn text delta observer failed.", err);
				}
				emitLive("text.delta", { delta }, { stepId: String(step) }).catch((err) => {
					this.reportDiagnostic("Turn text delta event emission failed.", err);
				});
			};
		}
		if (shouldStreamThinking) {
			chatOptions.onThinkingDelta = (delta: string) => {
				try {
					onThinkingDelta?.(delta);
				} catch (err) {
					this.reportDiagnostic("Turn thinking delta observer failed.", err);
				}
				emitLive("thinking.delta", { delta }, { stepId: String(step) }).catch((err) => {
					this.reportDiagnostic("Turn thinking delta event emission failed.", err);
				});
			};
		}
		if (shouldStreamToolCall) {
			chatOptions.onToolCallDelta = (delta: { id: string; name: string; argumentsPartial: string }) => {
				try {
					onToolCallDelta?.(delta);
				} catch (err) {
					this.reportDiagnostic("Turn tool-call delta observer failed.", err);
				}
				emitLive("tool.call.delta", delta, {
					stepId: String(step),
					toolCallId: delta.id,
				}).catch((err) => {
					this.reportDiagnostic("Turn tool-call delta event emission failed.", err);
				});
			};
		}

		const delays = retryBackoffDelays(this.maxRetriesPerStep);
		for (let attempt = 1; ; attempt += 1) {
			throwIfAborted(signal);
			let publishedAttemptDelta = false;
			try {
				const attemptOptions: ChatOptions = {
					...chatOptions,
					onTextDelta: chatOptions.onTextDelta
						? (delta) => {
								publishedAttemptDelta = true;
								chatOptions.onTextDelta!(delta);
							}
						: undefined,
					onThinkingDelta: chatOptions.onThinkingDelta
						? (delta) => {
								publishedAttemptDelta = true;
								chatOptions.onThinkingDelta!(delta);
							}
						: undefined,
					onToolCallDelta: chatOptions.onToolCallDelta
						? (delta) => {
								publishedAttemptDelta = true;
								chatOptions.onToolCallDelta!({ ...delta });
							}
						: undefined,
				};
				const response = normalizeProviderResponse(await llm.chat(attemptOptions), tools);
				return response;
			} catch (error) {
				if (isAbortError(error) || signal?.aborted) {
					throw error;
				}
				// Once partial output is observable, replaying the request could
				// duplicate text or execute a second copy of a streamed tool call.
				if (publishedAttemptDelta) {
					markPartialOutputError(error);
					throw error;
				}
				if (attempt >= this.maxRetriesPerStep || !llm.isRetryableError?.(error)) {
					throw error;
				}
				try {
					await llm.recoverAfterError?.(error, { attempt, signal });
				} catch (recoveryError) {
					this.reportDiagnostic("Provider recovery hook failed; continuing with bounded retry.", recoveryError);
				}
				throwIfAborted(signal);
				const delayMs = retryDelayFromError(error) ?? delays[attempt - 1] ?? 1000;
				await emitLive(
					"step.retrying",
					{
						step,
						attempt,
						maxAttempts: this.maxRetriesPerStep,
						delayMs,
						errorName: (error as Error).name ?? "Error",
						errorMessage: (error as Error).message ?? String(error),
					},
					{ stepId: String(step) },
				);
				await sleepForRetry(delayMs, signal);
			}
		}
	}

	private reportDiagnostic(message: string, error?: unknown): void {
		try {
			void Promise.resolve(this.onDiagnostic?.(message, error)).catch(() => {});
		} catch {
			/* diagnostics are observational */
		}
	}
}

const STREAK_REMINDER_THRESHOLDS = [3, 5, 8];

// Volatile call metadata that must not split a repeated-call streak.
const VOLATILE_TOOL_ARG_KEYS = new Set(["timeout", "timeoutMs", "requestId"]);

function normalizeToolCallArgs(value: unknown): unknown {
	if (typeof value === "string") {
		return value.trim().replace(/\s+/g, " ");
	}
	if (Array.isArray(value)) {
		return value.map(normalizeToolCallArgs);
	}
	if (value !== null && typeof value === "object") {
		const normalized: Record<string, unknown> = {};
		for (const [key, child] of Object.entries(value)) {
			if (VOLATILE_TOOL_ARG_KEYS.has(key)) continue;
			normalized[key] = normalizeToolCallArgs(child);
		}
		return normalized;
	}
	return value;
}

class ToolCallDedupTracker {
	private readonly forceStopThreshold: number;
	private crossStepStreak = new Map<string, number>();
	private stepKeys = new Set<string>();

	constructor(forceStopThreshold: number) {
		this.forceStopThreshold = forceStopThreshold;
	}

	beginStep(): void {
		this.stepKeys.clear();
	}

	key(name: string, args: unknown): string | null {
		const serialized = safeStringify(normalizeToolCallArgs(args ?? {}));
		if (serialized === null) {
			return null;
		}
		return `${name}:${serialized}`;
	}

	trackCrossStep(name: string, args: unknown): void {
		const key = this.key(name, args);
		if (key === null) {
			return;
		}
		this.stepKeys.add(key);
	}

	endStep(
		messages: TurnMessage[] | undefined,
		_meta: Record<string, unknown> = {},
	): { forceStop: boolean; remindersInjected: boolean } {
		let forceStop = false;
		let remindersInjected = false;
		const reminders: string[] = [];

		for (const key of this.stepKeys) {
			const count = (this.crossStepStreak.get(key) ?? 0) + 1;
			this.crossStepStreak.set(key, count);

			if (STREAK_REMINDER_THRESHOLDS.includes(count)) {
				reminders.push(
					`Notice: the same tool call has been repeated ${count} times in a row. Please reconsider your approach.`,
				);
			}
			if (count >= this.forceStopThreshold) {
				forceStop = true;
			}
		}

		// Reset streaks for keys that did not appear this step.
		for (const key of this.crossStepStreak.keys()) {
			if (!this.stepKeys.has(key)) {
				this.crossStepStreak.delete(key);
			}
		}

		if (reminders.length > 0 && messages) {
			remindersInjected = true;
			messages.push({
				role: "system",
				content: reminders.join("\n"),
				origin: "tool_call_dedup_reminder",
			});
		}

		return { forceStop, remindersInjected };
	}
}

class ToolProgressGuardrail {
	private readonly maxNoProgressSteps: number;
	private previousSignature: string | undefined;
	private consecutiveNoProgress = 0;
	private previousOutputClass: string | undefined;
	private outputClassStreak = 0;

	constructor(maxNoProgressSteps: number) {
		this.maxNoProgressSteps = maxNoProgressSteps;
	}

	observe({ toolName, args, result }: { toolName: string; args: unknown; result: ToolResult }): { forceStop: boolean; reminder?: string } {
		if (result.isError) {
			this.previousSignature = undefined;
			this.consecutiveNoProgress = 0;
			this.previousOutputClass = undefined;
			this.outputClassStreak = 0;
			return { forceStop: false };
		}
		const output = safeStringify(result.output);
		if (output === null) return { forceStop: false };
		const signature = crypto.createHash("sha256").update(`${toolName}:${safeStringify(args) ?? ""}:${output}`).digest("hex");
		this.consecutiveNoProgress = signature === this.previousSignature ? this.consecutiveNoProgress + 1 : 1;
		this.previousSignature = signature;
		// The output class ignores the arguments and volatile tokens, so a
		// successful call loop whose parameters keep changing (fresh session
		// names, selectors, flags) still counts as no progress while it keeps
		// observing the same page or state.
		const outputClass = `${toolName}:${normalizeObservationText(toolOutputText(result.output))}`;
		this.outputClassStreak = outputClass === this.previousOutputClass ? this.outputClassStreak + 1 : 1;
		this.previousOutputClass = outputClass;
		const forceStop =
			this.consecutiveNoProgress >= this.maxNoProgressSteps || this.outputClassStreak >= this.maxNoProgressSteps;
		const noProgressCount = Math.max(this.consecutiveNoProgress, this.outputClassStreak);
		return {
			forceStop,
			reminder: forceStop
				? `No externally observable progress after ${noProgressCount} identical observations from ${toolName}. Checkpointing this task for recovery or human review.`
				: this.consecutiveNoProgress === 3
					? "The same tool call produced the same observation three times. Verify external state or change strategy; repeated observations are not progress."
					: this.outputClassStreak === 3
						? `Tool ${toolName} returned the same observation three times in a row, even though the call arguments varied. Reissuing it with tweaked parameters is treated as the same no-progress step. Verify the current state first, or change strategy — use a different tool or extract what you need in-page.`
						: undefined,
		};
	}
}

function toolOutputText(output: ToolResult["output"]): string {
	if (typeof output === "string") return output;
	if (Array.isArray(output)) {
		return output
			.filter((part) => part && typeof part === "object" && part["type"] === "text")
			.map((part) => String(part["text"] ?? ""))
			.join("\n");
	}
	return "";
}

function isMutatingExecution(execution: ToolExecution): boolean {
	return execution.accesses.some((access) => {
		// `all` is a conservative scheduler fallback, not evidence that this call
		// mutates anything. Caching it would turn harmless repeated observations
		// (for example a screenshot command) into false idempotency hits.
		if (access.kind === "all") return false;
		if (access.kind === "file") return access.operation === "write" || access.operation === "readwrite";
		if (access.kind === "network") return access.operation === "send";
		if (access.kind === "process") return access.operation === "execute" || access.operation === "mutate" || access.operation === "create" || access.operation === "delete";
		if (access.kind === "session" || access.kind === "durable_state" || access.kind === "extension" || access.kind === "delegation" || access.kind === "credential" || access.kind === "interaction") {
			return access.operation !== "read" && access.operation !== "use";
		}
		return false;
	});
}

function toolIdempotencyKey(sessionId: string, toolName: string, args: unknown): string {
	return crypto.createHash("sha256").update(`${sessionId}:${toolName}:${safeStringify(args) ?? ""}`).digest("hex");
}

function generateTurnId(): string {
	if (crypto.randomUUID) {
		return crypto.randomUUID();
	}
	return crypto.randomBytes(16).toString("hex");
}

function normalizeStopReason(finishReason: string | undefined): string {
	const reason = String(finishReason ?? "").toLowerCase();
	switch (reason) {
		case "stop":
		case "stop_sequence":
		case "end_turn":
			return "end_turn";
		case "tool_calls":
		case "function_call":
		case "tool_use":
			return "tool_use";
		case "length":
		case "max_tokens":
			return "max_tokens";
		case "content_filter":
		case "filtered":
			return "filtered";
		case "pause":
		case "paused":
			return "paused";
		default:
			return "unknown";
	}
}

/**
 * Whether a response carrying tool calls may execute them (kimi-code
 * deriveStepStopReason semantics): normal completion signals and a missing
 * finish reason count as a tool step, while terminal (filter/truncation/
 * pause) and unrecognized reasons refuse side-effecting execution.
 */
function finishReasonAllowsToolExecution(finishReason: string | undefined): boolean {
	const reason = String(finishReason ?? "")
		.trim()
		.toLowerCase();
	switch (reason) {
		case "":
		case "stop":
		case "stop_sequence":
		case "end_turn":
		case "tool_calls":
		case "function_call":
		case "tool_use":
			return true;
		default:
			return false;
	}
}

function retryBackoffDelays(maxAttempts: number): number[] {
	const attempts = clampPositiveInteger(maxAttempts, 3);
	const delays: number[] = [];
	let delay = 300;
	for (let i = 1; i < attempts; i += 1) {
		const jittered = Math.floor(delay * (0.5 + Math.random() * 0.5));
		delays.push(Math.min(jittered, 5000));
		delay *= 2;
	}
	return delays;
}

function retryDelayFromError(error: unknown): number | undefined {
	const seen = new Set<unknown>();
	let current: unknown = error;
	for (let depth = 0; current && depth < 8 && !seen.has(current); depth += 1) {
		seen.add(current);
		if (typeof current !== "object") return undefined;
		const candidate = current as { retryAfterMs?: unknown; cause?: unknown };
		const delay = Number(candidate.retryAfterMs);
		if (Number.isFinite(delay) && delay >= 0) return Math.min(delay, 30_000);
		current = candidate.cause;
	}
	return undefined;
}

function normalizeProviderResponse(response: ChatResponse, tools: ChatOptions["tools"]): ChatResponse {
	if (!response || typeof response !== "object") throw new TypeError("Provider returned a malformed chat response");
	if (!Array.isArray(response.toolCalls)) throw new TypeError("Provider response toolCalls must be an array");
	const knownNames = (tools ?? []).map((tool) => tool.function.name);
	const seenIds = new Set<string>();
	const toolCalls = response.toolCalls.map((call, index) => {
		if (!call || typeof call !== "object") throw new TypeError(`Provider tool call ${index} is malformed`);
		if (typeof call.id !== "string" || !call.id.trim())
			throw new TypeError(`Provider tool call ${index} is missing an id`);
		if (seenIds.has(call.id)) throw new TypeError(`Provider returned duplicate tool call id ${call.id}`);
		seenIds.add(call.id);
		if (typeof call.name !== "string" || !call.name.trim())
			throw new TypeError(`Provider tool call ${call.id} is missing a name`);
		if (!call.arguments || typeof call.arguments !== "object" || Array.isArray(call.arguments)) {
			throw new TypeError(`Provider tool call ${call.id} arguments must be an object`);
		}
		const repairedName = repairToolName(call.name, knownNames);
		return repairedName === call.name ? call : { ...call, name: repairedName };
	});
	return { ...response, toolCalls };
}

function repairToolName(emitted: string, knownNames: readonly string[]): string {
	if (knownNames.includes(emitted)) return emitted;
	const normalize = (value: string) =>
		value
			.replace(/([a-z0-9])([A-Z])/g, "$1_$2")
			.toLowerCase()
			.replace(/[\s-]+/g, "_")
			.replace(/(?:_?tool){1,2}$/g, "")
			.replace(/^_+|_+$/g, "");
	const target = normalize(emitted);
	const matches = knownNames.filter((name) => normalize(name) === target);
	return matches.length === 1 ? matches[0]! : emitted;
}

function sleepForRetry(ms: number, signal?: AbortSignal): Promise<void> {
	return new Promise((resolve, reject) => {
		if (signal?.aborted) {
			reject(signal.reason ?? new Error("Aborted"));
			return;
		}
		const timer = setTimeout(() => {
			cleanup();
			resolve();
		}, ms);
		const onAbort = () => {
			cleanup();
			reject(signal!.reason ?? new Error("Aborted"));
		};
		const cleanup = () => {
			clearTimeout(timer);
			signal?.removeEventListener("abort", onAbort);
		};
		signal?.addEventListener("abort", onAbort, { once: true });
	});
}

const MAX_SAFE_TIMEOUT_MS = 2 ** 31 - 1;

/**
 * Retry only observations that are both safe to repeat and plausibly
 * transient. A caller passes zero retries for any operation with a declared
 * external side effect; those operations instead use the idempotency journal.
 */
async function executeToolWithRetry(
	tool: { execute: ToolExecution["execute"] },
	args: Record<string, unknown>,
	ctx: ToolExecutionContext,
	graceMs: number,
	maxExecutionMs: number | undefined,
	maxRetries: number,
	onRetrying?: (retry: { attempt: number; maxAttempts: number; delayMs: number; reason: string }) => Promise<void>,
): Promise<ToolResult> {
	let lastFailure: unknown;
	for (let attempt = 0; attempt <= maxRetries; attempt += 1) {
		try {
			const result = await executeToolWithGrace(tool, args, ctx, graceMs, maxExecutionMs);
			if (!result.isError || !isRetryableToolFailure(result.output) || attempt === maxRetries) {
				return attempt === 0 ? result : { ...result, retryAttempts: attempt };
			}
			lastFailure = result.output;
		} catch (error) {
			if (isAbortError(error) || ctx.signal?.aborted || !isRetryableToolFailure(error) || attempt === maxRetries) {
				throw error;
			}
			lastFailure = error;
		}
		const delayMs = retryDelayFromError(lastFailure) ?? retryBackoffDelays(maxRetries + 1)[attempt] ?? 1_000;
		await onRetrying?.({ attempt: attempt + 1, maxAttempts: maxRetries + 1, delayMs, reason: String(lastFailure) });
		await sleepForRetry(delayMs, ctx.signal);
	}
	throw lastFailure instanceof Error ? lastFailure : new Error(String(lastFailure ?? "Tool retry failed"));
}

function isRetryableToolFailure(failure: unknown): boolean {
	if (isAbortError(failure)) return false;
	const text = String(failure ?? "").toLowerCase();
	return /\b(?:429|500|502|503|504|econnreset|econnrefused|eai_again|enotfound|etimedout|timeout|timed out|network|socket|connection|temporar(?:y|ily)|rate limit|unavailable|service busy)\b/.test(
		text,
	);
}

async function executeToolWithGrace(
	tool: { execute: ToolExecution["execute"] },
	args: Record<string, unknown>,
	ctx: ToolExecutionContext,
	graceMs: number,
	maxExecutionMs?: number,
): Promise<ToolResult> {
	const { signal } = ctx;
	const toolAbort = new AbortController();
	const onParentAbort = () => toolAbort.abort(signal?.reason);
	if (signal?.aborted) toolAbort.abort(signal.reason);
	else signal?.addEventListener("abort", onParentAbort, { once: true });
	let timeout: NodeJS.Timeout | undefined;
	if (maxExecutionMs !== undefined) {
		timeout = setTimeout(() => toolAbort.abort(new Error(`Tool execution exceeded ${maxExecutionMs}ms`)), maxExecutionMs);
	}
	const toolContext = { ...ctx, signal: toolAbort.signal };
	const cleanupLimit = () => {
		if (timeout) clearTimeout(timeout);
		signal?.removeEventListener("abort", onParentAbort);
	};
	const effectiveGraceMs = clampGraceMs(graceMs);
	if (toolAbort.signal.aborted) {
		cleanupLimit();
		return { output: "Tool execution aborted before starting.", isError: true };
	}
	return new Promise((resolve, reject) => {
		let settled = false;
		let abortListener: (() => void) | undefined;
		let graceTimer: NodeJS.Timeout | undefined;
		const cleanup = () => {
			if (abortListener) toolAbort.signal.removeEventListener("abort", abortListener);
			if (graceTimer) clearTimeout(graceTimer);
			cleanupLimit();
		};
		const finish = (value?: ToolResult, error?: unknown) => {
			if (settled) return;
			settled = true;
			cleanup();
			if (error) reject(error);
			else resolve(value!);
		};
		Promise.resolve(tool.execute(args, toolContext))
			.then((value) => finish(value))
			.catch((err) => finish(undefined, err));
		const onAbort = async () => {
			// Ask the process tracker to kill any foreground child processes
			// spawned by this tool before waiting out the grace period.
			await toolContext.tracker?.stopForeground?.().catch(() => {});
			graceTimer = setTimeout(() => {
				finish(undefined, new Error(`Tool execution aborted and did not stop within ${effectiveGraceMs}ms`));
			}, effectiveGraceMs);
		};
		if (toolAbort.signal.aborted) {
			onAbort();
		} else {
			abortListener = onAbort;
			toolAbort.signal.addEventListener("abort", abortListener, { once: true });
		}
	});
}

function normalizeToolResult(result: unknown): ToolResult {
	if (result && typeof result === "object") {
		return result as ToolResult;
	}
	return { output: result == null ? "" : String(result), isError: false };
}

function pushToolResult(messages: TurnMessage[], call: ToolCall, result: ToolResult): void {
	messages.push({
		role: "tool",
		toolCallId: call.id,
		content: result.output as string,
		isError: result.isError ?? false,
	});
}

function prepareUpdatedArgs(call: ToolCall, prepare: HookResultPayload): Record<string, unknown> {
	return prepare?.updatedArgs ?? call.arguments ?? {};
}

function truncateToolResultForModel(result: ToolResult, maxLength: number = DEFAULT_TOOL_RESULT_BUDGET): ToolResult {
	if (!result || result.output == null) {
		return result;
	}
	if (typeof result.output === "string") {
		if (result.output.length <= maxLength) {
			return result;
		}
		return {
			...result,
			output: result.output.slice(0, maxLength) + "\n... (truncated)",
		};
	}
	if (Array.isArray(result.output)) {
		let remaining = maxLength;
		const truncated: Array<Record<string, unknown>> = [];
		let didTruncate = false;
		for (const part of result.output) {
			if (!part || typeof part !== "object") {
				continue;
			}
			if (part["type"] === "text") {
				const text = String(part["text"] ?? "");
				if (text.length <= remaining) {
					truncated.push(part);
					remaining -= text.length;
				} else if (remaining > 0) {
					truncated.push({ ...part, text: text.slice(0, remaining) + "\n... (truncated)" });
					remaining = 0;
					didTruncate = true;
				} else {
					didTruncate = true;
				}
			} else if (part["type"] === "image_url" || part["type"] === "video_url") {
				const url = ((part["imageUrl"] as { url?: string } | undefined)?.url ??
					(part["videoUrl"] as { url?: string } | undefined)?.url ??
					"") as string;
				if (url.length <= remaining) {
					truncated.push(part);
					remaining -= url.length;
				} else {
					didTruncate = true;
				}
			} else {
				const text = JSON.stringify(part);
				if (text.length <= remaining) {
					truncated.push(part);
					remaining -= text.length;
				} else {
					didTruncate = true;
				}
			}
		}
		if (!didTruncate) {
			return result;
		}
		return { ...result, output: truncated, truncated: true };
	}
	return result;
}

function isAbortError(err: unknown): boolean {
	if (!err) return false;
	const error = err as { name?: string; code?: string; message?: string };
	if (error.name === "AbortError") return true;
	if (error.code === "ABORT_ERR") return true;
	const message = String(error.message ?? err).toLowerCase();
	return message.includes("aborted") || message.includes("abort");
}

function abortedToolOutput(toolName: string, signal?: AbortSignal): string {
	const reason = signal?.reason as { name?: string; userCancelled?: boolean; reason?: string } | undefined;
	if (
		reason &&
		(reason.name === "UserCancelled" || reason.userCancelled === true || reason.reason === "user_cancelled")
	) {
		return `The user manually interrupted "${toolName}" (and anything else running at the same time). This was a deliberate user action, not a system error, timeout, or capacity limit. Do not retry automatically or guess at the cause — wait for the user's next instruction.`;
	}
	return `Tool "${toolName}" was aborted`;
}

function throwIfAborted(signal?: AbortSignal): void {
	if (signal?.aborted) {
		throw signal.reason ?? new Error("Aborted");
	}
}

function clampPositiveInteger(value: unknown, fallback: number): number {
	const n = Number(value);
	if (!Number.isFinite(n) || !Number.isInteger(n) || n < 1) {
		return Math.max(1, Math.floor(Number(fallback)) || 1);
	}
	return n;
}

function clampNonNegativeInteger(value: unknown, fallback: number): number {
	const n = Number(value);
	if (!Number.isFinite(n) || !Number.isInteger(n) || n < 0) {
		return Math.max(0, Math.floor(Number(fallback)) || 0);
	}
	return n;
}

function clampGraceMs(value: unknown): number {
	const n = Number(value);
	if (!Number.isFinite(n)) {
		return 0;
	}
	return Math.max(0, Math.min(n, MAX_SAFE_TIMEOUT_MS));
}
