import { EventStreamOverflowError, type Event, type SessionClient } from "@kageko/node-sdk";

/** Bounded recovery for non-overflow iterator errors before the stream is declared dead. */
const MAX_STREAM_ERROR_RETRIES = 3;
const STREAM_ERROR_BACKOFF_MS = 250;

export interface SessionEventStreamCallbacks {
	readonly isActive: (session: SessionClient, generation: number) => boolean;
	readonly onEvent: (event: Event) => void;
	readonly onReconnect: (resumeFromSequence: number) => void;
	readonly onError: (error: unknown) => void;
}

/**
 * Owns the only long-lived async iterator used by the TUI.
 *
 * The controller deliberately knows nothing about rendering. It provides one
 * lifecycle boundary for replay recovery, durable-event deduplication, and
 * cancellation so session switches cannot leave orphaned readers behind.
 */
export class SessionEventStream {
	private task: Promise<void> | undefined;
	private iterator: AsyncIterator<Event> | undefined;
	private lastSeenSequence = 0;
	private cancelRun: (() => void) | undefined;
	private lifecycleVersion = 0;

	constructor(private readonly callbacks: SessionEventStreamCallbacks) {}

	async start(session: SessionClient, generation: number): Promise<void> {
		const lifecycleVersion = ++this.lifecycleVersion;
		await this.stopCurrent();
		if (lifecycleVersion !== this.lifecycleVersion) return;
		this.lastSeenSequence = 0;
		const task = this.run(session, generation);
		this.task = task;
		await task;
	}

	async stop(): Promise<void> {
		this.lifecycleVersion += 1;
		await this.stopCurrent();
	}

	private async stopCurrent(): Promise<void> {
		const iterator = this.iterator;
		const task = this.task;
		this.iterator = undefined;
		this.task = undefined;
		this.cancelRun?.();
		this.cancelRun = undefined;
		void iterator?.return?.().catch(() => {});
		await task?.catch(() => {});
	}

	private async run(session: SessionClient, generation: number): Promise<void> {
		const stopped = Symbol("stopped");
		let cancel!: () => void;
		const stopSignal = new Promise<typeof stopped>((resolve) => {
			cancel = () => resolve(stopped);
		});
		this.cancelRun = cancel;
		let fromSequence = 1;
		let consecutiveErrors = 0;
		try {
			stream: while (this.callbacks.isActive(session, generation)) {
				const iterator = session.events({ fromSequence })[Symbol.asyncIterator]();
				this.iterator = iterator;
				try {
					for (;;) {
						const next = await Promise.race([iterator.next(), stopSignal]);
						if (next === stopped || !this.callbacks.isActive(session, generation)) return;
						if (next.done) {
							// Some transports expose a finite journal tail instead of a
							// never-ending subscription. Reopen it from the durable cursor;
							// otherwise a clean EOF makes the TUI permanently miss later
							// turn-end and interaction events.
							const wait = await Promise.race([
								new Promise<undefined>((resolve) => setTimeout(() => resolve(undefined), STREAM_ERROR_BACKOFF_MS)),
								stopSignal,
							]);
							if (wait === stopped || !this.callbacks.isActive(session, generation)) return;
							continue stream;
						}
						const event = next.value;
						consecutiveErrors = 0;
						const sequence = "sequence" in event.meta ? event.meta.sequence : undefined;
						if (sequence !== undefined) {
							fromSequence = Math.max(fromSequence, sequence + 1);
							if (sequence <= this.lastSeenSequence) continue;
							this.lastSeenSequence = sequence;
						}
						this.callbacks.onEvent(event);
					}
				} catch (error) {
					if (error instanceof EventStreamOverflowError && this.callbacks.isActive(session, generation)) {
						consecutiveErrors = 0;
						fromSequence = Math.max(fromSequence, error.resumeFromSequence);
						this.callbacks.onReconnect(error.resumeFromSequence);
						continue;
					}
					if (!this.callbacks.isActive(session, generation)) return;
					consecutiveErrors += 1;
					if (consecutiveErrors <= MAX_STREAM_ERROR_RETRIES) {
						// A non-overflow iterator error is often transient (transport
						// hiccup, host restart); retry with bounded backoff and resume
						// from the durable sequence before giving up on the stream.
						const wait = await Promise.race([
							new Promise<undefined>((resolve) =>
								setTimeout(() => resolve(undefined), STREAM_ERROR_BACKOFF_MS * 2 ** (consecutiveErrors - 1)),
							),
							stopSignal,
						]);
						if (wait === stopped || !this.callbacks.isActive(session, generation)) return;
						continue;
					}
					this.callbacks.onError(error);
					return;
				} finally {
					if (this.iterator === iterator) this.iterator = undefined;
				}
			}
		} finally {
			if (this.cancelRun === cancel) this.cancelRun = undefined;
		}
	}
}
