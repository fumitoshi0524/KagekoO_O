import {
	EVENT_SCHEMA_VERSION,
	effectiveSessionEvents,
	type DurableEvent,
	type DurableEventInput,
	type DurableEventType,
	type RuntimeEvent,
} from "@kageko/protocol";
import type { SessionRepository } from "@kageko/session-store";
import { randomUUID } from "node:crypto";

export type EventListener = (event: RuntimeEvent) => void | Promise<void>;
export interface Disposable {
	dispose(): void;
}
interface ListenerRegistration {
	readonly listener: EventListener;
	active: boolean;
}
export interface EventDeliveryFailure {
	readonly event: RuntimeEvent;
	readonly error: unknown;
}
export type EventDeliveryFailureReporter = (failure: EventDeliveryFailure) => void | Promise<void>;
export interface OpenEventStream {
	readonly history: readonly DurableEvent[];
	readonly dispose: () => void;
}

export class EventHub {
	private readonly listeners = new Map<string, Set<ListenerRegistration>>();
	private readonly globalListeners = new Set<ListenerRegistration>();
	private readonly controlChains = new Map<string, Promise<void>>();
	private closed = false;
	constructor(
		private readonly repository?: SessionRepository,
		private readonly reportDeliveryFailure?: EventDeliveryFailureReporter,
	) {}
	subscribe(sessionId: string, listener: EventListener): Disposable {
		if (this.closed) return { dispose: () => {} };
		const registration: ListenerRegistration = { listener, active: true };
		const set = this.listeners.get(sessionId) ?? new Set<ListenerRegistration>();
		set.add(registration);
		this.listeners.set(sessionId, set);
		return {
			dispose: () => {
				registration.active = false;
				set.delete(registration);
				if (!set.size) this.listeners.delete(sessionId);
			},
		};
	}
	/** Global observation for activity dashboards. It is still best-effort. */
	subscribeAll(listener: EventListener): Disposable {
		if (this.closed) return { dispose: () => {} };
		const registration: ListenerRegistration = { listener, active: true };
		this.globalListeners.add(registration);
		return {
			dispose: () => {
				registration.active = false;
				this.globalListeners.delete(registration);
			},
		};
	}
	/**
	 * Replays journaled durable events in sequence order. Live events are
	 * ephemeral by contract and never reach the journal, so replay covers
	 * durable events only; subscribers use subscribe() for the live tail.
	 */
	async *replay(sessionId: string, fromSequence = 1): AsyncIterable<DurableEvent> {
		if (!this.repository) throw new Error("EventHub replay requires a session repository");
		const events = await this.runControl(sessionId, async () =>
			effectiveSessionEvents(await this.repository!.read(sessionId)).filter(
				(event) => event.meta.sequence >= fromSequence,
			),
		);
		for (const event of events) yield event;
	}
	async publish(event: RuntimeEvent): Promise<void> {
		if (this.closed) return;
		// Live observation is explicitly best-effort, like Kimi's loop event
		// emitter. A slow or permanently pending host callback must never create
		// a per-session backlog, delay a later event, or outlive shutdown as a
		// retained delivery lane. Synchronous invocation preserves emission order;
		// completion order of async observers is intentionally not part of the API.
		for (const registration of [...(this.listeners.get(event.meta.sessionId) ?? []), ...this.globalListeners]) {
			if (!registration.active || this.closed) continue;
			try {
				void Promise.resolve(registration.listener(event)).catch((error: unknown) => {
					void this.reportFailure({ event, error });
				});
			} catch (error) {
				void this.reportFailure({ event, error });
			}
		}
	}
	/** Opens one atomic durable-history plus live-tail stream for a session. */
	async openStream(sessionId: string, fromSequence: number, listener: EventListener): Promise<OpenEventStream> {
		if (!this.repository) throw new Error("EventHub streams require a session repository");
		return this.runControl(sessionId, async () => {
			if (this.closed) throw new Error("EventHub is closed");
			const subscription = this.subscribe(sessionId, listener);
			try {
				const history = effectiveSessionEvents(await this.repository!.read(sessionId)).filter(
					(event) => event.meta.sequence >= fromSequence,
				);
				return { history, dispose: () => subscription.dispose() };
			} catch (error) {
				subscription.dispose();
				throw error;
			}
		});
	}
	/** The sole application durable-append path for executable session events. */
	async append<K extends DurableEventType>(sessionId: string, input: DurableEventInput<K>): Promise<DurableEvent<K>> {
		if (!this.repository) throw new Error("EventHub durable append requires a session repository");
		return this.runControl(sessionId, async () => {
			if (this.closed) throw new Error("EventHub is closed");
			const [persisted] = await this.repository!.appendInputs(sessionId, [input] as readonly DurableEventInput[]);
			if (!persisted) throw new Error(`Repository did not append journal event for session ${sessionId}`);
			await this.publish(persisted);
			return persisted as DurableEvent<K>;
		});
	}
	async close(): Promise<void> {
		if (this.closed) return;
		this.closed = true;
		for (const registrations of this.listeners.values())
			for (const registration of registrations) registration.active = false;
		this.listeners.clear();
		this.globalListeners.clear();
		this.controlChains.clear();
	}
	private async runControl<T>(sessionId: string, operation: () => Promise<T>): Promise<T> {
		const prior = this.controlChains.get(sessionId);
		if (!prior) {
			let immediate: Promise<T>;
			try {
				immediate = Promise.resolve(operation());
			} catch (error) {
				immediate = Promise.reject(error);
			}
			const settled = immediate.then(
				() => undefined,
				() => undefined,
			);
			this.controlChains.set(sessionId, settled);
			void settled.finally(() => {
				if (this.controlChains.get(sessionId) === settled) this.controlChains.delete(sessionId);
			});
			return immediate;
		}
		let resolveResult!: (value: T) => void;
		let rejectResult!: (reason: unknown) => void;
		const result = new Promise<T>((resolve, reject) => {
			resolveResult = resolve;
			rejectResult = reject;
		});
		const next = prior
			.catch(() => {})
			.then(async () => {
				try {
					resolveResult(await operation());
				} catch (error) {
					rejectResult(error);
				}
			});
		this.controlChains.set(sessionId, next);
		void next.finally(() => {
			if (this.controlChains.get(sessionId) === next) this.controlChains.delete(sessionId);
		});
		return result;
	}
	private async reportFailure(failure: EventDeliveryFailure): Promise<void> {
		try {
			await this.reportDeliveryFailure?.(failure);
		} catch {
			// Diagnostics are observational too. Never create an unhandled
			// rejection or feed a diagnostic failure back into event delivery.
		}
	}
	async publishStatus(
		sessionId: string,
		status: "ready" | "running" | "awaiting_approval" | "awaiting_question" | "closing" | "closed" | "failed",
		previous?: string,
	): Promise<void> {
		await this.publish({
			type: "session.status.changed",
			meta: { schemaVersion: EVENT_SCHEMA_VERSION, eventId: randomUUID(), sessionId, occurredAt: Date.now() },
			data: { status, previous },
		});
	}
}
