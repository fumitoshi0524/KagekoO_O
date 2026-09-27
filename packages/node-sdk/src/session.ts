import type { PromptInput } from "./types/prompts.js";
import type { GoalBudgetData } from "@kageko/protocol";
import type { SessionRestoreResult, SessionTimelineEntry } from "./types/sessions.js";
import type { SessionSnapshot } from "./types/sessions.js";
import type { Transport, TransportRequestOptions } from "./transport/transport.js";
import type { Event } from "./types/events.js";
import type { ActivityOutputChunk } from "./types/tasks.js";
import { randomUUID } from "node:crypto";
const SESSION_CLIENT_TOKEN: unique symbol = Symbol("SessionClient.internal");
export class SessionClient {
	constructor(
		private readonly transport: Transport,
		readonly id: string,
		token: typeof SESSION_CLIENT_TOKEN,
	) {
		if (token !== SESSION_CLIENT_TOKEN) throw new Error("SessionClient must be created by KagekoClient");
	}
	snapshot(): Promise<SessionSnapshot> {
		return this.transport.request("sessions.snapshot", { sessionId: this.id });
	}
	prompt(input: PromptInput): Promise<{ readonly turnId: string }> {
		return this.transport.request("sessions.prompt", { sessionId: this.id, prompt: input });
	}
	async promptAndWait(input: PromptInput, listener?: (event: Event) => void): Promise<{ readonly turnId: string }> {
		const requestedTurnId = randomUUID();
		// The server is asked to run the turn under requestedTurnId, but the
		// response is authoritative: if it reports a different id, completion
		// follows the reported one. Terminal events emitted before the response
		// are buffered until the server establishes that correlation.
		let serverTurnId: string | undefined;
		const terminalTurnIdsSeenBeforeAcceptance = new Set<string>();
		const failedTurnIdsSeenBeforeAcceptance = new Map<string, Error>();
		let resolveCompletion: (() => void) | undefined;
		let rejectCompletion: ((error: unknown) => void) | undefined;
		const completion = new Promise<void>((resolve, reject) => {
			resolveCompletion = resolve;
			rejectCompletion = reject;
		});
		// If the prompt request fails, the catch below rejects completion after
		// the caller has already abandoned it; without a standing handler that
		// orphaned rejection would surface as a process-level unhandledRejection.
		// Awaiting `completion` still observes the rejection normally.
		void completion.catch(() => {});
		let rejectTransportClosed!: (error: Error) => void;
		const transportClosed = new Promise<never>((_resolve, reject) => {
			rejectTransportClosed = reject;
		});
		void transportClosed.catch(() => {});
		const detachClose = this.transport.onClose(() => {
			const error = new Error("Kageko transport closed while waiting for turn completion");
			rejectCompletion?.(error);
			rejectTransportClosed(error);
		});
		const unsubscribe = this.transport.subscribe(this.id, (event) => {
			try {
				listener?.(event);
			} catch {
				// Client observation is best-effort and cannot change turn outcome.
			}
			if (event.type === "session.status.changed") {
				// Defense in depth: a session that is closing/closed/failed never
				// produces a terminal turn event for a prompt still queued behind
				// it (session close just drains the queue), so settle the waiter
				// on the terminal status instead of hanging forever.
				const status = typeof event.data.status === "string" ? event.data.status : undefined;
				if (status === "closing" || status === "closed" || status === "failed") {
					rejectCompletion?.(
						new Error(`Session entered terminal status "${status}" while waiting for turn completion`),
					);
				}
				return;
			}
			if (typeof event.meta.turnId !== "string") return;
			const belongsToPrompt = event.meta.turnId === requestedTurnId || event.meta.turnId === serverTurnId;
			if (event.type === "turn.failed" && belongsToPrompt) {
				const message = typeof event.data.message === "string" ? event.data.message : "Turn failed";
				rejectCompletion?.(new Error(message));
				return;
			}
			if (event.type === "turn.failed") {
				const message = typeof event.data.message === "string" ? event.data.message : "Turn failed";
				failedTurnIdsSeenBeforeAcceptance.set(event.meta.turnId, new Error(message));
				return;
			}
			if (event.type !== "turn.end") return;
			if (belongsToPrompt) {
				resolveCompletion?.();
			} else {
				// A compliant in-process host may allocate a server turn id and emit
				// its terminal event synchronously before resolving sessions.prompt.
				// Retain that terminal id until the response establishes correlation.
				terminalTurnIdsSeenBeforeAcceptance.add(event.meta.turnId);
			}
		});
		try {
			const response = (await Promise.race([
				this.transport.request("sessions.prompt", {
					sessionId: this.id,
					prompt: { ...input, turnId: requestedTurnId },
				}),
				transportClosed,
			])) as { turnId?: unknown } | undefined;
			serverTurnId = typeof response?.turnId === "string" ? response.turnId : undefined;
			if (serverTurnId !== undefined && terminalTurnIdsSeenBeforeAcceptance.has(serverTurnId)) resolveCompletion?.();
			if (serverTurnId !== undefined) {
				const failure = failedTurnIdsSeenBeforeAcceptance.get(serverTurnId);
				if (failure) rejectCompletion?.(failure);
			}
			await completion;
			return { turnId: serverTurnId ?? requestedTurnId };
		} catch (error) {
			rejectCompletion?.(error);
			throw error;
		} finally {
			detachClose();
			unsubscribe();
		}
	}
	cancel(turnId?: string, options?: TransportRequestOptions): Promise<void> {
		return this.transport.request("sessions.cancel", { sessionId: this.id, turnId }, options);
	}
	getGoal(options?: TransportRequestOptions): Promise<unknown> {
		return this.transport.request("goals.get", { sessionId: this.id }, options);
	}
	createGoal(
		input: {
			readonly objective: string;
			readonly completionCriterion?: string;
			readonly budget?: GoalBudgetData | null;
		},
		options?: TransportRequestOptions,
	): Promise<unknown> {
		return this.transport.request("goals.create", { sessionId: this.id, ...input }, options);
	}
	updateGoal(
		input: {
			readonly status: "active" | "paused" | "completed" | "blocked";
			readonly note?: string;
		},
		options?: TransportRequestOptions,
	): Promise<unknown> {
		return this.transport.request("goals.update", { sessionId: this.id, ...input }, options);
	}
	compact(instruction?: string, options?: TransportRequestOptions): Promise<unknown> {
		return this.transport.request("sessions.compact", { sessionId: this.id, instruction }, options);
	}
	timeline(options: TransportRequestOptions = {}): Promise<readonly SessionTimelineEntry[]> {
		return this.transport.request("sessions.timeline", { sessionId: this.id }, options);
	}
	restore(sequence: number, timelineId?: string, options?: TransportRequestOptions): Promise<SessionRestoreResult> {
		return this.transport.request("sessions.restore", { sessionId: this.id, sequence, timelineId }, options);
	}
	runShell(
		command: string,
		options: { readonly background?: boolean } = {},
	): Promise<{ readonly taskId: string; readonly status: string }> {
		return this.transport.request("sessions.shell", { sessionId: this.id, command, background: options.background });
	}
	readActivityOutput(
		taskId: string,
		offset = 0,
		limit?: number,
		options: TransportRequestOptions = {},
	): Promise<ActivityOutputChunk> {
		return this.transport.request("activities.output", { sessionId: this.id, taskId, offset, limit }, options);
	}
	stopActivity(taskId: string, options: TransportRequestOptions = {}): Promise<void> {
		return this.transport.request("activities.stop", { sessionId: this.id, taskId }, options);
	}
	/**
	 * Streams a server-atomic durable-history plus live tail. The application
	 * installs the tail before reading history and serializes durable appends
	 * behind that barrier, so this iterator never client-side merges two lanes.
	 */
	events(options: EventStreamOptions = {}): AsyncIterable<Event> {
		const fromSequence = options.fromSequence ?? 1;
		const maxBufferedEvents = options.maxBufferedEvents ?? 256;
		if (!Number.isSafeInteger(fromSequence) || fromSequence < 1)
			throw new Error("fromSequence must be a positive safe integer");
		if (!Number.isSafeInteger(maxBufferedEvents) || maxBufferedEvents < 1)
			throw new Error("maxBufferedEvents must be a positive safe integer");
		const queue: Event[] = [];
		const waiters: (() => void)[] = [];
		let done = false;
		let overflow: EventStreamOverflowError | undefined;
		let lastDeliveredDurableSequence = fromSequence - 1;
		let resolveClosed!: () => void;
		let detachClose: (() => void) | undefined;
		const closed = new Promise<void>((resolve) => {
			resolveClosed = resolve;
		});
		let streamDispose: (() => void) | undefined;
		let opened: Promise<{ readonly history: readonly Event[]; readonly dispose: () => void }> | undefined;
		const stop = (): void => {
			if (done) return;
			done = true;
			resolveClosed();
			streamDispose?.();
			queue.length = 0;
			detachClose?.();
			for (const wake of waiters.splice(0)) wake();
		};
		const start = (): Promise<{ readonly history: readonly Event[]; readonly dispose: () => void }> => {
			if (opened) return opened;
			detachClose = this.transport.onClose(stop);
			opened = this.transport.openEventStream(this.id, fromSequence, (event) => {
				if (done) return;
				if (queue.length >= maxBufferedEvents) {
					overflow = new EventStreamOverflowError(this.id, lastDeliveredDurableSequence + 1, maxBufferedEvents);
					stop();
					return;
				}
				queue.push(event);
				for (const wake of waiters.splice(0)) wake();
			});
			void opened.then(
				(stream) => {
					streamDispose = stream.dispose;
					if (done) stream.dispose();
				},
				() => {},
			);
			return opened;
		};
		let history: readonly Event[] | undefined;
		let historyIndex = 0;
		const iterator: AsyncIterator<Event, void> = {
			next: async (): Promise<IteratorResult<Event, void>> => {
				for (;;) {
					if (overflow) throw overflow;
					if (done) return { done: true, value: undefined };
					if (!history) {
						try {
							const opening = start();
							const result = await Promise.race([
								opening.then((stream) => ({ stream })),
								closed.then(() => ({ stream: undefined })),
							]);
							if (result.stream === undefined || done) return { done: true, value: undefined };
							history = result.stream.history;
						} catch (error) {
							stop();
							throw error;
						}
					}
					if (historyIndex < history.length) {
						const event = history[historyIndex++]!;
						if ("sequence" in event.meta) {
							if (event.meta.sequence <= lastDeliveredDurableSequence) continue;
							lastDeliveredDurableSequence = event.meta.sequence;
						}
						return { done: false, value: event };
					}
					const buffered = queue.shift();
					if (buffered !== undefined) {
						if ("sequence" in buffered.meta) {
							if (buffered.meta.sequence <= lastDeliveredDurableSequence) continue;
							lastDeliveredDurableSequence = buffered.meta.sequence;
						}
						return { done: false, value: buffered };
					}
					await new Promise<void>((resolve) => {
						waiters.push(resolve);
					});
				}
			},
			return: async (): Promise<IteratorResult<Event, void>> => {
				stop();
				return { done: true, value: undefined };
			},
		};
		return { [Symbol.asyncIterator]: () => iterator };
	}
	close(): Promise<void> {
		return this.transport.request("sessions.close", { sessionId: this.id });
	}
}

/** @internal SDK construction path; transports are never a client-facing API. */
export function createSessionClient(transport: Transport, id: string): SessionClient {
	return new SessionClient(transport, id, SESSION_CLIENT_TOKEN);
}

export interface EventStreamOptions {
	readonly fromSequence?: number;
	/** Maximum unconsumed live events before the iterator closes with a recoverable overflow error. */
	readonly maxBufferedEvents?: number;
}

/** A live tail overflowed; resume from `resumeFromSequence` to replay durable events. */
export class EventStreamOverflowError extends Error {
	override readonly name = "EventStreamOverflowError";
	constructor(
		readonly sessionId: string,
		readonly resumeFromSequence: number,
		readonly maxBufferedEvents: number,
	) {
		super(
			`Event stream for ${sessionId} exceeded its ${maxBufferedEvents}-event live buffer; resume from durable sequence ${resumeFromSequence}`,
		);
	}
}
