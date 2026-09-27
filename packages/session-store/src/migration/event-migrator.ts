import { EVENT_SCHEMA_VERSION, isDurableEvent, type DurableEvent } from "@kageko/protocol";

/** Migrate only events from schemas explicitly supported by the journal. */
export function migrateJournalEvent(value: unknown): DurableEvent {
	if (!isDurableEvent(value)) {
		throw new Error("Unsupported journal event schema");
	}
	if (value.meta.schemaVersion !== EVENT_SCHEMA_VERSION) {
		throw new Error(`Unsupported journal event schema version: ${String(value.meta.schemaVersion)}`);
	}
	return value;
}

export function migrateJournalEvents(values: readonly unknown[]): DurableEvent[] {
	return values.map(migrateJournalEvent);
}
