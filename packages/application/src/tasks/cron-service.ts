import { Cron } from "croner";
import * as crypto from "node:crypto";

const MAX_USER_PROMPT_JOBS = 50;
const STALE_DAYS = 7;
const DAY_MS = 1000 * 60 * 60 * 24;
const MAX_CRON_EXPRESSION_LENGTH = 256;
const CRON_BASIC_RE = /^[\d\s*,/\-?LWC#A-Za-z]+$/;

export interface CronJobBase {
	id: string;
	cron: string;
	type: "internal" | "prompt";
	createdAt: number;
	recurring: boolean;
	stale: boolean;
	instance?: Cron;
}

export interface InternalCronJob extends CronJobBase {
	type: "internal";
	fn: () => void | Promise<void>;
}

export interface PromptCronJob extends CronJobBase {
	type: "prompt";
	prompt: string;
	isFiring: boolean;
	coalescedCount: number;
}

export type CronJob = InternalCronJob | PromptCronJob;

export interface CronFireInfo {
	coalescedCount: number;
	stale: boolean;
}

export interface CronDiagnostic {
	readonly message: string;
	readonly error?: unknown;
}
export type CronDiagnosticReporter = (diagnostic: CronDiagnostic) => void | Promise<void>;

export interface SerializedCronJob {
	id: string;
	cron: string;
	prompt: string;
	recurring: boolean;
	createdAt: number;
	stale: boolean;
}

export interface CronCreateOptions {
	id?: string;
	cron: string;
	prompt: string;
	recurring?: boolean;
	createdAt?: number;
}

export interface CronCreateResult {
	id: string;
	cron: string;
	humanSchedule: string;
	recurring: boolean;
	nextFireAt: string | null;
}

export interface CronListItem {
	id: string;
	cron: string;
	humanSchedule: string;
	prompt: string;
	nextFireAt: string | null;
	recurring: boolean;
	ageDays: number;
	stale: boolean;
}

export interface CronManagerOptions {
	onFire?: (job: PromptCronJob, info: CronFireInfo) => void | Promise<void>;
	onPersist?: (jobs: SerializedCronJob[]) => void | Promise<void>;
	onDiagnostic?: CronDiagnosticReporter;
}

/**
 * Cron scheduler that supports internal function jobs (e.g. auto-index) and
 * user-facing prompt jobs. Prompt jobs are capped, tracked, and drained by the
 * agent when it takes a user turn.
 */
export class CronManager {
	onFire?: (job: PromptCronJob, info: CronFireInfo) => void | Promise<void>;
	onPersist?: (jobs: SerializedCronJob[]) => void | Promise<void>;
	private readonly onDiagnostic?: CronDiagnosticReporter;
	readonly jobs = new Map<string, CronJob>();
	private _persistPromise: Promise<void> = Promise.resolve();
	private _persistPending = false;
	private restoring = false;
	private _fires = new Set<Promise<void>>();

	constructor({ onFire, onPersist, onDiagnostic }: CronManagerOptions = {}) {
		this.onFire = onFire;
		this.onPersist = onPersist;
		this.onDiagnostic = onDiagnostic;
	}

	/**
	 * Add an internal function-based job. Used by auto-index and similar
	 * background tasks. These jobs are not surfaced by `list()` and are not
	 * persisted.
	 */
	add(id: string, expression: string, fn: () => void | Promise<void>): InternalCronJob {
		validateCronExpression(expression);
		this.remove(id);
		const job: InternalCronJob = {
			id,
			cron: expression,
			fn,
			type: "internal",
			createdAt: Date.now(),
			recurring: true,
			stale: false,
		};
		job.instance = new Cron(expression, { protect: true, maxRuns: Infinity, unref: true }, () =>
			this._onInternalFire(job),
		);
		this.jobs.set(id, job);
		return job;
	}

	/**
	 * Create a user-facing prompt job. Throws if the active prompt job cap is
	 * exceeded or required fields are missing. Optionally accepts an `id` and
	 * `createdAt` to restore persisted jobs.
	 */
	create(
		{ id, cron, prompt, recurring = true, createdAt }: CronCreateOptions = { cron: "", prompt: "" },
	): CronCreateResult {
		if (this._activePromptCount() >= MAX_USER_PROMPT_JOBS) {
			throw new Error(`Maximum number of active cron prompt jobs (${MAX_USER_PROMPT_JOBS}) reached.`);
		}
		if (!cron || typeof prompt !== "string") {
			throw new Error("Both `cron` and `prompt` are required.");
		}
		validateCronExpression(cron);

		const jobId = id ?? crypto.randomBytes(4).toString("hex");
		const job: PromptCronJob = {
			id: jobId,
			cron,
			prompt,
			type: "prompt",
			createdAt: createdAt ?? Date.now(),
			recurring,
			stale: false,
			isFiring: false,
			coalescedCount: 0,
		};
		job.instance = new Cron(cron, { protect: false, maxRuns: recurring ? Infinity : 1, unref: true }, () =>
			this._onPromptFire(job),
		);
		this.jobs.set(jobId, job);
		this._persist();
		return this._toCreateResult(job);
	}

	/**
	 * Stop and delete a job by id. Returns true if a job was removed.
	 */
	remove(id: string): boolean {
		const job = this.jobs.get(id);
		if (!job) return false;
		job.instance?.stop();
		this.jobs.delete(id);
		this._persist();
		return true;
	}

	/**
	 * List user-facing prompt jobs.
	 */
	list(): CronListItem[] {
		const staleIds: string[] = [];
		for (const [id, job] of this.jobs) {
			if (job.type === "prompt" && job.recurring && this._ageDays(job) > STALE_DAYS) {
				job.instance?.stop();
				job.stale = true;
				staleIds.push(id);
			}
		}
		for (const id of staleIds) {
			this.jobs.delete(id);
		}
		this._persist();
		return Array.from(this.jobs.values())
			.filter((job): job is PromptCronJob => job.type === "prompt")
			.map((job) => this._toListItem(job));
	}

	/**
	 * Serialize user-facing prompt jobs for persistence.
	 */
	serialize(): SerializedCronJob[] {
		return Array.from(this.jobs.values())
			.filter((job): job is PromptCronJob => job.type === "prompt")
			.map((job) => ({
				id: job.id,
				cron: job.cron,
				prompt: truncateUtf8(job.prompt, 8192),
				recurring: job.recurring,
				createdAt: job.createdAt,
				stale: job.stale,
			}));
	}

	toJSON(): SerializedCronJob[] {
		return this.serialize();
	}

	/**
	 * Restore user-facing prompt jobs from a serialized array. Existing prompt
	 * jobs are removed first; internal jobs are left untouched.
	 */
	restore(serialized: unknown): void {
		if (!Array.isArray(serialized)) return;
		this.restoring = true;
		try {
			for (const [id, job] of this.jobs) {
				if (job.type === "prompt") {
					job.instance?.stop();
					this.jobs.delete(id);
				}
			}

			for (const item of serialized as Array<Partial<SerializedCronJob> | null>) {
				if (!item || typeof item !== "object") {
					this.reportDiagnostic({ message: "Cron restore skipped a non-object entry" });
					continue;
				}
				if (!item.cron || typeof item.prompt !== "string") {
					this.reportDiagnostic({ message: `Cron restore skipped invalid entry ${item.id ?? "unknown"}` });
					continue;
				}
				try {
					this.create({
						id: item.id,
						cron: item.cron,
						prompt: item.prompt,
						recurring: item.recurring ?? true,
						createdAt: item.createdAt,
					});
				} catch (err) {
					this.reportDiagnostic({ message: `Cron restore failed for job ${item.id ?? "unknown"}`, error: err });
				}
			}
		} finally {
			this.restoring = false;
		}
	}

	/**
	 * Stop all jobs and clear the registry.
	 */
	async stopAll(): Promise<void> {
		for (const job of this.jobs.values()) {
			job.instance?.stop();
		}
		await Promise.allSettled(this._fires);
		this._fires.clear();
		this.jobs.clear();
	}

	private _activePromptCount(): number {
		return Array.from(this.jobs.values()).filter((job) => job.type === "prompt" && !job.stale).length;
	}

	private _ageDays(job: CronJob): number {
		return Math.floor((Date.now() - job.createdAt) / DAY_MS);
	}

	private _trackFire(promise: Promise<void> | undefined): void {
		if (!promise) return;
		this._fires.add(promise);
		promise.then(
			() => this._fires.delete(promise),
			() => this._fires.delete(promise),
		);
	}

	private reportDiagnostic(diagnostic: CronDiagnostic): void {
		try {
			void Promise.resolve(this.onDiagnostic?.(diagnostic)).catch(() => {});
		} catch {
			/* diagnostics do not affect cron */
		}
	}

	private _onInternalFire(job: InternalCronJob): void {
		const promise = (async () => {
			if (job.recurring && this._ageDays(job) > STALE_DAYS) {
				job.instance?.stop();
				job.stale = true;
				return;
			}
			try {
				await job.fn?.();
			} catch {
				// Best-effort background task; failures are not fatal.
			}
		})();
		this._trackFire(promise);
	}

	private async _onPromptFire(job: PromptCronJob): Promise<void> {
		const promise = this._doPromptFire(job);
		this._trackFire(promise);
		return promise;
	}

	private async _doPromptFire(job: PromptCronJob): Promise<void> {
		if (job.isFiring) {
			job.coalescedCount += 1;
			return;
		}

		if (job.recurring && this._ageDays(job) > STALE_DAYS) {
			job.instance?.stop();
			job.stale = true;
			try {
				await this.onFire?.(job, { coalescedCount: Math.max(1, job.coalescedCount), stale: true });
			} catch {
				// Best-effort background task; failures are not fatal.
			}
			this.jobs.delete(job.id);
			this._persist();
			return;
		}

		job.isFiring = true;
		try {
			do {
				const coalescedCount = Math.max(1, job.coalescedCount);
				job.coalescedCount = 0;
				try {
					await this.onFire?.(job, { coalescedCount, stale: false });
				} catch {
					// Best-effort background task; failures are not fatal.
				}
			} while (job.coalescedCount > 0);
		} finally {
			job.isFiring = false;
		}

		if (!job.recurring) {
			this.remove(job.id);
		}
	}

	private _persist(): void {
		if (this.restoring) return;
		// Coalesce overlapping persist requests into a single in-flight loop to
		// avoid unbounded promise-chain growth when mutations happen rapidly.
		if (this._persistPending) return;
		this._persistPending = true;
		this._persistPromise = this._persistPromise.then(async () => {
			while (this._persistPending) {
				this._persistPending = false;
				try {
					await this.onPersist?.(this.serialize());
				} catch {
					// Persistence is best-effort.
				}
			}
		});
	}

	async flushPersist(): Promise<void> {
		await this._persistPromise;
	}

	private _toCreateResult(job: PromptCronJob): CronCreateResult {
		return {
			id: job.id,
			cron: job.cron,
			humanSchedule: job.cron,
			recurring: job.recurring,
			nextFireAt: job.instance?.nextRun()?.toISOString() ?? null,
		};
	}

	private _toListItem(job: PromptCronJob): CronListItem {
		return {
			id: job.id,
			cron: job.cron,
			humanSchedule: job.cron,
			prompt: truncateUtf8(job.prompt, 200),
			nextFireAt: job.instance?.nextRun()?.toISOString() ?? null,
			recurring: job.recurring,
			ageDays: this._ageDays(job),
			stale: job.stale,
		};
	}
}

function truncateUtf8(text: string, maxBytes: number): string {
	const buf = Buffer.from(text, "utf8");
	if (buf.length <= maxBytes) return text;
	return buf.toString("utf8", 0, maxBytes);
}

function validateCronExpression(expression: unknown): asserts expression is string {
	if (typeof expression !== "string" || expression.length === 0 || expression.length > MAX_CRON_EXPRESSION_LENGTH) {
		throw new Error("Invalid cron expression");
	}
	if (!CRON_BASIC_RE.test(expression)) {
		throw new Error("Invalid cron expression characters");
	}
	validateCronInterval(expression);
}

function validateCronInterval(expression: string): void {
	try {
		const cron = new Cron(expression);
		const next1 = cron.nextRun();
		const next2 = cron.nextRun(next1 ?? undefined);
		if (next1 && next2 && next2.getTime() - next1.getTime() < 1_000) {
			throw new Error("Cron interval must be at least 1 second");
		}
	} catch (err) {
		if ((err as Error).message.includes("interval")) throw err;
		throw new Error("Invalid cron expression");
	}
}

/** Partial fire metadata consumed by session steering. */
export type CronJobFireInfo = Partial<CronFireInfo>;
