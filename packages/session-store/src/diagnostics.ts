export type SessionPersistenceDiagnosticCode =
	| "metadata-missing"
	| "metadata-corrupt"
	| "journal-corrupt"
	| "journal-truncated"
	| "snapshot-corrupt"
	| "snapshot-ahead-of-journal";

export interface SessionPersistenceDiagnostic {
	readonly code: SessionPersistenceDiagnosticCode;
	readonly sessionId: string;
	readonly filePath: string;
	readonly message: string;
}

export class SessionPersistenceError extends Error {
	constructor(
		readonly diagnostic: SessionPersistenceDiagnostic,
		options?: ErrorOptions,
	) {
		super(`${diagnostic.code}: ${diagnostic.message} (${diagnostic.filePath})`, options);
		this.name = "SessionPersistenceError";
	}
}

export function persistenceDiagnostic(
	code: SessionPersistenceDiagnosticCode,
	sessionId: string,
	filePath: string,
	message: string,
): SessionPersistenceDiagnostic {
	return { code, sessionId, filePath, message };
}
