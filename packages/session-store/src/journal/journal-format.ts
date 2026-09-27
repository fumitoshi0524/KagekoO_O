export const JOURNAL_FORMAT_VERSION = 1 as const;
export const JOURNAL_HEADER_TYPE = "kageko.session-journal" as const;
export const MAX_JOURNAL_BYTES: number = 128 * 1024 * 1024;
export class JournalCorruptionError extends Error {}
export class JournalIncompatibleError extends Error {}
export class JournalFaultedError extends Error {}
export interface JournalHeader {
	readonly type: typeof JOURNAL_HEADER_TYPE;
	readonly formatVersion: typeof JOURNAL_FORMAT_VERSION;
	readonly sessionId: string;
	readonly createdAt: number;
}
