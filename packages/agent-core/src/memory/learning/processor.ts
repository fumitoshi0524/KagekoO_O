import * as fs from "node:fs/promises";
import * as path from "node:path";
import { readJsonlLines, tryJsonStringify } from "../utils.js";
import type { LearningBus } from "./bus.js";
import type { LearningTriage } from "./triage.js";
import { redactLearningEvent } from "./triage.js";
import type { Learner, PendingEntry, ResolvePendingResult } from "./types.js";
import type { LearningEvent } from "./event.js";
import type { TriageDecision } from "./types.js";

export interface LearningOutputInfo {
	/** True when this report follows a newly written pending-queue entry. */
	stashed?: boolean;
}

export interface LearningProcessorOptions {
	bus: LearningBus;
	triage: LearningTriage;
	/** Directory holding the pending queue, injected by the composition root. */
	pendingDir: string;
	pendingPath?: string;
	maxPendingEntries?: number;
	onDiagnostic?: (message: string, error?: unknown) => void | Promise<void>;
	onDecision?: (decision: TriageDecision, event: LearningEvent) => void;
	onOutput?: (
		decision: TriageDecision,
		event: LearningEvent,
		output: unknown,
		info?: LearningOutputInfo,
	) => void | Promise<void>;
}

/**
 * Consumes flushed learning events, runs triage, and dispatches to learners.
 *
 * Pending outputs (skills, conventions, etc.) are stored in a pending queue
 * for user approval before they become permanent.
 */
export class LearningProcessor {
	readonly bus: LearningBus;
	readonly triage: LearningTriage;
	readonly learners: Map<string, Learner> = new Map();
	readonly pendingDir: string;
	readonly pendingPath: string;
	readonly maxPendingEntries: number;
	private _unsubscribe: (() => void) | null = null;
	private _running = false;
	private _inFlight = new Set<Promise<void>>();
	private _pendingIds: Set<string> | null = null;
	/** Serialize all pending-file mutations. */
	private _lock: Promise<unknown> = Promise.resolve();
	private readonly onDiagnostic?: (message: string, error?: unknown) => void | Promise<void>;
	private readonly onDecision?: (decision: TriageDecision, event: LearningEvent) => void;
	private readonly onOutput?: (
		decision: TriageDecision,
		event: LearningEvent,
		output: unknown,
		info?: LearningOutputInfo,
	) => void | Promise<void>;

	constructor(options: LearningProcessorOptions) {
		this.bus = options.bus;
		this.triage = options.triage;
		this.pendingDir = options.pendingDir;
		this.pendingPath = options.pendingPath ?? path.join(this.pendingDir, "pending.jsonl");
		this.maxPendingEntries = options.maxPendingEntries ?? 100;
		this.onDiagnostic = options.onDiagnostic;
		this.onDecision = options.onDecision;
		this.onOutput = options.onOutput;
	}

	private _runLocked<T>(fn: () => Promise<T>): Promise<T> {
		const result = this._lock.then(() => fn());
		this._lock = result.catch(() => {});
		return result;
	}

	registerLearner(target: string, learner: Learner): void {
		this.learners.set(target, learner);
	}

	start(): void {
		if (this._running) return;
		this._running = true;
		this._unsubscribe = this.bus.subscribe((events) => {
			const promise = this._processBatch(events);
			this._inFlight.add(promise);
			// `promise.finally(cb)` would create a discarded derived promise that
			// rejects when `promise` rejects — a latent unhandled rejection.
			// then(cleanup, cleanup) settles successfully in both cases.
			const cleanup = () => {
				this._inFlight.delete(promise);
			};
			promise.then(cleanup, cleanup);
			return promise;
		});
	}

	async stop(): Promise<void> {
		this._running = false;
		if (this._unsubscribe) {
			this._unsubscribe();
			this._unsubscribe = null;
		}
		await this._drainInFlight();
	}

	private async _drainInFlight(): Promise<void> {
		if (this._inFlight.size === 0) return;
		await Promise.allSettled([...this._inFlight]);
	}

	private async _processBatch(events: PendingEntry["event"][]): Promise<void> {
		for (const rawEvent of events) {
			try {
				// Redact secrets ONCE here, before triage and learner dispatch, so
				// raw credentials in tool output never reach knowledge.jsonl or
				// the pending queue. Inside the try: a poisoned payload must not
				// kill the rest of the batch. (The bus already redacts at enqueue
				// time so secrets never hit queue.jsonl; this is defense in depth
				// for events delivered by other paths.)
				const event = redactLearningEvent(rawEvent);
				const decision = await this.triage.triage(event);
				this.onDecision?.(decision, event);
				if (decision.action === "drop") continue;

				const learner = decision.target ? this.learners.get(decision.target) : undefined;
				if (!learner) {
					if (decision.action === "pending") {
						await this._stashPending({ event, decision, output: undefined });
					} else {
						this.reportDiagnostic(
							`Learning processor dropped event ${event.id}: no learner registered for target "${decision.target ?? "none"}".`,
						);
					}
					continue;
				}

				const output = await learner.handle(event, decision);
				if (!output) continue;

				await this._handleLearnerOutput(event, decision, output);
			} catch (err) {
				// A single event must not crash the processor.
				this.reportDiagnostic("Learning processor event failed.", err);
			}
		}
	}

	/**
	 * Submission entry point for the resident learner agent: stash a proposal in
	 * the pending queue exactly like the pending branch of `_processBatch`.
	 *
	 * Falsy output and auto-approved output are never stashed (auto-approved
	 * output was already written and hot-loaded by the sink), but any truthy
	 * output still fires `onOutput` — the composition root's reload hook depends
	 * on it.
	 */
	async submitAgentProposal(
		target: string,
		event: LearningEvent,
		output: unknown,
	): Promise<{ stashed: boolean; reason?: string }> {
		if (!output) return { stashed: false, reason: "empty output" };
		const decision: TriageDecision = { action: "pending", target, reason: "learner-agent proposal" };
		// Redact here, mirroring where _processBatch redacts, so agent-submitted
		// events cannot carry raw credentials into pending.jsonl. Redaction is
		// idempotent, so an event already redacted by the batch path is simply
		// redacted again; applying it defensively on both paths keeps each entry
		// point safe on its own.
		return this._handleLearnerOutput(redactLearningEvent(event), decision, output);
	}

	private async _handleLearnerOutput(
		event: LearningEvent,
		decision: TriageDecision,
		output: unknown,
	): Promise<{ stashed: boolean; reason?: string }> {
		// Auto-approved outputs were already written and hot-loaded by the
		// learner; stashing them would double-fire on a later approve.
		const eligible = decision.action === "pending" && !isApprovedOutput(output);
		if (!eligible) {
			await this.reportOutput(decision, event, output, { stashed: false });
			return { stashed: false, reason: decision.action === "pending" ? "already approved" : "not pending" };
		}
		const stash = await this._stashPending({ event, decision, output });
		await this.reportOutput(decision, event, output, { stashed: stash.wrote });
		return stash.wrote ? { stashed: true } : { stashed: false, reason: stash.reason };
	}

	private async _stashPending(entry: PendingEntry): Promise<{ wrote: boolean; reason?: string }> {
		return this._runLocked(async () => {
			await fs.mkdir(this.pendingDir, { recursive: true });
			await this._loadPendingIds();
			if (this._pendingIds!.has(entry.event.id)) {
				return { wrote: false, reason: "duplicate" };
			}
			this._pendingIds!.add(entry.event.id);
			const serialized = this.serializePendingEntry(entry);
			if (!serialized) return { wrote: false, reason: "unserializable" };
			let existing = "";
			try {
				existing = await fs.readFile(this.pendingPath, "utf-8");
			} catch (err) {
				if ((err as NodeJS.ErrnoException).code !== "ENOENT") throw err;
			}
			await writeFileAtomic(this.pendingPath, `${existing}${serialized}\n`);

			if (this.maxPendingEntries > 0 && this._pendingIds!.size > this.maxPendingEntries) {
				await this._prunePendingLocked();
			}
			return { wrote: true };
		});
	}

	private async _loadPendingIds(): Promise<void> {
		if (this._pendingIds) return;
		this._pendingIds = new Set();
		const pending = await this.listPending();
		for (const entry of pending) {
			if (entry?.event?.id) this._pendingIds.add(entry.event.id);
		}
	}

	private async _prunePending(): Promise<void> {
		return this._runLocked(() => this._prunePendingLocked());
	}

	private async _prunePendingLocked(): Promise<void> {
		let pending = await this.listPending();
		const overflow = pending.length - this.maxPendingEntries;
		if (overflow > 0) {
			pending = pending.slice(overflow);
			const lines =
				pending
					.map((e) => this.serializePendingEntry(e))
					.filter((l): l is string => l !== undefined)
					.join("\n") + (pending.length ? "\n" : "");
			await writeFileAtomic(this.pendingPath, lines);
		}
		this._pendingIds = new Set(pending.map((p) => p.event?.id).filter((id): id is string => Boolean(id)));
	}

	async listPending(): Promise<PendingEntry[]> {
		try {
			return await readJsonlLines<PendingEntry>(this.pendingPath, {
				onSkippedLines: (skipped, filePath) =>
					this.reportDiagnostic(`Learning pending queue skipped ${skipped} unreadable line(s) in ${filePath}.`),
			});
		} catch (err) {
			if ((err as NodeJS.ErrnoException).code === "ENOENT") return [];
			// A corrupt or locked queue must surface as a diagnostic instead of
			// reading as a silent "0 pending".
			this.reportDiagnostic(`Learning pending queue is unreadable: ${this.pendingPath}.`, err);
			return [];
		}
	}

	async clearPending(): Promise<void> {
		return this._runLocked(async () => {
			await fs.unlink(this.pendingPath).catch(() => {
				// Ignore if file does not exist.
			});
			this._pendingIds = new Set();
		});
	}

	async approvePending(eventId: string): Promise<ResolvePendingResult> {
		return this._resolvePending(eventId, "approve");
	}

	async rejectPending(eventId: string): Promise<ResolvePendingResult> {
		return this._resolvePending(eventId, "reject");
	}

	private async _resolvePending(eventId: string, action: "approve" | "reject"): Promise<ResolvePendingResult> {
		return this._runLocked(async () => {
			const pending = await this.listPending();
			const idx = pending.findIndex((entry) => entry.event.id === eventId);
			if (idx === -1) {
				return { resolved: false, reason: "pending entry not found" };
			}

			const entry = pending[idx] as PendingEntry;
			let approvalResult: Record<string, unknown> | undefined;
			if (action === "approve") {
				const learner = entry.decision.target ? this.learners.get(entry.decision.target) : undefined;
				if (!learner || typeof learner.approve !== "function") {
					return { resolved: false, reason: "target does not support approval" };
				}
				approvalResult = (await learner.approve(entry.output)) as Record<string, unknown> | undefined;
				await this.reportOutput(entry.decision, entry.event, {
					...approvalResult,
					status: "approved",
				});
			} else {
				// Let the learner release any suppression state (e.g. seen
				// fingerprints) so an identical future proposal is not
				// permanently suppressed by a rejected one.
				const learner = entry.decision.target ? this.learners.get(entry.decision.target) : undefined;
				learner?.reject?.(entry.output);
			}

			pending.splice(idx, 1);
			this._pendingIds?.delete(eventId);
			const lines =
				pending
					.map((e) => this.serializePendingEntry(e))
					.filter((l): l is string => l !== undefined)
					.join("\n") + (pending.length ? "\n" : "");
			await writeFileAtomic(this.pendingPath, lines);
			return { resolved: true, action, target: entry.decision.target, ...approvalResult };
		});
	}

	async flush(): Promise<void> {
		await this._drainInFlight();
		for (const learner of this.learners.values()) {
			if (typeof learner.flush === "function") {
				try {
					await learner.flush();
				} catch {
					// Learner flush failures must not crash the processor.
				}
			}
		}
	}

	private serializePendingEntry(entry: PendingEntry): string | undefined {
		const serialized = tryJsonStringify(entry);
		if (!serialized.ok) {
			this.reportDiagnostic(
				`Learning processor skipped unserializable pending entry ${entry?.event?.id ?? "unknown"}.`,
			);
			return undefined;
		}
		return serialized.text;
	}

	private reportDiagnostic(message: string, error?: unknown): void {
		try {
			void Promise.resolve(this.onDiagnostic?.(message, error)).catch(() => {});
		} catch {
			/* diagnostics are non-fatal */
		}
	}

	/**
	 * Fire the output hook without letting a throwing hook corrupt the pending
	 * queue state: on the stash path the entry is already written, and on the
	 * approve path the learner already persisted and hot-loaded. A hook failure
	 * (e.g. the composition root's capability reload) degrades to a diagnostic
	 * instead of propagating out of an otherwise-successful mutation.
	 */
	private async reportOutput(
		decision: TriageDecision,
		event: LearningEvent,
		output: unknown,
		info?: LearningOutputInfo,
	): Promise<void> {
		try {
			await this.onOutput?.(decision, event, output, info);
		} catch (err) {
			this.reportDiagnostic("Learning processor onOutput hook failed.", err);
		}
	}
}

function isApprovedOutput(output: unknown): boolean {
	return typeof output === "object" && output !== null && (output as { status?: unknown }).status === "approved";
}

async function writeFileAtomic(filePath: string, data: string): Promise<void> {
	const tmpPath = `${filePath}.tmp`;
	try {
		await fs.writeFile(tmpPath, data, "utf-8");
		await fs.rename(tmpPath, filePath);
	} catch (err) {
		await fs.unlink(tmpPath).catch(() => {});
		throw err;
	}
}
