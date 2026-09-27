import * as path from "node:path";
import { createPolicyChain } from "./policies/index.js";
import type {
	AskResult,
	PermissionConfig,
	InteractionMode,
	PermissionProfile,
	PermissionPolicy,
	PlanModeState,
	PolicyResult,
	RuleEntry,
} from "./types.js";
import type { ToolExecution } from "../tools/types.js";

export interface PermissionDecision {
	approved: boolean;
	reason?: string;
	record?: boolean;
	feedback?: string;
}

export type ApprovalHandler = (
	toolName: string,
	args: unknown,
	reason?: string,
	signal?: AbortSignal,
) =>
	| Promise<boolean | { approved: boolean; record?: boolean; feedback?: string }>
	| boolean
	| { approved: boolean; record?: boolean; feedback?: string };

export interface HookEngine {
	trigger(event: string, payload: Record<string, unknown>): Promise<unknown[] | undefined>;
}

export interface PermissionManagerOptions {
	profile?: PermissionProfile;
	interaction?: InteractionMode;
	cwd?: string;
	/** User-level Kageko directory, supplied by the caller (the application layer owns its location). */
	kagekoDir: string;
	safeDirs?: string[];
	approvalHandler?: ApprovalHandler;
	planMode?: PlanModeState;
	hookEngine?: HookEngine;
	config?: PermissionConfig;
	denyList?: RuleEntry[];
	allowList?: RuleEntry[];
	askList?: RuleEntry[];
	onDiagnostic?: (message: string, error?: unknown) => void;
}

/**
 * Permission manager with a policy-chain design inspired by kimi-code.
 *
 * Policies are evaluated in order; the first non-undefined result wins.
 */
export class PermissionManager {
	profile: PermissionProfile;
	interaction: InteractionMode;
	cwd: string;
	kagekoDir: string;
	safeDirs: string[];
	approvalHandler?: ApprovalHandler;
	planMode?: PlanModeState;
	hookEngine?: HookEngine;
	config: PermissionConfig;
	denyList: RuleEntry[];
	allowList: RuleEntry[];
	askList: RuleEntry[];
	private readonly onDiagnostic?: (message: string, error?: unknown) => void;
	history: Map<string, boolean> = new Map();
	policies!: PermissionPolicy[];

	constructor(options: PermissionManagerOptions) {
		this.profile = options.profile ?? "manual";
		this.interaction = options.interaction ?? "interactive";
		this.cwd = path.resolve(options.cwd ?? process.cwd());
		this.kagekoDir = path.resolve(options.kagekoDir);
		this.safeDirs = [this.cwd, this.kagekoDir, ...(options.safeDirs ?? [])].map((d) => path.resolve(d));
		this.approvalHandler = options.approvalHandler;
		this.planMode = options.planMode;
		this.hookEngine = options.hookEngine;
		this.config = options.config ?? {};
		this.denyList = options.denyList ?? [];
		this.allowList = options.allowList ?? [];
		this.askList = options.askList ?? [];
		this.onDiagnostic = options.onDiagnostic;
		this._rebuildPolicies();
	}

	setApprovalHandler(handler: ApprovalHandler | undefined): void {
		this.approvalHandler = handler;
	}

	setPlanMode(planMode: PlanModeState | undefined): void {
		this.planMode = planMode;
		this._rebuildPolicies();
	}

	setHookEngine(hookEngine: HookEngine | undefined): void {
		this.hookEngine = hookEngine;
		this._rebuildPolicies();
	}

	setConfig(config: PermissionConfig | undefined): void {
		this.config = config ?? {};
		this.denyList = this.config.denyList ?? [];
		this.allowList = this.config.allowList ?? [];
		this.askList = this.config.askList ?? [];
		this._rebuildPolicies();
	}

	_rebuildPolicies(): void {
		this.policies = createPolicyChain({ permission: this, planMode: this.planMode, hookEngine: this.hookEngine });
	}

	async authorize(
		toolName: string,
		args: unknown,
		ctx: { session?: unknown; execution?: ToolExecution; signal?: AbortSignal } = {},
	): Promise<PermissionDecision> {
		try {
			return await this._authorizeUnchecked(toolName, args, ctx);
		} catch (error) {
			this.reportDiagnostic(`Permission evaluation failed closed for ${toolName}`, error);
			return { approved: false, reason: `permission evaluation failed for ${toolName}` };
		}
	}

	private async _authorizeUnchecked(
		toolName: string,
		args: unknown,
		ctx: { session?: unknown; execution?: ToolExecution; signal?: AbortSignal },
	): Promise<PermissionDecision> {
		const context = {
			toolName,
			args,
			profile: this.profile,
			interaction: this.interaction,
			session: ctx.session,
			execution: ctx.execution,
		};

		const requestBlocks = await this.hookEngine?.trigger("PermissionRequest", {
			toolName,
			args,
			profile: this.profile,
			interaction: this.interaction,
		});
		const block = requestBlocks?.find((r) => {
			const item = r && typeof r === "object" ? (r as Record<string, unknown>) : undefined;
			return item?.["action"] === "block" || item?.["block"];
		});
		if (block) {
			const blockRecord = block && typeof block === "object" ? (block as Record<string, unknown>) : {};
			const decision: PermissionDecision = {
				approved: false,
				reason: (blockRecord["reason"] ?? blockRecord["message"] ?? "blocked by PermissionRequest hook") as
					string | undefined,
			};
			await this.hookEngine?.trigger("PermissionResult", {
				toolName,
				args,
				approved: decision.approved,
				reason: decision.reason,
				profile: this.profile,
				interaction: this.interaction,
			});
			return decision;
		}

		for (const policy of this.policies) {
			const result = await policy.evaluate(context);
			if (result !== undefined) {
				const decision =
					result.kind === "ask"
						? await this.resolveAsk(toolName, args, result, ctx.signal)
						: policyResultToDecision(result);
				if (decision.approved && decision.record === true) {
					this.recordApproval(toolName, args, context.execution);
				}
				await this.hookEngine?.trigger("PermissionResult", {
					toolName,
					args,
					approved: decision.approved,
					reason: decision.reason,
					profile: this.profile,
					interaction: this.interaction,
				});
				return decision;
			}
		}

		const decision: PermissionDecision = { approved: false, reason: "no policy decided" };
		await this.hookEngine?.trigger("PermissionResult", {
			toolName,
			args,
			approved: decision.approved,
			reason: decision.reason,
			profile: this.profile,
			interaction: this.interaction,
		});
		return decision;
	}

	async ask(toolName: string, args: unknown, reason?: string, signal?: AbortSignal): Promise<AskResult> {
		if (!this.approvalHandler) {
			return { approved: false, record: false };
		}
		try {
			const raw = await this.approvalHandler(toolName, args, reason, signal);
			if (raw && typeof raw === "object") {
				const record = raw as { approved?: unknown; record?: unknown; feedback?: unknown };
				return {
					approved: Boolean(record.approved),
					record: record.record !== false,
					...(typeof record.feedback === "string" && record.feedback.trim()
						? { feedback: record.feedback.trim() }
						: {}),
				};
			}
			return { approved: Boolean(raw), record: Boolean(raw) };
		} catch {
			return { approved: false, record: false };
		}
	}

	private async resolveAsk(
		toolName: string,
		args: unknown,
		result: Extract<PolicyResult, { kind: "ask" }>,
		signal?: AbortSignal,
	): Promise<PermissionDecision> {
		if (this.interaction === "unattended") {
			return {
				approved: false,
				reason: `Approval required for ${toolName}, but the session is unattended${result.deniedMessage ? `: ${result.deniedMessage}` : ""}`,
				record: false,
			};
		}
		const response = await this.ask(toolName, args, result.reason, signal);
		if (!response.approved && signal?.aborted) {
			// The approval prompt was cancelled (turn aborted), not denied —
			// report the reason honestly so the model does not see "User denied".
			return { approved: false, reason: `Approval request for ${toolName} was cancelled`, record: false };
		}
		const feedback = response.feedback;
		return response.approved
			? {
					approved: true,
					reason: feedback ? `user approved with feedback: ${feedback}` : "user approved",
					record: result.record === false ? false : response.record,
					...(feedback ? { feedback } : {}),
				}
			: {
					approved: false,
					reason: feedback
						? `${result.deniedMessage ?? `User denied ${toolName}`}: ${feedback}`
						: (result.deniedMessage ?? `User denied ${toolName}`),
					record: false,
					...(feedback ? { feedback } : {}),
				};
	}

	recordApproval(toolName: string, args: unknown, execution?: ToolExecution): void {
		let key: string;
		if (execution?.approvalRule) {
			key = `${toolName}:${execution.approvalRule}`;
		} else {
			key = this.historyKey(toolName, args);
		}
		this.history.delete(key);
		this.history.set(key, true);
		while (this.history.size > MAX_HISTORY_ENTRIES) {
			const oldest = this.history.keys().next().value as string | undefined;
			if (oldest === undefined) break;
			this.history.delete(oldest);
		}
	}

	historyKey(toolName: string, args: unknown): string {
		return `${toolName}:${safeHistoryStringify(normalizeArgsForHistory(args, this.cwd))}`;
	}

	private reportDiagnostic(message: string, error?: unknown): void {
		try {
			this.onDiagnostic?.(message, error);
		} catch {
			// Diagnostic sinks never influence permission decisions.
		}
	}
}

const MAX_HISTORY_ENTRIES = 500;

function safeHistoryStringify(value: unknown): string {
	try {
		return JSON.stringify(value);
	} catch {
		return "[unserializable]";
	}
}

function normalizeArgsForHistory(args: unknown, cwd: string): unknown {
	if (args === null || typeof args !== "object") {
		return args;
	}

	const record = args as Record<string, unknown>;
	const sorted: Record<string, unknown> = {};
	for (const key of Object.keys(record).sort()) {
		const value = record[key];
		if (value === undefined) continue;
		sorted[key] = normalizeValueForHistory(value, cwd, isPathLikeKey(key));
	}
	return sorted;
}

const CASE_INSENSITIVE_PLATFORMS = new Set(["win32", "darwin"]);

function normalizeValueForHistory(value: unknown, cwd: string, pathLike: boolean): unknown {
	if (Array.isArray(value)) {
		return value.map((v) => normalizeValueForHistory(v, cwd, pathLike));
	}
	if (typeof value === "object" && value !== null) {
		return normalizeArgsForHistory(value, cwd);
	}
	if (pathLike && typeof value === "string" && value.length > 0 && !/^[a-z][+\-.\w]*:/i.test(value)) {
		// Normalize plausible relative paths to absolute paths.
		const normalized = !path.isAbsolute(value) ? path.resolve(cwd, value) : value;
		return CASE_INSENSITIVE_PLATFORMS.has(process.platform) ? normalized.toLowerCase() : normalized;
	}
	return value;
}

function isPathLikeKey(key: string): boolean {
	return /(?:^|_)(?:path|paths|file|files|cwd|dir|directory|root|target|destination)$/i.test(key);
}

function policyResultToDecision(result: PolicyResult): PermissionDecision {
	switch (result.kind) {
		case "approve":
			return { approved: true, reason: result.reason, record: result.record };
		case "deny":
			return { approved: false, reason: result.message ?? result.reason ?? "denied", record: result.record };
		case "ask":
			return { approved: false, reason: result.reason, record: false };
		default:
			return { approved: false, reason: "unknown policy result", record: (result as { record?: boolean }).record };
	}
}
