// Public surface: the session repository contract plus the types consumers
// legitimately handle. Journal/snapshot/metadata implementations stay internal
// so the repository remains the only writer of `.kageko/sessions/<id>`.
export type {
	SessionRepository,
	RuntimeSessionRepository,
	SessionSummary,
	SessionSnapshot,
	CreateSessionInput,
	SessionListQuery,
	SessionListResult,
} from "./repository/session-repository.js";
export { FileSessionRepository } from "./repository/file-session-repository.js";
export { SessionPersistenceError } from "./diagnostics.js";
export type { SessionPersistenceDiagnostic, SessionPersistenceDiagnosticCode } from "./diagnostics.js";
export { JournalCorruptionError, JournalIncompatibleError, JournalFaultedError } from "./journal/journal-format.js";
export type { SessionMetadataPatch } from "./metadata/metadata.js";
export {
	RuntimeLease,
	RuntimeLeaseError,
	RuntimeLeaseBusyError,
	RuntimeLeaseCompromisedError,
} from "./lease/runtime-lease.js";
export type { RuntimeLeaseOwner } from "./lease/runtime-lease.js";
export { SessionPaths } from "./paths/session-paths.js";
export { replaceAtomically, retryTransientFileOperation } from "./atomic-replace.js";
export type { AtomicReplaceOptions, TransientFileRetryOptions } from "./atomic-replace.js";
