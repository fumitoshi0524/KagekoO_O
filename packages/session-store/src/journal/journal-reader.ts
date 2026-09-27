import { readFile, stat } from "node:fs/promises";
import type { DurableEvent } from "@kageko/protocol";
import { EVENT_SCHEMA_VERSION } from "@kageko/protocol";
import { migrateJournalEvent } from "../migration/event-migrator.js";
import {
	JOURNAL_FORMAT_VERSION,
	JOURNAL_HEADER_TYPE,
	MAX_JOURNAL_BYTES,
	JournalCorruptionError,
	JournalIncompatibleError,
} from "./journal-format.js";
export class JournalReader {
	constructor(
		readonly filePath: string,
		readonly sessionId?: string,
	) {}
	async read(fromSequence = 1): Promise<DurableEvent[]> {
		if (!Number.isSafeInteger(fromSequence) || fromSequence < 1) {
			throw new RangeError("Journal read fromSequence must be a positive safe integer");
		}
		let text: string;
		try {
			text = await readFile(this.filePath, "utf8");
		} catch (error) {
			if ((error as NodeJS.ErrnoException).code === "ENOENT") return [];
			throw error;
		}
		if (!text) return [];
		const info = await stat(this.filePath);
		if (info.size > MAX_JOURNAL_BYTES) throw new JournalCorruptionError("Journal exceeds maximum size");
		const lines = text.split("\n");
		if (lines.at(-1) !== "") throw new JournalCorruptionError("Journal has an incomplete final line");
		let header: { type?: string; formatVersion?: number; eventSchemaVersion?: number; sessionId?: string };
		try {
			header = JSON.parse(lines[0] ?? "null") as typeof header;
		} catch (error) {
			throw new JournalCorruptionError("Invalid journal header", { cause: error });
		}
		if (
			header.type !== JOURNAL_HEADER_TYPE ||
			header.formatVersion !== JOURNAL_FORMAT_VERSION ||
			header.eventSchemaVersion !== EVENT_SCHEMA_VERSION
		)
			throw new JournalIncompatibleError("Invalid journal header");
		if (this.sessionId && header.sessionId !== this.sessionId)
			throw new JournalIncompatibleError("Journal session mismatch");
		// Every event line is parsed and validated/migrated individually: a
		// corrupted or tampered line fails the read with a corruption error
		// instead of an unchecked cast flowing downstream.
		// Writers reject blank lines and duplicate event ids. Readers deliberately
		// tolerate both for compatibility with already-produced journals while
		// still enforcing envelope validity and contiguous sequence ordering.
		const events = lines
			.slice(1, -1)
			.filter(Boolean)
			.map((line, index) => {
				let parsed: unknown;
				try {
					parsed = JSON.parse(line);
				} catch (error) {
					throw new JournalCorruptionError(`Invalid journal event at line ${index + 2}`, { cause: error });
				}
				try {
					return migrateJournalEvent(parsed);
				} catch (error) {
					throw new JournalCorruptionError(`Invalid journal event at line ${index + 2}`, { cause: error });
				}
			});
		for (const [index, event] of events.entries()) {
			if (event.meta.sequence !== index + 1) throw new JournalCorruptionError("Journal event sequence mismatch");
			if (this.sessionId && event.meta.sessionId !== this.sessionId)
				throw new JournalCorruptionError("Journal event session mismatch");
		}
		return events.filter((event) => event.meta.sequence >= fromSequence);
	}
}
