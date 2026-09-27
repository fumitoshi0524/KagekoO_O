import type { DurableEvent, DurableEventInput, DurableEventType } from "@kageko/protocol";

export interface RepositoryPort {
	append(sessionId: string, events: readonly unknown[]): Promise<void>;
}
/** Persistence port consumed by the engine; application supplies the journal implementation. */
export interface JournalPort {
	readonly sessionId: string;
	readonly fault?: Error;
	append<K extends DurableEventType>(event: DurableEventInput<K>): Promise<DurableEvent<K>>;
	load(): Promise<DurableEvent[]>;
}
