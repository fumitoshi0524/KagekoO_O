import { readFile } from "node:fs/promises";
import type { Snapshot } from "./snapshot.js";
import { persistenceDiagnostic, SessionPersistenceError } from "../diagnostics.js";

export class SnapshotReader {
	constructor(
		readonly filePath: string,
		readonly sessionId: string,
	) {}
	async read(): Promise<Snapshot | undefined> {
		try {
			const value = JSON.parse(await readFile(this.filePath, "utf8")) as unknown;
			if (!isSnapshot(value)) throw new Error("Snapshot has an invalid shape");
			if (value.sessionId !== this.sessionId) throw new Error("Snapshot session mismatch");
			return value;
		} catch (error) {
			if ((error as NodeJS.ErrnoException).code === "ENOENT") return undefined;
			if (error instanceof SessionPersistenceError) throw error;
			throw new SessionPersistenceError(
				persistenceDiagnostic("snapshot-corrupt", this.sessionId, this.filePath, errorMessage(error)),
				{ cause: error },
			);
		}
	}
}

function isSnapshot(value: unknown): value is Snapshot {
	if (typeof value !== "object" || value === null || Array.isArray(value)) return false;
	const candidate = value as Partial<Snapshot>;
	return (
		Number.isSafeInteger(candidate.schemaVersion) &&
		(candidate.schemaVersion ?? 0) > 0 &&
		typeof candidate.sessionId === "string" &&
		Number.isSafeInteger(candidate.sequence) &&
		(candidate.sequence ?? -1) >= 0 &&
		Object.hasOwn(candidate, "state")
	);
}

function errorMessage(error: unknown): string {
	return error instanceof Error ? error.message : String(error);
}
