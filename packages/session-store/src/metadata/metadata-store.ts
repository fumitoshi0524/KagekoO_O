import { link, mkdir, open, readFile, unlink } from "node:fs/promises";
import path from "node:path";
import type { SessionMetadata, SessionMetadataPatch } from "./metadata.js";
import { replaceAtomically } from "../atomic-replace.js";
import { persistenceDiagnostic, SessionPersistenceError } from "../diagnostics.js";

export class MetadataStore {
	constructor(
		readonly filePath: string,
		readonly expectedSessionId?: string,
	) {}
	async read(): Promise<SessionMetadata | undefined> {
		let parsed: unknown;
		try {
			parsed = JSON.parse(await readFile(this.filePath, "utf8")) as unknown;
		} catch (error) {
			if ((error as NodeJS.ErrnoException).code === "ENOENT") return undefined;
			throw this.corrupt("Session metadata is not valid JSON", error);
		}
		if (!isSessionMetadata(parsed)) throw this.corrupt("Session metadata has an invalid shape");
		if (this.expectedSessionId !== undefined && parsed.sessionId !== this.expectedSessionId) {
			throw this.corrupt(`Session metadata belongs to ${parsed.sessionId}`);
		}
		return parsed;
	}
	async create(input: Omit<SessionMetadata, "updatedAt">): Promise<SessionMetadata> {
		const value = { ...input, updatedAt: input.createdAt };
		await this.writeNew(value);
		return value;
	}
	async patch(patch: SessionMetadataPatch): Promise<SessionMetadata> {
		const current = await this.read();
		if (!current) throw new Error("Session metadata does not exist");
		const value = {
			...current,
			...(patch.title === undefined ? {} : { title: patch.title }),
			...(patch.archived === undefined ? {} : { archived: patch.archived }),
			updatedAt: Date.now(),
		};
		await this.write(value);
		return value;
	}
	private async write(value: SessionMetadata): Promise<void> {
		await mkdir(path.dirname(this.filePath), { recursive: true, mode: 0o700 });
		const temporary = `${this.filePath}.${process.pid}.${Date.now().toString(36)}.tmp`;
		let handle: Awaited<ReturnType<typeof open>> | undefined;
		try {
			handle = await open(temporary, "wx", 0o600);
			await handle.writeFile(`${JSON.stringify(value, null, 2)}\n`, "utf8");
			await handle.sync();
			await handle.close();
			handle = undefined;
			await replaceAtomically(temporary, this.filePath);
		} catch (error) {
			await handle?.close().catch(() => {});
			await unlink(temporary).catch(() => {});
			throw error;
		}
	}

	private async writeNew(value: SessionMetadata): Promise<void> {
		await mkdir(path.dirname(this.filePath), { recursive: true, mode: 0o700 });
		const temporary = `${this.filePath}.${process.pid}.${Date.now().toString(36)}.tmp`;
		let handle: Awaited<ReturnType<typeof open>> | undefined;
		try {
			handle = await open(temporary, "wx", 0o600);
			await handle.writeFile(`${JSON.stringify(value, null, 2)}\n`, "utf8");
			await handle.sync();
			await handle.close();
			handle = undefined;
			// link is an atomic no-overwrite publication primitive; rename is not.
			await link(temporary, this.filePath);
			await unlink(temporary);
		} catch (error) {
			await handle?.close().catch(() => {});
			await unlink(temporary).catch(() => {});
			throw error;
		}
	}

	private corrupt(message: string, cause?: unknown): SessionPersistenceError {
		return new SessionPersistenceError(
			persistenceDiagnostic("metadata-corrupt", this.expectedSessionId ?? "unknown", this.filePath, message),
			cause === undefined ? undefined : { cause },
		);
	}
}

function isSessionMetadata(value: unknown): value is SessionMetadata {
	if (typeof value !== "object" || value === null || Array.isArray(value)) return false;
	const candidate = value as Partial<SessionMetadata>;
	return (
		typeof candidate.sessionId === "string" &&
		candidate.sessionId.length > 0 &&
		typeof candidate.cwd === "string" &&
		(typeof candidate.title === "string" || candidate.title === null) &&
		isTimestamp(candidate.createdAt) &&
		isTimestamp(candidate.updatedAt) &&
		candidate.updatedAt >= candidate.createdAt &&
		typeof candidate.archived === "boolean"
	);
}

function isTimestamp(value: unknown): value is number {
	return typeof value === "number" && Number.isSafeInteger(value) && value >= 0;
}
