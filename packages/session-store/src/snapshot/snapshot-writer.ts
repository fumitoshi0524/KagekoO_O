import { mkdir, open, unlink } from "node:fs/promises";
import { randomUUID } from "node:crypto";
import path from "node:path";
import type { Snapshot } from "./snapshot.js";
import { replaceAtomically } from "../atomic-replace.js";

export class SnapshotWriter {
	constructor(
		readonly filePath: string,
		readonly sessionId: string,
	) {}
	async write(snapshot: Snapshot): Promise<void> {
		if (snapshot.sessionId !== this.sessionId) throw new Error("Snapshot session mismatch");
		if (!Number.isSafeInteger(snapshot.schemaVersion) || snapshot.schemaVersion < 1)
			throw new Error("Invalid snapshot schema version");
		if (!Number.isInteger(snapshot.sequence) || snapshot.sequence < 0) throw new Error("Invalid snapshot sequence");
		await mkdir(path.dirname(this.filePath), { recursive: true, mode: 0o700 });
		const temporary = `${this.filePath}.${process.pid}.${randomUUID()}.tmp`;
		let handle: Awaited<ReturnType<typeof open>> | undefined;
		try {
			handle = await open(temporary, "wx", 0o600);
			await handle.writeFile(`${JSON.stringify(snapshot, null, 2)}\n`, "utf8");
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
}
