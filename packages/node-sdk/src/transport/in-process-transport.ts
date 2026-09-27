import type { Event } from "../types/events.js";
import type {
	ApplicationMethod,
	ApplicationRequestInput,
	ApplicationRequestOutput,
	Transport,
	TransportRequestOptions,
} from "./transport.js";
export interface InProcessHandler {
	handle<K extends ApplicationMethod>(
		method: K,
		payload: ApplicationRequestInput<K>,
		context: InProcessRequestContext,
	): Promise<ApplicationRequestOutput<K>>;
	subscribe?(sessionId: string, listener: (event: Event) => void): () => void;
	subscribeAll?(listener: (event: Event) => void): () => void;
	openEventStream?(
		sessionId: string,
		fromSequence: number,
		listener: (event: Event) => void,
		context: InProcessRequestContext,
	): Promise<{ readonly history: readonly Event[]; readonly dispose: () => void }>;
	close?(): Promise<void>;
}

/** Request-scoped cancellation supplied by the SDK transport to its host. */
export interface InProcessRequestContext {
	readonly signal: AbortSignal;
}

interface PendingOperation {
	readonly controller: AbortController;
	reject(error: Error): void;
}

export class InProcessTransport implements Transport {
	private closed = false;
	private hostClosed = false;
	private closePromise: Promise<void> | undefined;
	private readonly disposers = new Set<() => void>();
	private readonly closeListeners = new Set<() => void>();
	private readonly pending = new Set<PendingOperation>();
	constructor(private readonly handler: InProcessHandler) {}
	request<K extends ApplicationMethod>(
		method: K,
		payload?: ApplicationRequestInput<K>,
		options?: TransportRequestOptions,
	): Promise<ApplicationRequestOutput<K>> {
		return this.runPending(
			(context) => this.handler.handle(method, payload as ApplicationRequestInput<K>, context),
			options?.signal,
		);
	}
	subscribe(sessionId: string, listener: (event: Event) => void): () => void {
		if (this.closed) throw new Error("Kageko transport is closed");
		if (!this.handler.subscribe) throw new Error("Transport does not support event subscriptions");
		const dispose = this.handler.subscribe(sessionId, listener);
		return this.track(dispose);
	}
	subscribeAll(listener: (event: Event) => void): () => void {
		if (this.closed) throw new Error("Kageko transport is closed");
		if (!this.handler.subscribeAll) throw new Error("Transport does not support global event subscriptions");
		return this.track(this.handler.subscribeAll(listener));
	}
	async openEventStream(
		sessionId: string,
		fromSequence: number,
		listener: (event: Event) => void,
	): Promise<{ readonly history: readonly Event[]; readonly dispose: () => void }> {
		if (!this.handler.openEventStream) throw new Error("Transport does not support atomic event streams");
		const stream = await this.runPending((context) =>
			this.handler.openEventStream!(sessionId, fromSequence, listener, context),
		);
		if (this.closed) {
			stream.dispose();
			throw this.closedError();
		}
		return { history: stream.history, dispose: this.track(stream.dispose) };
	}
	onClose(listener: () => void): () => void {
		if (this.closed) {
			listener();
			return () => {};
		}
		this.closeListeners.add(listener);
		return () => this.closeListeners.delete(listener);
	}
	async close(): Promise<void> {
		if (this.hostClosed) return;
		if (this.closePromise) return this.closePromise;
		if (!this.closed) {
			this.closed = true;
			const error = this.closedError();
			for (const pending of [...this.pending]) {
				pending.controller.abort(error);
				pending.reject(error);
			}
			this.pending.clear();
			for (const listener of [...this.closeListeners]) {
				try {
					listener();
				} catch {
					/* host shutdown is best-effort */
				}
			}
			this.closeListeners.clear();
			for (const dispose of [...this.disposers]) {
				try {
					dispose();
				} catch {
					/* host shutdown is best-effort */
				}
			}
			this.disposers.clear();
		}
		this.closePromise = Promise.resolve(this.handler.close?.());
		try {
			await this.closePromise;
			this.hostClosed = true;
		} catch (error) {
			// The public transport is already admission-closed, but the application
			// remains its owner until its close succeeds on a later retry.
			this.closePromise = undefined;
			throw error;
		}
	}
	private track(dispose: () => void): () => void {
		let active = true;
		const tracked = (): void => {
			if (!active) return;
			active = false;
			this.disposers.delete(tracked);
			dispose();
		};
		this.disposers.add(tracked);
		return tracked;
	}
	private runPending<T>(operation: (context: InProcessRequestContext) => Promise<T>, signal?: AbortSignal): Promise<T> {
		if (this.closed) return Promise.reject(this.closedError());
		if (signal?.aborted)
			return Promise.reject(
				signal.reason instanceof Error ? signal.reason : new Error("Application request was aborted"),
			);
		const controller = new AbortController();
		return new Promise<T>((resolve, reject) => {
			const cleanup = (): void => signal?.removeEventListener("abort", abort);
			const pending: PendingOperation = {
				controller,
				reject: (error) => {
					cleanup();
					reject(error);
				},
			};
			const abort = (): void => {
				const error = signal?.reason instanceof Error ? signal.reason : new Error("Application request was aborted");
				controller.abort(error);
				if (!this.pending.delete(pending)) return;
				cleanup();
				reject(error);
			};
			this.pending.add(pending);
			signal?.addEventListener("abort", abort, { once: true });
			void Promise.resolve()
				.then(() => {
					if (controller.signal.aborted) throw controller.signal.reason ?? this.closedError();
					return operation({ signal: controller.signal });
				})
				.then(
					(value) => {
						if (!this.pending.delete(pending)) return;
						cleanup();
						resolve(value);
					},
					(error: unknown) => {
						if (!this.pending.delete(pending)) return;
						cleanup();
						reject(error);
					},
				);
		});
	}
	private closedError(): Error {
		return new Error("Kageko transport is closed");
	}
}
