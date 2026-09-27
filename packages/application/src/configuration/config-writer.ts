import * as fs from "node:fs/promises";
import * as path from "node:path";
import { randomUUID } from "node:crypto";
import { replaceAtomically } from "@kageko/session-store";

/** Atomic writer for application configuration documents. */
export class ConfigWriter {
	constructor(readonly filePath: string) {}

	async write(document: Record<string, unknown>): Promise<void> {
		await fs.mkdir(path.dirname(this.filePath), { recursive: true, mode: 0o700 });
		const temporaryPath = `${this.filePath}.${process.pid}.${randomUUID()}.tmp`;
		let handle: fs.FileHandle | undefined;
		try {
			handle = await fs.open(temporaryPath, "wx", 0o600);
			await handle.writeFile(`${JSON.stringify(document, null, 2)}\n`, "utf8");
			await handle.sync();
			await handle.close();
			handle = undefined;
			await replaceAtomically(temporaryPath, this.filePath);
			await fs.chmod(this.filePath, 0o600).catch(() => {});
		} catch (error) {
			await handle?.close().catch(() => {});
			await fs.unlink(temporaryPath).catch(() => {});
			throw error;
		}
	}
}
