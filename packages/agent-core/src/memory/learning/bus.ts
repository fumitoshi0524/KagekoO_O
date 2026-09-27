import * as fs from "node:fs/promises";
import * as path from "node:path";
import { tryJsonStringify } from "../utils.js";
import { redactLearningEvent } from "./triage.js";
import type { LearningEvent } from "./event.js";

export interface LearningBusOptions {
	/** Durable learning directory, injected by the composition root. */
	learningDir: string;
	queuePath?: string;
	maxQueueSize?: number;
	maxQueueBytes?: number;
	maxPersistedBytes?: number;
	flushIntervalMs?: number;
	onDiagnostic?: (message: string, error?: unknown) => void | Promise<void>;
}

export type LearningBusSubscriber = (events: LearningEvent[]) => void | Promise<void>;

/**
 * In-memory queue + durable buffer for learning events.
 *
 * Events are queued in memory and persisted to disk on flush (session close
 * or queue size threshold). Pending persisted events can be replayed on the
 * next session start so nothing is lost if the process exits unexpectedly.
 */
export class LearningBus {
	readonly learningDir: string;
	readonly queuePath: string;
	readonly maxQueueSize: number;
	readonly maxQueueBytes: number;
	readonly maxPersistedBytes: number;
	readonly flushIntervalMs: number;
	private _queue: LearningEvent[] = [];
	private _subscribers: LearningBusSubscriber[] = [];
	private _flushTimer: ReturnType<typeof setTimeout> | null = null;
	private _flushPromise: Promise<void> | null = null;
	private _closed = false;
	private _closing = false;
	/** Serialize load/flush to prevent torn reads/writes. */
	private _ioLock: Promise<unknown> = Promise.resolve();
	private readonly onDiagnostic?: (message: string, error?: unknown) => void | Promise<void>;

	constructor(options: LearningBusOptions) {
		this.learningDir = options.learningDir;
		this.queuePath = options.queuePath ?? path.join(this.learningDir, "queue.jsonl");
		this.maxQueueSize = options.maxQueueSize ?? 100;
		this.maxQueueBytes = options.maxQueueBytes ?? 4 * 1024 * 1024;
		this.maxPersistedBytes = options.maxPersistedBytes ?? 16 * 1024 * 1024;
		this.flushIntervalMs = clampFlushIntervalMs(options.flushIntervalMs);
		this.onDiagnostic = options.onDiagnostic;
	}

	async load(): Promise<void> {
		return this._runLocked(async () => {
			await fs.mkdir(this.learningDir, { recursive: true });
			let lines: string[];
			try {
				lines = await readLines(this.queuePath, this.maxPersistedBytes);
			} catch (err) {
				this.reportDiagnostic(`Learning queue ${this.queuePath} is oversized or unreadable; discarding it.`, err);
				await fs.writeFile(this.queuePath, "", "utf-8").catch(() => {});
				lines = [];
			}
			for (const line of lines) {
				try {
					const event = JSON.parse(line) as LearningEvent;
					if (!event || !event.id) continue;
					// A queue.jsonl written before enqueue-time redaction existed
					// may hold raw secrets; redact on replay so the next flush
					// never re-persists them verbatim.
					let safeEvent: LearningEvent;
					try {
						safeEvent = redactLearningEvent(event);
					} catch (err) {
						this.reportDiagnostic(
							`Learning bus dropped replayed event ${event.id}: payload could not be redacted.`,
							err,
						);
						continue;
					}
					this._queue.push(safeEvent);
				} catch {
					// Ignore corrupt lines.
				}
			}
			// Leave queue.jsonl intact: events stay durable until a flush succeeds.
		});
	}

	enqueue(event: LearningEvent): boolean {
		if (this._closed || this._closing) {
			this.reportDiagnostic(`Learning bus dropped event ${event?.id ?? "unknown"}: enqueue after close.`);
			return false;
		}
		// Redact BEFORE the event can be persisted: queue.jsonl is written on
		// flush, so secrets must never enter the queue in raw form. The
		// processor redacts again as defense in depth.
		let safeEvent: LearningEvent;
		try {
			safeEvent = redactLearningEvent(event);
		} catch (err) {
			this.reportDiagnostic(
				`Learning bus dropped event ${event?.id ?? "unknown"}: payload could not be redacted.`,
				err,
			);
			return false;
		}
		this._queue.push(safeEvent);
		this._enforceQueueCap();
		if (this._queue.length >= this.maxQueueSize) {
			this.flush().catch((err) => this.reportDiagnostic("Learning bus flush failed.", err));
		} else {
			this._armFlushTimer();
		}
		return true;
	}

	private _enforceQueueCap(): void {
		let bytes = 0;
		let i = 0;
		while (i < this._queue.length) {
			const serialized = tryJsonStringify(this._queue[i]);
			if (!serialized.ok) {
				this.reportDiagnostic(`Learning bus dropped unserializable event ${this._queue[i]?.id ?? "unknown"}.`);
				this._queue.splice(i, 1);
				continue;
			}
			bytes += Buffer.byteLength(serialized.text, "utf-8");
			i++;
		}
		let evicted = 0;
		while (this._queue.length > 0 && (this._queue.length > this.maxQueueSize || bytes > this.maxQueueBytes)) {
			const removed = this._queue.shift();
			const serialized = tryJsonStringify(removed);
			if (serialized.ok) {
				bytes -= Buffer.byteLength(serialized.text, "utf-8");
			}
			evicted++;
		}
		if (evicted > 0) {
			this.reportDiagnostic(
				`Learning bus evicted ${evicted} oldest event(s) to enforce the queue cap; they were never persisted and are lost.`,
			);
		}
	}

	subscribe(fn: LearningBusSubscriber): () => void {
		this._subscribers.push(fn);
		return () => {
			const idx = this._subscribers.indexOf(fn);
			if (idx >= 0) this._subscribers.splice(idx, 1);
		};
	}

	async flush(): Promise<void> {
		if (this._closed) return;
		if (this._flushPromise) return this._flushPromise;
		this._flushPromise = this._flush();
		try {
			await this._flushPromise;
		} finally {
			this._flushPromise = null;
		}
	}

	private async _flush(): Promise<void> {
		return this._runLocked(async () => {
			this._clearFlushTimer();
			if (this._queue.length === 0) return;

			const batch = this._queue.slice(0);
			const lines: string[] = [];
			for (const event of batch) {
				const serialized = tryJsonStringify(event);
				if (!serialized.ok) {
					this.reportDiagnostic(`Learning bus skipped unserializable event ${event?.id ?? "unknown"}.`);
					continue;
				}
				lines.push(serialized.text);
			}

			await fs.mkdir(this.learningDir, { recursive: true });
			if (lines.length > 0) {
				const chunk = lines.join("\n") + "\n";
				// Atomic overwrite: readers always see a complete pending batch.
				const tmpPath = `${this.queuePath}.tmp`;
				try {
					await fs.writeFile(tmpPath, chunk, "utf-8");
					await fs.rename(tmpPath, this.queuePath);
				} catch (err) {
					await fs.unlink(tmpPath).catch(() => {});
					throw err;
				}
				await this._enforcePersistedCap();
			}

			for (const fn of this._subscribers) {
				try {
					await fn(batch);
				} catch (err) {
					// Subscribers must not crash the bus. Delivery acknowledges the
					// batch: a failing subscriber gets a diagnostic, but the batch is
					// NOT retained for replay — replay would silently re-apply
					// already-processed events to non-idempotent consumers.
					this.reportDiagnostic("Learning bus subscriber failed; batch will not be replayed.", err);
				}
			}

			// Clear the durable file BEFORE splicing the in-memory queue. A crash
			// between the two leaves an empty file and a dead process: nothing is
			// re-delivered. Events the subscribers never saw stay durable only
			// when the persist step above throws.
			await fs.writeFile(this.queuePath, "", "utf-8");
			this._queue.splice(0, batch.length);
		});
	}

	async close(): Promise<void> {
		if (this._closed || this._closing) return;
		this._closing = true;
		this._clearFlushTimer();
		// Bounded retries: a persist failure must not hang session close. Any
		// events still queued afterwards stay durable in queue.jsonl for replay.
		let attempts = 0;
		while (this._queue.length > 0 && attempts < MAX_CLOSE_FLUSH_ATTEMPTS) {
			attempts++;
			try {
				await this.flush();
			} catch (err) {
				this.reportDiagnostic("Learning bus flush during close failed.", err);
			}
		}
		if (this._queue.length > 0) {
			// flush() may have failed before OR after the persist step; check the
			// file instead of claiming the events are durable either way.
			let persistedBytes = 0;
			try {
				persistedBytes = (await fs.stat(this.queuePath)).size;
			} catch {
				// No queue file: nothing was persisted.
			}
			this.reportDiagnostic(
				persistedBytes > 0
					? `Learning bus closed with ${this._queue.length} undelivered event(s); they remain durable at ${this.queuePath}.`
					: `Learning bus closed with ${this._queue.length} undelivered event(s); they were never persisted and are lost.`,
			);
		}
		this._closed = true;
	}

	clearPersisted(): Promise<void> {
		return fs.unlink(this.queuePath).catch(() => {
			// Ignore if file does not exist.
		});
	}

	get queuedCount(): number {
		return this._queue.length;
	}

	private async _enforcePersistedCap(): Promise<void> {
		let stat;
		try {
			stat = await fs.stat(this.queuePath);
		} catch {
			return;
		}
		if (stat.size <= this.maxPersistedBytes) return;
		this.reportDiagnostic(
			`Learning queue ${this.queuePath} exceeds ${this.maxPersistedBytes} bytes and was truncated.`,
		);
		// Reading a multi-hundred-megabyte queue to trim gracefully risks OOM.
		// Reset to an empty file; subscribers that failed will lose replay data,
		// but the agent can continue.
		await fs.writeFile(this.queuePath, "", "utf-8");
	}

	private _armFlushTimer(): void {
		if (this._flushTimer || this.flushIntervalMs <= 0) return;
		this._flushTimer = setTimeout(() => {
			this._flushTimer = null;
			this.flush().catch((err) => this.reportDiagnostic("Learning bus flush failed.", err));
		}, this.flushIntervalMs);
		if (typeof this._flushTimer.unref === "function") this._flushTimer.unref();
	}

	private _clearFlushTimer(): void {
		if (this._flushTimer) {
			clearTimeout(this._flushTimer);
			this._flushTimer = null;
		}
	}

	private reportDiagnostic(message: string, error?: unknown): void {
		try {
			void Promise.resolve(this.onDiagnostic?.(message, error)).catch(() => {});
		} catch {
			/* diagnostics are non-fatal */
		}
	}

	private _runLocked<T>(fn: () => Promise<T>): Promise<T> {
		const result = this._ioLock.then(() => fn());
		this._ioLock = result.catch(() => {});
		return result;
	}
}

const MAX_SAFE_TIMEOUT_MS = 2 ** 31 - 1;
const MAX_CLOSE_FLUSH_ATTEMPTS = 2;

function clampFlushIntervalMs(value: unknown): number {
	const n = Number(value);
	if (!Number.isFinite(n)) {
		return 0;
	}
	const clamped = Math.max(0, Math.min(n, MAX_SAFE_TIMEOUT_MS));
	return Number.isInteger(clamped) ? clamped : Math.floor(clamped);
}

async function readLines(filePath: string, maxBytes: number): Promise<string[]> {
	let stat;
	try {
		stat = await fs.stat(filePath);
	} catch (err) {
		if ((err as NodeJS.ErrnoException).code === "ENOENT") return [];
		throw err;
	}
	if (stat.size > maxBytes) {
		throw new Error(`queue file is ${stat.size} bytes, exceeding ${maxBytes} byte limit`);
	}
	const text = await fs.readFile(filePath, "utf-8");
	return text.split("\n").filter((l) => l.trim());
}
