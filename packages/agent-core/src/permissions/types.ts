import type { ToolExecution } from "../tools/types.js";

export type PermissionProfile = "manual" | "workspace" | "unrestricted";
export type InteractionMode = "interactive" | "unattended";

export interface PolicyApproveResult {
	kind: "approve";
	reason?: string;
	record?: boolean;
}

export interface PolicyDenyResult {
	kind: "deny";
	message?: string;
	reason?: string;
	record?: boolean;
}

export interface PolicyAskResult {
	kind: "ask";
	reason: string;
	record?: boolean;
	deniedMessage?: string;
}

export type PolicyResult = PolicyApproveResult | PolicyDenyResult | PolicyAskResult;

export interface PolicyContext {
	toolName: string;
	args: unknown;
	profile: PermissionProfile;
	interaction: InteractionMode;
	session?: unknown;
	execution?: ToolExecution;
	reason?: string;
}

export interface PermissionPolicy {
	name: string;
	evaluate(context: PolicyContext): PolicyResult | undefined | Promise<PolicyResult | undefined>;
}

export interface AskResult {
	approved: boolean;
	record: boolean;
	feedback?: string;
}

export interface PlanModeState {
	active: boolean;
	hasWrites?: boolean;
	isPlanFile(path: string): boolean;
	markWrite(): void;
}

export interface PermissionConfig {
	denyList?: RuleEntry[];
	allowList?: RuleEntry[];
	askList?: RuleEntry[];
	[key: string]: unknown;
}

export interface RuleEntryObject {
	tool?: string;
	path?: string;
	glob?: string;
	regex?: string;
	cwd?: string;
}

export type RuleEntry = string | RuleEntryObject;

/** Structural view of the permission manager used by policies. */
export interface PermissionManagerLike {
	profile: PermissionProfile;
	interaction: InteractionMode;
	cwd: string;
	planMode?: PlanModeState;
	denyList: RuleEntry[];
	allowList: RuleEntry[];
	askList: RuleEntry[];
	history: Map<string, boolean>;
	historyKey(toolName: string, args: unknown): string;
}
