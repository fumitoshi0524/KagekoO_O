export type SupervisorTaskStatus = "running" | "completed" | "failed" | "killed" | "timed_out" | "lost";

export interface SupervisorTaskInfo {
	taskId: string;
	pid?: number;
	status: SupervisorTaskStatus;
	background: boolean;
	startedAt: number;
	endedAt?: number;
	exitCode?: number | null;
	stopReason?: string;
	logPath: string;
}

export interface SupervisorSpawnRequest {
	taskId: string;
	command: string;
	args?: string[];
	cwd: string;
	env?: Record<string, string | undefined>;
	/** Explicitly allow credential-bearing variables in the child environment. */
	allowSensitiveEnv?: boolean;
	background?: boolean;
	logPath: string;
}

export interface SupervisorDescriptor {
	version: 1;
	pid: number;
	endpoint: string;
	createdAt: number;
}
