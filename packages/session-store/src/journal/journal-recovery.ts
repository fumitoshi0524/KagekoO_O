import { open, readFile, unlink } from "node:fs/promises";
import { randomUUID } from "node:crypto";
import { createHash } from "node:crypto";
import type { DurableEvent } from "@kageko/protocol";
import { JournalReader } from "./journal-reader.js";
import { JournalCorruptionError } from "./journal-format.js";

export interface JournalRecoveryInspection {
	readonly events: readonly DurableEvent[];
	readonly truncated: boolean;
	readonly validBytes: number;
	readonly discardedBytes: number;
	readonly contentHash: string | null;
}

export class JournalRecovery {
	constructor(
		readonly filePath: string,
		readonly sessionId: string,
	) {}
	async inspect(): Promise<JournalRecoveryInspection> {
		let content: Buffer;
		try {
			content = await readFile(this.filePath);
		} catch (error) {
			if ((error as NodeJS.ErrnoException).code === "ENOENT") {
				return { events: [], truncated: false, validBytes: 0, discardedBytes: 0, contentHash: null };
			}
			throw error;
		}
		if (content.length === 0) throw new JournalCorruptionError("Journal is empty");
		if (content.at(-1) === 0x0a) {
			return {
				events: await new JournalReader(this.filePath, this.sessionId).read(),
				truncated: false,
				validBytes: content.length,
				discardedBytes: 0,
				contentHash: hash(content),
			};
		}

		const lastNewline = content.lastIndexOf(0x0a);
		if (lastNewline < 0) throw new JournalCorruptionError("Journal header is incomplete");
		const validBytes = lastNewline + 1;
		const prefix = content.subarray(0, validBytes);
		const temporaryPath = `${this.filePath}.${process.pid}.${randomUUID()}.recovery-read`;
		const handle = await open(temporaryPath, "wx", 0o600);
		try {
			await handle.writeFile(prefix);
			await handle.close();
			const events = await new JournalReader(temporaryPath, this.sessionId).read();
			return {
				events,
				truncated: true,
				validBytes,
				discardedBytes: content.length - validBytes,
				contentHash: hash(content),
			};
		} finally {
			await handle.close().catch(() => {});
			await unlink(temporaryPath).catch(() => {});
		}
	}

	async recoverTruncatedTail(): Promise<JournalRecoveryInspection> {
		const inspection = await this.inspect();
		if (!inspection.truncated) return inspection;
		const handle = await open(this.filePath, "r+");
		try {
			const current = await handle.readFile();
			if (inspection.contentHash === null || hash(current) !== inspection.contentHash) {
				throw new JournalCorruptionError("Journal changed after recovery inspection; refusing to truncate");
			}
			await handle.truncate(inspection.validBytes);
			await handle.sync();
		} finally {
			await handle.close();
		}
		return inspection;
	}
}

function hash(content: Uint8Array): string {
	return createHash("sha256").update(content).digest("hex");
}
