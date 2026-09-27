import type { ToolAccess } from "../../tools/types.js";
import type { ShellDialect } from "../../ports/workspace.js";

export type AnalysisConfidence = "parsed" | "partial" | "opaque";
export type CommandRisk = "safe" | "workspace" | "external" | "dangerous" | "hardline" | "opaque";

export interface CommandEffects {
	filesystem: "none" | "read" | "external-read" | "workspace-write" | "external-write" | "destructive";
	network: "none" | "read" | "write" | "remote-exec";
	credentials: "none" | "read" | "export";
	processes: "none" | "spawn" | "background" | "signal" | "system-control";
	packages: "none" | "install" | "publish";
	vcs: "none" | "read" | "local-write" | "remote-write" | "history-rewrite";
	privilege: "normal" | "elevated";
}

export interface ParsedCommand {
	name?: string;
	text: string;
	arguments: string[];
	dynamic: boolean;
}

export interface ExecutionEnvironment {
	kind: "local" | "ssh" | "container";
	hostReachable: boolean;
	privileged: boolean;
	hasHostMounts: boolean;
	hasCredentials: boolean;
}

export interface CommandAnalysis {
	dialect: ShellDialect;
	confidence: AnalysisConfidence;
	commands: ParsedCommand[];
	accesses: ToolAccess[];
	effects: CommandEffects;
	risk: CommandRisk;
	reasons: string[];
	hardlineRule?: string;
}

export interface CommandAnalysisOptions {
	dialect: ShellDialect;
	cwd: string;
	shellExecutable?: string;
	environment?: Partial<ExecutionEnvironment>;
}
