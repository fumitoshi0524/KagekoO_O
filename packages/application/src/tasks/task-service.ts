import { CronManager, type CronDiagnosticReporter, type SerializedCronJob } from "./cron-service.js";
import * as crypto from "node:crypto";
import type { SessionProcessSupervisor } from "@kageko/process-supervisor";
import type { JournalPort } from "@kageko/agent-core";
import type { DurableEvent } from "@kageko/protocol";

export interface SessionCronOptions {
	readonly initialJobs?: readonly SerializedCronJob[];
	readonly persist?: (jobs: readonly SerializedCronJob[]) => Promise<void> | void;
}

export type TaskStatus = "queued" | "running" | "completed" | "failed" | "cancelled";
export interface TaskSummary {
	readonly sessionId: string;
	readonly taskId: string;
	readonly status: TaskStatus;
	readonly startedAt?: number;
	readonly endedAt?: number;
	readonly error?: string;
}
export class TaskService {
	private readonly tasks = new Map<string, TaskSummary>();
	private readonly cronBySession = new Map<string, CronManager>();
	private readonly childCrons = new Set<CronManager>();
	constructor(private readonly reportCronDiagnostic?: CronDiagnosticReporter) {}
	createCron(sessionId: string, options: SessionCronOptions = {}): CronManager {
		const existing = this.cronBySession.get(sessionId);
		if (existing) return existing;
		const cron = new CronManager({
			onPersist: options.persist ? (jobs) => options.persist!(jobs) : undefined,
			onDiagnostic: this.reportCronDiagnostic,
		});
		if (options.initialJobs?.length) cron.restore(options.initialJobs);
		this.cronBySession.set(sessionId, cron);
		return cron;
	}
	async closeCron(sessionId: string): Promise<void> {
		const cron = this.cronBySession.get(sessionId);
		if (!cron) return;
		await this.stopAndFlush(cron);
		this.cronBySession.delete(sessionId);
	}
	createChildCron(): CronManager {
		const cron = new CronManager({ onDiagnostic: this.reportCronDiagnostic });
		this.childCrons.add(cron);
		return cron;
	}
	async closeChildCron(cron: CronManager): Promise<void> {
		await this.stopAndFlush(cron);
		this.childCrons.delete(cron);
	}
	async closeSession(sessionId: string): Promise<void> {
		await this.closeCron(sessionId);
		for (const [taskId, task] of this.tasks) {
			if (task.sessionId === sessionId) this.tasks.delete(taskId);
		}
	}
	async closeAll(): Promise<void> {
		const sessionCrons = [...this.cronBySession.entries()];
		const childCrons = [...this.childCrons];
		const all = [...sessionCrons.map(([, cron]) => cron), ...childCrons];
		const results = await Promise.allSettled(all.map((cron) => this.stopAndFlush(cron)));
		for (const [index, result] of results.entries()) {
			if (result.status !== "fulfilled") continue;
			if (index < sessionCrons.length) this.cronBySession.delete(sessionCrons[index]![0]);
			else this.childCrons.delete(childCrons[index - sessionCrons.length]!);
		}
		const failures = results.filter((result): result is PromiseRejectedResult => result.status === "rejected");
		if (failures.length)
			throw new AggregateError(
				failures.map((failure) => failure.reason),
				"Failed to stop session cron schedulers",
			);
	}
	register(sessionId: string, taskId: string): TaskSummary {
		const task = { sessionId, taskId, status: "queued" as const };
		this.tasks.set(taskId, task);
		return task;
	}
	get(taskId: string): TaskSummary | undefined {
		return this.tasks.get(taskId);
	}
	start(taskId: string): TaskSummary {
		const task = this.require(taskId);
		const next = { ...task, status: "running" as const, startedAt: Date.now() };
		this.tasks.set(taskId, next);
		return next;
	}
	complete(taskId: string): TaskSummary {
		const task = this.require(taskId);
		const next = { ...task, status: "completed" as const, endedAt: Date.now() };
		this.tasks.set(taskId, next);
		return next;
	}
	fail(taskId: string, error?: string): TaskSummary {
		const task = this.require(taskId);
		const next = { ...task, status: "failed" as const, endedAt: Date.now(), error };
		this.tasks.set(taskId, next);
		return next;
	}
	cancel(taskId: string): TaskSummary {
		const task = this.require(taskId);
		const next = { ...task, status: "cancelled" as const, endedAt: Date.now() };
		this.tasks.set(taskId, next);
		return next;
	}
	/**
	 * Reconciles durable process events with the authenticated supervisor on
	 * session recovery.  Task ownership and recovery stay at the application
	 * task boundary; session runtimes only receive the resulting replay stream.
	 */
	async reconcileSupervisorTasks(
		recordStore: JournalPort,
		events: readonly DurableEvent[],
		supervisor: SessionProcessSupervisor,
	): Promise<DurableEvent[]> {
		const unresolved = new Map<
			string,
			Extract<DurableEvent, { type: "process.requested" | "process.started" }>["data"]["task"]
		>();
		for (const event of events) {
			if (event.type === "process.requested" || event.type === "process.started") {
				unresolved.set(event.data.task.taskId, event.data.task);
			} else if (event.type === "process.terminated") {
				unresolved.delete(event.data.task.taskId);
			}
		}

		const supervised = await supervisor.list();
		const running = new Map(supervised.filter((task) => task.status === "running").map((task) => [task.taskId, task]));
		const recovered: DurableEvent[] = [];
		for (const [taskId, task] of unresolved) {
			const owned = running.get(taskId);
			const stopped = owned ? await supervisor.stop(taskId, "Recovered session cleanup") : undefined;
			const endedAt = stopped?.endedAt ?? Date.now();
			const status = stopped?.status === "killed" ? "killed" : "lost";
			const event = await recordStore.append({
				type: "process.terminated",
				meta: { occurredAt: endedAt },
				data: {
					task: {
						...task,
						pid: stopped?.pid ?? task.pid,
						status,
						endedAt,
						exitCode: stopped?.exitCode ?? null,
						stopReason:
							status === "killed"
								? "Recovered orphan was terminated by its authenticated session supervisor"
								: "Recovered task had no authenticated live supervisor handle",
					},
				},
			});
			recovered.push(event);
			running.delete(taskId);
		}

		for (const task of running.values()) {
			const stopped = await supervisor.stop(task.taskId, "Unjournaled supervisor task cleanup");
			const endedAt = stopped?.endedAt ?? Date.now();
			const event = await recordStore.append({
				type: "process.terminated",
				meta: { occurredAt: endedAt },
				data: {
					task: {
						taskId: task.taskId,
						pid: task.pid,
						background: task.background,
						status: stopped?.status === "killed" ? "killed" : "lost",
						startedAt: task.startedAt,
						endedAt,
						exitCode: stopped?.exitCode ?? null,
						stopReason: "Supervisor contained a running task with no durable write-ahead event",
						commandDigest: crypto.createHash("sha256").update(`unjournaled:${task.taskId}`).digest("hex"),
					},
				},
			});
			recovered.push(event);
		}
		return recovered.length ? [...events, ...recovered] : [...events];
	}
	private async stopAndFlush(cron: CronManager): Promise<void> {
		// A mutation can queue an onPersist append immediately before shutdown.
		// Attempt both cleanup stages so a failed stop cannot strand an already
		// queued journal continuation after EventHub closes.
		const results = await Promise.allSettled([cron.stopAll(), cron.flushPersist()]);
		const failures = results.filter((result): result is PromiseRejectedResult => result.status === "rejected");
		if (failures.length)
			throw new AggregateError(
				failures.map((failure) => failure.reason),
				"Failed to stop cron scheduler",
			);
	}
	private require(taskId: string): TaskSummary {
		const task = this.tasks.get(taskId);
		if (!task) throw new Error(`Unknown task: ${taskId}`);
		return task;
	}
}
