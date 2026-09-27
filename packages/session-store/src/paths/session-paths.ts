import path from "node:path";

export class SessionPaths {
	readonly directory: string;
	readonly metadata: string;
	readonly journal: string;
	readonly snapshot: string;
	readonly lease: string;
	readonly attachments: string;

	/** Root directory that stores every session of a workspace. */
	static sessionsRoot(cwd: string): string {
		return path.join(cwd, ".kageko", "sessions");
	}

	constructor(
		rootDir: string,
		readonly sessionId: string,
	) {
		if (!sessionId || sessionId.includes("..") || path.isAbsolute(sessionId) || /[\\/]/.test(sessionId)) {
			throw new Error("Invalid session id");
		}
		this.directory = path.join(path.resolve(rootDir), sessionId);
		this.metadata = path.join(this.directory, "metadata.json");
		this.journal = path.join(this.directory, "journal.jsonl");
		this.snapshot = path.join(this.directory, "snapshot.json");
		this.lease = path.join(this.directory, "lease");
		this.attachments = path.join(this.directory, "attachments");
	}
}
