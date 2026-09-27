import * as path from "node:path";
import type { FileToolAccess, ToolAccess } from "../tools/types.js";

/**
 * Stateful execution scheduler for tool calls in one model step.
 *
 * - tasks with non-conflicting resource accesses may overlap
 * - tasks with conflicting resource accesses wait for the conflicting active tasks
 * - drained results are handed back in provider order
 */

export interface ToolCallTask<Result> {
	accesses: ToolAccesses;
	start: () => Promise<{ readonly result: Promise<Result> }>;
}

interface ControlledPromise<Result> {
	promise: Promise<Result>;
	resolve: (value: Result) => void;
	reject: (reason?: unknown) => void;
}

type ScheduledToolCallTask<Result = unknown> = ToolCallTask<Result> & {
	readonly result: ControlledPromise<Result>;
};

function createControlledPromise<Result>(): ControlledPromise<Result> {
	let resolve!: (value: Result) => void;
	let reject!: (reason?: unknown) => void;
	const promise = new Promise<Result>((res, rej) => {
		resolve = res;
		reject = rej;
	});
	return { promise, resolve, reject };
}

export const DEFAULT_TOOL_CONCURRENCY = 8;

function clampMaxConcurrency(value: number): number {
	const n = Number(value);
	if (!Number.isFinite(n) || n < 1) {
		throw new TypeError("maxConcurrency must be a finite positive number");
	}
	return Math.floor(n);
}

export interface ToolSchedulerOptions {
	maxConcurrency?: number;
}

export class ToolScheduler<Result = unknown> {
	readonly maxConcurrency: number;
	private activeTasks: Array<ScheduledToolCallTask<Result>> = [];
	private queuedTasks: Array<ScheduledToolCallTask<Result>> = [];
	private finished: Set<ScheduledToolCallTask<Result>> = new Set();

	constructor({ maxConcurrency = DEFAULT_TOOL_CONCURRENCY }: ToolSchedulerOptions = {}) {
		this.maxConcurrency = clampMaxConcurrency(maxConcurrency);
	}

	add(task: ToolCallTask<Result>): Promise<Result> {
		const result = createControlledPromise<Result>();
		// Prevent unhandled rejection if the caller never awaits the result.
		result.promise.catch(() => undefined);

		const scheduledTask: ScheduledToolCallTask<Result> = { ...task, result };
		if (this.isBlocked(scheduledTask, this.queuedTasks)) {
			this.queuedTasks.push(scheduledTask);
		} else {
			this.start(scheduledTask);
		}

		return result.promise;
	}

	private isBlocked(task: ScheduledToolCallTask<Result>, queuedBefore: Array<ScheduledToolCallTask<Result>>): boolean {
		return this.conflictsWithAny(task, this.activeTasks) || this.conflictsWithAny(task, queuedBefore);
	}

	private conflictsWithAny(
		task: ScheduledToolCallTask<Result>,
		candidates: Array<ScheduledToolCallTask<Result>>,
	): boolean {
		return candidates.some((candidate) => ToolAccesses.conflict(task.accesses, candidate.accesses));
	}

	private start(task: ScheduledToolCallTask<Result>): void {
		if (this.activeTasks.length >= this.maxConcurrency) {
			this.queuedTasks.push(task);
			return;
		}
		this.activeTasks.push(task);
		let started: Promise<{ readonly result: Promise<Result> }>;
		try {
			started = task.start();
		} catch (error) {
			task.result.reject(error);
			this.finish(task);
			return;
		}

		void started
			.then(({ result }) => result)
			.then(task.result.resolve, task.result.reject)
			.finally(() => {
				this.finish(task);
			});
	}

	private finish(task: ScheduledToolCallTask<Result>): void {
		if (this.finished.has(task)) {
			return;
		}
		this.finished.add(task);
		const index = this.activeTasks.indexOf(task);
		if (index >= 0) this.activeTasks.splice(index, 1);
		this.startQueuedTasks();
	}

	private startQueuedTasks(): void {
		const stillQueued: Array<ScheduledToolCallTask<Result>> = [];
		for (const task of this.queuedTasks) {
			if (this.activeTasks.length >= this.maxConcurrency || this.isBlocked(task, stillQueued)) {
				stillQueued.push(task);
			} else {
				this.start(task);
			}
		}
		this.queuedTasks = stillQueued;
	}
}

/** Sequential adapter retained for callers that explicitly require ordering. */
export class SerialToolScheduler {
	private tail: Promise<void> = Promise.resolve();
	schedule<T>(task: () => Promise<T>): Promise<T> {
		const run = this.tail.then(task, task);
		this.tail = run.then(
			() => undefined,
			() => undefined,
		);
		return run;
	}
}

export type ToolAccesses = ReadonlyArray<ToolAccess>;
type ToolFileOperation = NonNullable<FileToolAccess["operation"]>;

export const ToolAccesses = {
	none(): ToolAccesses {
		return [];
	},

	all(): ToolAccesses {
		return [{ kind: "all" }];
	},

	file(operation: ToolFileOperation, path: string, options: { recursive?: boolean } = {}): ToolAccesses {
		return [{ kind: "file", operation, path, recursive: options.recursive }];
	},

	readFile(path: string): ToolAccesses {
		return ToolAccesses.file("read", path);
	},

	readTree(path: string): ToolAccesses {
		return ToolAccesses.file("read", path, { recursive: true });
	},

	writeFile(path: string): ToolAccesses {
		return ToolAccesses.file("write", path);
	},

	writeTree(path: string): ToolAccesses {
		return ToolAccesses.file("write", path, { recursive: true });
	},

	readWriteFile(path: string): ToolAccesses {
		return ToolAccesses.file("readwrite", path);
	},

	readWriteTree(path: string): ToolAccesses {
		return ToolAccesses.file("readwrite", path, { recursive: true });
	},

	searchTree(path: string): ToolAccesses {
		return ToolAccesses.file("search", path, { recursive: true });
	},

	conflict(left: ToolAccesses, right: ToolAccesses): boolean {
		return left.some((leftAccess) => right.some((rightAccess) => resourceAccessesConflict(leftAccess, rightAccess)));
	},
} as const;

function resourceAccessesConflict(left: ToolAccess, right: ToolAccess): boolean {
	if (left.kind === "none" || right.kind === "none") return false;
	if (left.kind === "all" || right.kind === "all") return true;
	if (left.kind === "file" && right.kind === "file") {
		if (!fileOperationsConflict(left.operation, right.operation)) return false;
		return fileAccessesOverlap(left, right);
	}
	if (left.kind !== right.kind) return false;
	if (left.kind === "network" && right.kind === "network") return false;
	if ("target" in left && "target" in right && left.target !== right.target) return false;
	return capabilityOperationWrites(left.operation) || capabilityOperationWrites(right.operation);
}

function fileOperationsConflict(left: FileToolAccess["operation"], right: FileToolAccess["operation"]): boolean {
	return fileOperationWrites(left) || fileOperationWrites(right);
}

function fileOperationWrites(operation: FileToolAccess["operation"]): boolean {
	switch (operation) {
		case "read":
		case "search":
			return false;
		case "write":
		case "readwrite":
			return true;
		case undefined:
			// A file access without an operation is not safe to run concurrently.
			return true;
	}
}

function capabilityOperationWrites(operation: string | undefined): boolean {
	return operation !== "read" && operation !== "use";
}

function fileAccessesOverlap(left: FileToolAccess, right: FileToolAccess): boolean {
	if (!left.path || !right.path) return true;
	const leftPath = normalizePath(left.path);
	const rightPath = normalizePath(right.path);
	if (leftPath === rightPath) return true;

	const leftPrefix = leftPath.endsWith("/") ? leftPath : `${leftPath}/`;
	const rightPrefix = rightPath.endsWith("/") ? rightPath : `${rightPath}/`;
	return (
		(left.recursive === true && rightPath.startsWith(leftPrefix)) ||
		(right.recursive === true && leftPath.startsWith(rightPrefix))
	);
}

function normalizePath(inputPath: string): string {
	let normalized = inputPath.replaceAll("\\", "/").replaceAll(/\/+/g, "/");
	normalized = path.normalize(normalized).replaceAll("\\", "/");
	const shouldFoldCase = process.platform === "win32" || process.platform === "darwin";
	const folded = shouldFoldCase ? normalized.toLowerCase() : normalized;
	if (folded.length > 1 && folded.endsWith("/")) {
		return folded.slice(0, -1);
	}
	return folded;
}
