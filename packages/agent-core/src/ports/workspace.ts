import type { Dirent } from "node:fs";

export interface WorkspacePort {
	cwd: string;
	contains(target: string): boolean;
}

/** Security-scoped filesystem and shell surface consumed by agent tools. */
export type ShellDialect = "bash" | "powershell" | "cmd";
export interface KaosPort {
	cwd: string;
	env: Record<string, string | undefined>;
	shellDialect: ShellDialect;
	shellExecutable: string;
	maxFileSizeBytes: number;
	readText(filePath: string): Promise<string>;
	writeText(filePath: string, data: string): Promise<void>;
	readdir(dirPath: string): Promise<Dirent[]>;
	resolveReal(filePath: string): Promise<string>;
	shellInvocation(script: string): { command: string; args: string[] };
}
export function isKaosError(error: unknown, kind: "FileTooLargeError" | "PathSecurityError"): error is Error {
	return error instanceof Error && error.name === kind;
}

/** Injected environment scrubber; the composition root supplies the kaos implementation. */
export type EnvironmentScrubber = (
	environment: Record<string, string | undefined>,
	options?: { allowSensitive?: boolean },
) => Record<string, string>;
