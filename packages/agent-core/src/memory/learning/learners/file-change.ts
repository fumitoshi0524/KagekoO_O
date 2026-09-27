import * as fs from "node:fs/promises";
import * as path from "node:path";
import type { RepoIndexer } from "../../repo-indexer.js";
import type { GraphBuilder } from "../../graph-builder.js";
import type { RepoIndexEntry } from "../../types.js";
import type { LearningEvent } from "../event.js";
import type { Learner } from "../types.js";

export interface FileChangeLearnerOptions {
	repoIndexer: RepoIndexer;
	graphBuilder?: GraphBuilder;
}

/**
 * Learns from file changes by incrementally re-indexing modified files.
 */
export class FileChangeLearner implements Learner {
	private readonly repoIndexer: RepoIndexer;
	private readonly graphBuilder?: GraphBuilder;
	/** Pending paths with their last seen operation; last write wins per path. */
	private _pendingPaths = new Map<string, string>();
	private _flushTimer: ReturnType<typeof setTimeout> | null = null;
	readonly debounceMs = 500;

	constructor({ repoIndexer, graphBuilder }: FileChangeLearnerOptions) {
		this.repoIndexer = repoIndexer;
		this.graphBuilder = graphBuilder;
	}

	handle(event: LearningEvent): { queued: boolean; path: string } | undefined {
		const { path: filePath, operation } = event.payload as { path?: string; operation?: string };
		if (!filePath) return undefined;
		this._pendingPaths.set(filePath, operation ?? "write");
		this._debouncedReindex();
		return { queued: true, path: filePath };
	}

	private _debouncedReindex(): void {
		if (this._flushTimer) return;
		this._flushTimer = setTimeout(() => {
			this._flushTimer = null;
			void this._reindex();
		}, this.debounceMs);
		if (typeof this._flushTimer.unref === "function") this._flushTimer.unref();
	}

	private async _reindex(): Promise<void> {
		const pending = [...this._pendingPaths.entries()];
		this._pendingPaths.clear();
		if (pending.length === 0) return;

		try {
			const paths = pending.map(([p]) => p);
			await this.repoIndexer.index({ summarize: false, paths });
			if (this.graphBuilder) {
				// Patch the graph with only the changed entries; rebuilding from
				// every indexed entry re-reads the whole repo per edit batch.
				const existing = await this.repoIndexer.loadExisting();
				const changed: RepoIndexEntry[] = [];
				const removed: string[] = [];
				for (const [p, operation] of pending) {
					const key = toEntryPath(p, this.repoIndexer.cwd);
					// A deleted file has no fresh entry; drop its graph node instead
					// of leaving it (and its edges) behind forever. Boundary note:
					// no production tool currently emits `operation: "delete"`
					// file-change events (bash-side deletes are unobservable), so
					// the disk-existence check is the only deletion detector.
					if (operation === "delete" || !(await fileExists(path.resolve(this.repoIndexer.cwd, p)))) {
						removed.push(key);
						continue;
					}
					const entry = existing.get(key);
					if (entry) changed.push(entry);
				}
				await this.graphBuilder.patch(changed, { removedPaths: removed });
			}
		} catch {
			// Best-effort incremental indexing; failures are not fatal.
		}
	}

	async flush(): Promise<void> {
		if (this._flushTimer) {
			clearTimeout(this._flushTimer);
			this._flushTimer = null;
		}
		await this._reindex();
	}
}

/** Map an event payload path (relative or absolute) to the index entry key. */
function toEntryPath(filePath: string, cwd: string): string {
	return path.relative(cwd, path.resolve(cwd, filePath)).replace(/\\/g, "/");
}

async function fileExists(absPath: string): Promise<boolean> {
	try {
		return (await fs.lstat(absPath)).isFile();
	} catch (err) {
		// Only a genuinely missing path means "deleted"; transient errors
		// (EPERM, Windows file locks) must leave the graph alone.
		const code = (err as NodeJS.ErrnoException).code;
		if (code === "ENOENT" || code === "ENOTDIR") return false;
		return true;
	}
}
