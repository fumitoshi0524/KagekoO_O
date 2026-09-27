import type { ChildProcess } from "node:child_process";

export interface ProcessPort {
	start(input: unknown): Promise<unknown>;
	stop(id: string): Promise<void>;
}

/** Narrow process lifecycle surface consumed by the execution kernel. */
export type ProcessTaskStatus = "running" | "completed" | "failed" | "killed" | "timed_out" | "lost";
export interface ProcessTaskInfo {
	taskId: string;
	pid?: number;
	status: ProcessTaskStatus;
	stopReason?: string;
	command: string;
	background: boolean;
	startedAt: number;
	endedAt?: number;
	exitCode?: number | null;
	outputPath?: string;
}
export interface ProcessOutputSnapshot {
	preview: string;
	outputSizeBytes: number;
	previewBytes: number;
	truncated: boolean;
	fullOutputAvailable: boolean;
	persistedOutputTruncated: boolean;
	outputPath?: string;
}
export interface ProcessOutputChunk {
	content: string;
	offset: number;
	nextOffset: number;
	totalBytes: number;
	eof: boolean;
	persistedOutputTruncated: boolean;
}
export interface TrackedProcessPort {
	taskId: string;
	proc: ChildProcess | null;
	wait(timeoutMs?: number): Promise<ProcessExitResult>;
	kill(options?: {
		signal?: NodeJS.Signals | number;
		reason?: string;
		graceMs?: number;
		status?: "killed" | "timed_out";
	}): Promise<void>;
	stdout: { text(): string; truncated(): boolean };
	stderr: { text(): string; truncated(): boolean };
}
export interface ProcessExitResult {
	exitCode: number | null;
	error?: string;
	info: ProcessTaskInfo;
	timedOut?: boolean;
}
export interface ProcessTrackerPort {
	spawnDurable(command: string, args?: string[], options?: Record<string, unknown>): Promise<TrackedProcessPort>;
	list(activeOnly?: boolean, limit?: number): ProcessTaskInfo[];
	getTask(taskId: string): ProcessTaskInfo | undefined;
	wait(taskId: string, timeoutMs?: number): Promise<ProcessExitResult | undefined>;
	stop(taskId: string, reason?: string): Promise<ProcessTaskInfo | undefined>;
	getOutputSnapshot(taskId: string, previewBytes?: number): Promise<ProcessOutputSnapshot | undefined>;
	readOutput(taskId: string, offset?: number, limit?: number): Promise<ProcessOutputChunk | undefined>;
	stopForeground(): Promise<void>;
	stopAll(): Promise<void>;
	fork(): ProcessTrackerPort;
}
