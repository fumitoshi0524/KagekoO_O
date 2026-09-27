import * as fs from "node:fs/promises";
import * as path from "node:path";
import Ajv, { type ErrorObject, type ValidateFunction } from "ajv";
import {
	BASH_DEFAULT_TIMEOUT_MS,
	BASH_MAX_TIMEOUT_MS,
	DEFAULT_CAPABILITY_SYNTHESIS_TIMEOUT_MS,
	DEFAULT_COMPACTION_INPUT_RATIO,
	DEFAULT_COMPACTION_MIN_HISTORY_EVENTS,
	DEFAULT_COMPACTION_TARGET_RATIO,
	DEFAULT_COMPACT_THRESHOLD,
	DEFAULT_MCP_CALL_TIMEOUT_MS,
	DEFAULT_MCP_CONNECT_TIMEOUT_MS,
	DEFAULT_MCP_SYNTHESIS_TIMEOUT_MS,
	DEFAULT_SKILL_MIN_COMPLETED_TURNS,
	DEFAULT_SKILL_MIN_EVENTS,
	DEFAULT_SKILL_SIMILARITY_THRESHOLD,
	DEFAULT_SKILL_SYNTHESIS_COOLDOWN_EVENTS,
	DEFAULT_SKILL_SYNTHESIS_TIMEOUT_MS,
	DEFAULT_TOOL_CONCURRENCY,
	DEFAULT_TOOL_RESULT_BUDGET,
	type InteractionMode,
	type PermissionProfile,
} from "@kageko/agent-core";
import { canonicalHermesProviderId } from "@kageko/kosong";
import type { ModelMetadataOrigin, ModelMetadataProvenance } from "@kageko/kosong";
import { kagekoHomeDir } from "@kageko/oauth";

const VALID_PERMISSION_PROFILES = new Set(["manual", "workspace", "unrestricted"]);
const VALID_INTERACTION_MODES = new Set(["interactive", "unattended"]);
const VALID_SHELL_DIALECTS = new Set(["bash", "powershell", "cmd"]);

export interface ModelConfig {
	provider?: string;
	modelName?: string;
	apiKey?: string;
	baseUrl?: string;
	/** Provider-reported model context window; distinct from the local execution cap. */
	contextLength?: number;
	/** Provider-reported model capabilities retained with the selected route. */
	capabilities?: string[];
	maxContextSize?: number;
	maxOutputTokens?: number;
	/** Provider-specific reasoning/thinking selection, e.g. { enabled, effort }. */
	reasoningConfig?: Record<string, unknown>;
	temperature?: number;
	authMode?: "api" | "oauth";
	/** Per-field source metadata; configured values are never relabeled as provider truth. */
	provenance?: ModelMetadataProvenance;
	metadataSource?: ModelMetadataOrigin;
}

export interface PermissionConfig {
	defaultProfile: PermissionProfile | string;
	allowList: string[];
	denyList: string[];
	askList: string[];
}

export interface InteractionConfig {
	defaultMode: InteractionMode | string;
}

export interface ShellConfig {
	dialect: "bash" | "powershell" | "cmd";
	executable: string;
	/** Foreground shell timeout applied when a call does not request one. */
	defaultTimeoutMs: number;
	/** Upper bound applied to any requested foreground shell timeout. */
	maxTimeoutMs: number;
}

export interface McpConfig {
	servers: Record<string, unknown>;
	/** Bound on each server connect handshake. */
	connectTimeoutMs: number;
	/** Bound on each tools/list and tools/call operation. */
	callTimeoutMs: number;
}

/** Coordinator turn-execution tuning. */
export interface TurnsConfig {
	/** Maximum simultaneously running tool executions per step. */
	toolConcurrency: number;
	/** Per-tool-result character budget applied to model-facing output. */
	toolResultBudgetChars: number;
	/** Task-level elapsed-time budget. Reaching it checkpoints rather than discarding work. */
	maxWallClockMs?: number;
	/** Task-level aggregate model-token budget. */
	maxTokens?: number;
	maxCostUsd?: number;
	inputTokenCostUsd?: number;
	outputTokenCostUsd?: number;
	/** Per-tool runtime cap, independent of individual tool defaults. */
	maxToolExecutionMs?: number;
	/** Extra attempts only for retryable read-only tool failures. */
	maxToolRetries?: number;
	/** Same normalized tool call allowed before a stalled checkpoint. */
	maxRepeatedToolCalls?: number;
	/** Same normalized observation allowed before a stalled checkpoint. */
	maxNoProgressSteps?: number;
	/** Consecutive identical (tool, args) failures before a stalled checkpoint. */
	maxConsecutiveToolFailures?: number;
	/** Consecutive failures of one tool, with any arguments, before a stalled checkpoint. */
	maxToolFailureLoop?: number;
}

/** Context compaction policy for the session's ContextMemory. */
export interface CompactionConfig {
	/** Fraction of the context window that triggers compaction. */
	thresholdRatio: number;
	/** Share of the threshold retained as raw tail after compaction. */
	targetRatio: number;
	/** Share of the context window the summarizer input may occupy. */
	inputRatio: number;
	/** Minimum history length before automatic compaction may trigger. */
	minHistoryEvents: number;
}

export interface TelemetryConfig {
	enabled: boolean;
}

export interface MemoryConfig {
	autoIndex: boolean;
	rememberSessions: boolean;
}

export interface LearningConfig {
	/** Disable the complete learning pipeline while retaining the ordinary agent runtime. */
	enabled: boolean;
	/** Proposal products the resident learner may create. An empty array retains passive memory learners only. */
	proposalKinds: Array<"skill" | "tool" | "mcp">;
	/**
	 * Whether a recurring tool error may wake the generative resident learner.
	 * Error facts are always retained; the default keeps them passive because a
	 * single session's retry failure is not evidence of a reusable capability.
	 */
	synthesizeErrorPatterns: boolean;
	minContentLength: number;
	maxContentLength: number;
	erroneousToolThreshold: number;
	maxPendingEntries: number;
	autoApproveSkills: boolean;
	autoApproveCapabilities: boolean;
	/** Minimum journal history before a skill-review trigger may fire. */
	skillMinEvents: number;
	/** Minimum completed turns a session record must contain to be eligible. */
	skillMinCompletedTurns: number;
	/** Gated events required between resident learner runs. */
	skillSynthesisCooldownEvents: number;
	/** Bound on a skill-synthesis LLM call. */
	skillSynthesisTimeoutMs: number;
	/** Bound on a capability-synthesis LLM call. */
	capabilitySynthesisTimeoutMs: number;
	/** Bound on an MCP-synthesis LLM call. */
	mcpSynthesisTimeoutMs: number;
	/** Token-overlap threshold above which a proposed skill counts as a duplicate. */
	skillSimilarityThreshold: number;
}

/** Per-agent model and execution policy. */
export interface AgentRoleConfig {
	provider?: string;
	modelName?: string;
	baseUrl?: string;
	authMode?: "api" | "oauth";
	contextLength?: number;
	capabilities?: string[];
	maxContextSize?: number;
	maxOutputTokens?: number;
	reasoningConfig?: Record<string, unknown>;
	provenance?: ModelMetadataProvenance;
	metadataSource?: ModelMetadataOrigin;
	systemPrompt?: string;
	permissionProfile?: string;
	interactionMode?: string;
	tools?: string[];
	maxSteps?: number;
	/** Wall-clock bound for runs of this role as a subagent (10_000-7_200_000). */
	timeoutMs?: number;
}

/** Model metadata for a fixed Kageko system role. Its behavior is not configurable. */
export type SystemAgentRouteConfig = Pick<
	AgentRoleConfig,
	| "provider"
	| "modelName"
	| "baseUrl"
	| "authMode"
	| "contextLength"
	| "capabilities"
	| "maxContextSize"
	| "maxOutputTokens"
	| "reasoningConfig"
	| "provenance"
	| "metadataSource"
>;

/**
 * The coordinator's route plus its turn bound. Unlike the other fixed system
 * roles, the coordinator accepts `maxSteps`; everything else about its
 * behavior is not configurable.
 */
export interface CoordinatorAgentRouteConfig extends SystemAgentRouteConfig {
	/** Maximum agent steps in one checkpointable execution slice (1-250), not a task-completion budget. */
	maxSteps?: number;
}

/**
 * The resident learner's route plus its bounded-run execution parameters.
 * Absent parameters keep the `LearnerAgentRunner` built-in defaults.
 */
export interface LearnerAgentRouteConfig extends SystemAgentRouteConfig {
	/** Maximum agent steps per learner run (1-20). */
	maxSteps?: number;
	/** Wall-clock budget per learner run in milliseconds (30_000-900_000). */
	runTimeoutMs?: number;
	/** Maximum triggers queued behind a running learner run; excess is dropped (1-16). */
	maxQueuedRuns?: number;
}

/** A KimiCode-style worker declaration, selectable only by the coordinator. */
export interface SubagentProfileConfig extends AgentRoleConfig {
	description?: string;
	whenToUse?: string;
}

/** KimiCode-style worker types shipped with Kageko, separate from system roles. */
export const BUILTIN_SUBAGENT_PROFILE_IDS = ["coder", "explore", "plan"] as const;

const BUILTIN_SUBAGENT_PROFILES: Record<(typeof BUILTIN_SUBAGENT_PROFILE_IDS)[number], SubagentProfileConfig> = {
	coder: {
		description: "General software engineering worker.",
		whenToUse: "Use for delegated implementation, edits, tests, and technically complete handoff.",
		systemPrompt:
			"You are Kageko's internal coding worker. The coordinator is your caller and the only agent that speaks to the end user. Complete the delegated task with the available tools, then return a concise technical handoff: files changed, verification, and remaining risks.",
		tools: ["read", "write", "edit", "ls", "bash", "grep", "glob", "read_media", "web_search", "fetch_url"],
		maxSteps: 24,
	},
	explore: {
		description: "Read-only codebase exploration worker.",
		whenToUse: "Use for fast repository investigation, code search, and evidence gathering before implementation.",
		systemPrompt:
			"You are Kageko's internal exploration worker. The coordinator is your caller; never address the end user. You are read-only: inspect, search, and report evidence, but do not modify files or run commands that can modify the workspace. Return relevant paths and concise findings to the coordinator.",
		tools: ["read", "read_media", "ls", "grep", "glob", "query_graph", "query_memory", "web_search", "fetch_url"],
		maxSteps: 12,
	},
	plan: {
		description: "Read-only implementation planning worker.",
		whenToUse:
			"Use when the coordinator needs an implementation plan, trade-offs, or unanswered investigation questions.",
		systemPrompt:
			"You are Kageko's internal planning worker. The coordinator is your caller; never address the end user. You are read-only. Analyze the task and return a concrete implementation plan, relevant files, trade-offs, and any questions that require exploration before edits begin.",
		tools: ["read", "read_media", "ls", "grep", "glob", "query_graph", "query_memory", "web_search", "fetch_url"],
		maxSteps: 12,
	},
};

export interface AgentGraphConfig {
	/** Fixed user-facing root agent; only its model route and turn bound may be selected. */
	coordinator: CoordinatorAgentRouteConfig;
	/** @deprecated Legacy default retained so existing configurations keep working. */
	executor: AgentRoleConfig;
	/** Fixed resident learning pipeline; its model route and bounded-run parameters may be selected. */
	learner: LearnerAgentRouteConfig;
	/** User-defined executable agent classes, addressed by profile id. */
	subagents: Record<string, SubagentProfileConfig>;
	/** Maximum concurrent subagent runs per session (1-16); absent keeps the SubagentHost default. */
	maxConcurrentSubagents?: number;
}

export interface Config {
	model: ModelConfig;
	permission: PermissionConfig;
	interaction: InteractionConfig;
	shell: ShellConfig;
	mcp: McpConfig;
	telemetry: TelemetryConfig;
	memory: MemoryConfig;
	learning: LearningConfig;
	turns: TurnsConfig;
	compaction: CompactionConfig;
	agentGraph?: AgentGraphConfig;
	hooks: unknown[];
}

type RawConfig = Record<string, unknown>;

export type ConfigSource = "user" | "project";

export class ConfigError extends Error {
	readonly filePath: string;
	readonly issues: readonly string[];

	constructor(filePath: string, issues: readonly string[], options?: ErrorOptions) {
		super(`Invalid Kageko configuration at ${filePath}: ${issues.join("; ")}`, options);
		this.name = "ConfigError";
		this.filePath = filePath;
		this.issues = issues;
	}
}

const systemAgentRouteConfigSchema = {
	type: "object",
	additionalProperties: false,
	properties: {
		provider: { type: "string", minLength: 1 },
		modelName: { type: "string", minLength: 1 },
		baseUrl: { type: "string", minLength: 1 },
		authMode: { enum: ["api", "oauth"] },
		contextLength: { type: "number", exclusiveMinimum: 0 },
		capabilities: { type: "array", items: { type: "string", minLength: 1 } },
		maxContextSize: { type: "number", exclusiveMinimum: 0 },
		maxOutputTokens: { type: "number", exclusiveMinimum: 0 },
		reasoningConfig: { type: "object", additionalProperties: true },
		provenance: {
			type: "object",
			additionalProperties: false,
			properties: Object.fromEntries(
				["contextLength", "capabilities", "maxContextSize", "maxOutputTokens"].map((key) => [
					key,
					{ enum: ["authoritative", "catalog", "configured", "estimated", "unknown"] },
				]),
			),
		},
		metadataSource: {
			type: "object",
			additionalProperties: false,
			properties: {
				kind: { enum: ["provider", "catalog"] },
				providerId: { type: "string", minLength: 1 },
				endpoint: { type: "string", minLength: 1 },
				authMode: { enum: ["api", "oauth"] },
				source: { enum: ["provider-live", "public-catalog", "local-cache", "static-fallback"] },
				authoritative: { type: "boolean" },
			},
		},
	},
} as const;

const coordinatorAgentRouteConfigSchema = {
	type: "object",
	additionalProperties: false,
	properties: {
		...systemAgentRouteConfigSchema.properties,
		maxSteps: { type: "integer", minimum: 1, maximum: 250 },
	},
} as const;

const learnerAgentRouteConfigSchema = {
	type: "object",
	additionalProperties: false,
	properties: {
		...systemAgentRouteConfigSchema.properties,
		maxSteps: { type: "integer", minimum: 1, maximum: 20 },
		runTimeoutMs: { type: "integer", minimum: 30_000, maximum: 900_000 },
		maxQueuedRuns: { type: "integer", minimum: 1, maximum: 16 },
	},
} as const;

const agentRoleConfigSchema = {
	type: "object",
	additionalProperties: false,
	properties: {
		...systemAgentRouteConfigSchema.properties,
		systemPrompt: { type: "string" },
		permissionProfile: { type: "string", minLength: 1 },
		interactionMode: { type: "string", minLength: 1 },
		tools: { type: "array", items: { type: "string", minLength: 1 } },
		maxSteps: { type: "number", minimum: 1 },
		timeoutMs: { type: "integer", minimum: 10_000, maximum: 7_200_000 },
	},
} as const;

const subagentProfileConfigSchema = {
	type: "object",
	additionalProperties: false,
	properties: {
		...agentRoleConfigSchema.properties,
		description: { type: "string", minLength: 1 },
		whenToUse: { type: "string", minLength: 1 },
	},
} as const;

const configDocumentSchema = {
	type: "object",
	additionalProperties: false,
	properties: {
		model: {
			type: "object",
			additionalProperties: false,
			properties: {
				provider: { type: "string", minLength: 1 },
				modelName: { type: "string", minLength: 1 },
				apiKey: { type: "string", minLength: 1 },
				baseUrl: { type: "string", minLength: 1 },
				contextLength: { type: "number", exclusiveMinimum: 0 },
				capabilities: { type: "array", items: { type: "string", minLength: 1 } },
				maxContextSize: { type: "number", exclusiveMinimum: 0 },
				maxOutputTokens: { type: "number", exclusiveMinimum: 0 },
				reasoningConfig: { type: "object", additionalProperties: true },
				temperature: { type: "number" },
				authMode: { enum: ["api", "oauth"] },
				provenance: {
					type: "object",
					additionalProperties: false,
					properties: Object.fromEntries(
						["contextLength", "capabilities", "maxContextSize", "maxOutputTokens"].map((key) => [
							key,
							{ enum: ["authoritative", "catalog", "configured", "estimated", "unknown"] },
						]),
					),
				},
				metadataSource: {
					type: "object",
					additionalProperties: false,
					properties: {
						kind: { enum: ["provider", "catalog"] },
						providerId: { type: "string", minLength: 1 },
						endpoint: { type: "string", minLength: 1 },
						authMode: { enum: ["api", "oauth"] },
						source: { enum: ["provider-live", "public-catalog", "local-cache", "static-fallback"] },
						authoritative: { type: "boolean" },
					},
				},
			},
		},
		permission: {
			type: "object",
			additionalProperties: false,
			properties: {
				defaultProfile: { enum: ["manual", "workspace", "unrestricted"] },
				// Read-only compatibility input. ConfigService never writes this field.
				defaultMode: { enum: ["manual", "auto", "yolo"] },
				allowList: { type: "array", items: { type: "string" } },
				denyList: { type: "array", items: { type: "string" } },
				askList: { type: "array", items: { type: "string" } },
			},
		},
		interaction: {
			type: "object",
			additionalProperties: false,
			properties: { defaultMode: { enum: ["interactive", "unattended"] } },
		},
		shell: {
			type: "object",
			additionalProperties: false,
			properties: {
				dialect: { enum: ["bash", "powershell", "cmd"] },
				executable: { type: "string", minLength: 1 },
				defaultTimeoutMs: { type: "integer", minimum: 1_000 },
				maxTimeoutMs: { type: "integer", minimum: 1_000 },
			},
		},
		mcp: {
			type: "object",
			additionalProperties: false,
			properties: {
				servers: { type: "object" },
				connectTimeoutMs: { type: "integer", minimum: 1_000, maximum: 120_000 },
				callTimeoutMs: { type: "integer", minimum: 1_000, maximum: 600_000 },
			},
		},
		telemetry: {
			type: "object",
			additionalProperties: false,
			properties: { enabled: { type: "boolean" } },
		},
		memory: {
			type: "object",
			additionalProperties: false,
			properties: {
				autoIndex: { type: "boolean" },
				rememberSessions: { type: "boolean" },
			},
		},
		learning: {
			type: "object",
			additionalProperties: false,
			properties: {
				enabled: { type: "boolean" },
				synthesizeErrorPatterns: { type: "boolean" },
				proposalKinds: {
					type: "array",
					uniqueItems: true,
					items: { type: "string", enum: ["skill", "tool", "mcp"] },
				},
				minContentLength: { type: "number", minimum: 0 },
				maxContentLength: { type: "number", minimum: 1 },
				erroneousToolThreshold: { type: "number", minimum: 1 },
				maxPendingEntries: { type: "number", minimum: 1 },
				autoApproveSkills: { type: "boolean" },
				autoApproveCapabilities: { type: "boolean" },
				skillMinEvents: { type: "integer", minimum: 1, maximum: 100 },
				skillMinCompletedTurns: { type: "integer", minimum: 1, maximum: 100 },
				skillSynthesisCooldownEvents: { type: "integer", minimum: 1, maximum: 100 },
				skillSynthesisTimeoutMs: { type: "integer", minimum: 1_000 },
				capabilitySynthesisTimeoutMs: { type: "integer", minimum: 1_000 },
				mcpSynthesisTimeoutMs: { type: "integer", minimum: 1_000 },
				skillSimilarityThreshold: { type: "number", minimum: 0, maximum: 1 },
			},
		},
		turns: {
			type: "object",
			additionalProperties: false,
			properties: {
				toolConcurrency: { type: "integer", minimum: 1, maximum: 16 },
				toolResultBudgetChars: { type: "integer", minimum: 10_000, maximum: 1_000_000 },
				maxWallClockMs: { type: "integer", minimum: 1_000, maximum: 86_400_000 },
				maxTokens: { type: "integer", minimum: 1 },
				maxCostUsd: { type: "number", exclusiveMinimum: 0 },
				inputTokenCostUsd: { type: "number", minimum: 0 },
				outputTokenCostUsd: { type: "number", minimum: 0 },
				maxToolExecutionMs: { type: "integer", minimum: 1_000, maximum: 3_600_000 },
				maxToolRetries: { type: "integer", minimum: 0, maximum: 10 },
				maxRepeatedToolCalls: { type: "integer", minimum: 1, maximum: 100 },
				maxNoProgressSteps: { type: "integer", minimum: 1, maximum: 100 },
				maxConsecutiveToolFailures: { type: "integer", minimum: 1, maximum: 100 },
				maxToolFailureLoop: { type: "integer", minimum: 1, maximum: 100 },
			},
		},
		compaction: {
			type: "object",
			additionalProperties: false,
			properties: {
				thresholdRatio: { type: "number", minimum: 0, maximum: 1 },
				targetRatio: { type: "number", minimum: 0, maximum: 1 },
				inputRatio: { type: "number", minimum: 0, maximum: 1 },
				minHistoryEvents: { type: "integer", minimum: 1 },
			},
		},
		agentGraph: {
			type: "object",
			additionalProperties: false,
			properties: {
				coordinator: coordinatorAgentRouteConfigSchema,
				executor: agentRoleConfigSchema,
				learner: learnerAgentRouteConfigSchema,
				subagents: {
					type: "object",
					propertyNames: { pattern: "^[A-Za-z][A-Za-z0-9_-]{0,63}$" },
					additionalProperties: subagentProfileConfigSchema,
				},
				maxConcurrentSubagents: { type: "integer", minimum: 1, maximum: 16 },
			},
		},
		hooks: { type: "array", items: { type: "object" } },
	},
} as const;

const validateDocument: ValidateFunction = new Ajv({ allErrors: true, strict: false }).compile(configDocumentSchema);

function asConfigSection(value: unknown): RawConfig {
	if (value && typeof value === "object" && !Array.isArray(value)) {
		return value as RawConfig;
	}
	return {};
}

function normalizeProposalKinds(value: unknown): Array<"skill" | "tool" | "mcp"> {
	if (value === undefined) return ["skill", "tool", "mcp"];
	if (!Array.isArray(value)) return [];
	return value.filter(
		(kind): kind is "skill" | "tool" | "mcp" => kind === "skill" || kind === "tool" || kind === "mcp",
	);
}

/**
 * Load merged Kageko configuration without validating the final shape.
 *
 * User config lives at `~/.kageko/config.json`. Project config lives at
 * `<cwd>/.kageko/config.json` and overrides user config. Environment variables
 * override both.
 *
 * @param cwd - Project root to search for project config. Defaults to `process.cwd()`.
 * @returns Merged config object (not yet validated).
 */
export async function loadConfigRaw(cwd = process.cwd()): Promise<Config> {
	const userConfigDir = path.join(kagekoHomeDir(), ".kageko");
	const userConfigPath = path.join(userConfigDir, "config.json");
	const projectConfigPath = path.join(path.resolve(cwd), ".kageko", "config.json");

	const [userRaw, projectRaw] = await Promise.all([
		readJson(userConfigPath, "user"),
		readJson(projectConfigPath, "project"),
	]);

	const base = merge(merge({}, asConfigSection(userRaw)), asConfigSection(projectRaw));

	const modelSection = asConfigSection(base["model"]);
	const modelProvider = env("KAGEKO_MODEL_PROVIDER") ?? (modelSection["provider"] as string | undefined);
	const maxOutputTokensRaw = parseNumberEnv("KAGEKO_MAX_OUTPUT_TOKENS") ?? modelSection["maxOutputTokens"];
	const model: ModelConfig = {
		provider: modelProvider,
		modelName: env("KAGEKO_MODEL_NAME") ?? (modelSection["modelName"] as string | undefined),
		// The generic KAGEKO_API_KEY only authenticates the custom (user-supplied
		// endpoint) provider; named providers read their own env or stored
		// credentials. This mirrors providerApiKey in the composition root.
		apiKey:
			(modelProvider !== undefined && canonicalHermesProviderId(modelProvider) === "custom"
				? env("KAGEKO_API_KEY")
				: undefined) ?? (modelSection["apiKey"] as string | undefined),
		baseUrl: env("KAGEKO_BASE_URL") ?? (modelSection["baseUrl"] as string | undefined),
		contextLength: modelSection["contextLength"] as number | undefined,
		capabilities: Array.isArray(modelSection["capabilities"])
			? modelSection["capabilities"].filter((value): value is string => typeof value === "string" && value.length > 0)
			: undefined,
		maxContextSize: parseNumberEnv("KAGEKO_MAX_CONTEXT_SIZE") ?? (modelSection["maxContextSize"] as number | undefined),
		maxOutputTokens: maxOutputTokensRaw === undefined ? undefined : Number(maxOutputTokensRaw),
		reasoningConfig: isRecord(modelSection["reasoningConfig"]) ? modelSection["reasoningConfig"] : undefined,
		temperature: modelSection["temperature"] as number | undefined,
		authMode: modelSection["authMode"] === "oauth" ? "oauth" : modelSection["authMode"] === "api" ? "api" : undefined,
		provenance: isModelProvenance(modelSection["provenance"]) ? modelSection["provenance"] : undefined,
		metadataSource: isModelMetadataOrigin(modelSection["metadataSource"]) ? modelSection["metadataSource"] : undefined,
	};

	const permissionSection = asConfigSection(base["permission"]);
	const interactionSection = asConfigSection(base["interaction"]);
	if (Object.hasOwn(permissionSection, "defaultMode") && Object.hasOwn(permissionSection, "defaultProfile")) {
		throw new ConfigError("<merged-config>", [
			"legacy permission.defaultMode cannot be combined with permission.defaultProfile",
		]);
	}
	const legacyEnvironmentMode = env("KAGEKO_PERMISSION_MODE");
	const profileEnvironment = env("KAGEKO_PERMISSION_PROFILE");
	const interactionEnvironment = env("KAGEKO_INTERACTION_MODE");
	if (legacyEnvironmentMode) {
		throw legacyPermissionError("<environment:KAGEKO_PERMISSION_MODE>", legacyEnvironmentMode);
	}
	const legacyMode = permissionSection["defaultMode"] as string | undefined;
	if (legacyMode) {
		throw legacyPermissionError("<merged-config>", legacyMode);
	}
	const permission: PermissionConfig = {
		defaultProfile: profileEnvironment ?? (permissionSection["defaultProfile"] as string | undefined) ?? "manual",
		allowList: (permissionSection["allowList"] as string[] | undefined) ?? [],
		denyList: (permissionSection["denyList"] as string[] | undefined) ?? [],
		askList: (permissionSection["askList"] as string[] | undefined) ?? [],
	};
	const interaction: InteractionConfig = {
		defaultMode: interactionEnvironment ?? (interactionSection["defaultMode"] as string | undefined) ?? "interactive",
	};
	const shellSection = asConfigSection(base["shell"]);
	const defaultDialect = process.platform === "win32" ? "powershell" : "bash";
	const shell: ShellConfig = {
		dialect: (shellSection["dialect"] as ShellConfig["dialect"] | undefined) ?? defaultDialect,
		executable:
			(shellSection["executable"] as string | undefined) ?? (defaultDialect === "powershell" ? "pwsh" : "bash"),
		defaultTimeoutMs: (shellSection["defaultTimeoutMs"] as number | undefined) ?? BASH_DEFAULT_TIMEOUT_MS,
		maxTimeoutMs: (shellSection["maxTimeoutMs"] as number | undefined) ?? BASH_MAX_TIMEOUT_MS,
	};

	const mcpSection = asConfigSection(base["mcp"]);
	const mcp: McpConfig = {
		servers: (mcpSection["servers"] as Record<string, unknown> | undefined) ?? {},
		connectTimeoutMs: (mcpSection["connectTimeoutMs"] as number | undefined) ?? DEFAULT_MCP_CONNECT_TIMEOUT_MS,
		callTimeoutMs: (mcpSection["callTimeoutMs"] as number | undefined) ?? DEFAULT_MCP_CALL_TIMEOUT_MS,
	};

	const telemetrySection = asConfigSection(base["telemetry"]);
	const telemetry: TelemetryConfig = {
		enabled: parseBooleanEnv("KAGEKO_TELEMETRY_ENABLED") ?? telemetrySection["enabled"] === true,
	};

	const memorySection = asConfigSection(base["memory"]);
	const memory: MemoryConfig = {
		autoIndex: memorySection["autoIndex"] !== false,
		rememberSessions: memorySection["rememberSessions"] !== false,
	};

	const learningSection = asConfigSection(base["learning"]);
	const learning: LearningConfig = {
		enabled: learningSection["enabled"] !== false,
		proposalKinds: normalizeProposalKinds(learningSection["proposalKinds"]),
		synthesizeErrorPatterns: learningSection["synthesizeErrorPatterns"] === true,
		minContentLength: (learningSection["minContentLength"] as number | undefined) ?? 8,
		maxContentLength: (learningSection["maxContentLength"] as number | undefined) ?? 50_000,
		erroneousToolThreshold: (learningSection["erroneousToolThreshold"] as number | undefined) ?? 2,
		maxPendingEntries: (learningSection["maxPendingEntries"] as number | undefined) ?? 100,
		autoApproveSkills: (learningSection["autoApproveSkills"] as boolean | undefined) ?? false,
		autoApproveCapabilities: (learningSection["autoApproveCapabilities"] as boolean | undefined) ?? false,
		skillMinEvents: (learningSection["skillMinEvents"] as number | undefined) ?? DEFAULT_SKILL_MIN_EVENTS,
		skillMinCompletedTurns:
			(learningSection["skillMinCompletedTurns"] as number | undefined) ?? DEFAULT_SKILL_MIN_COMPLETED_TURNS,
		skillSynthesisCooldownEvents:
			(learningSection["skillSynthesisCooldownEvents"] as number | undefined) ??
			DEFAULT_SKILL_SYNTHESIS_COOLDOWN_EVENTS,
		skillSynthesisTimeoutMs:
			(learningSection["skillSynthesisTimeoutMs"] as number | undefined) ?? DEFAULT_SKILL_SYNTHESIS_TIMEOUT_MS,
		capabilitySynthesisTimeoutMs:
			(learningSection["capabilitySynthesisTimeoutMs"] as number | undefined) ??
			DEFAULT_CAPABILITY_SYNTHESIS_TIMEOUT_MS,
		mcpSynthesisTimeoutMs:
			(learningSection["mcpSynthesisTimeoutMs"] as number | undefined) ?? DEFAULT_MCP_SYNTHESIS_TIMEOUT_MS,
		skillSimilarityThreshold:
			(learningSection["skillSimilarityThreshold"] as number | undefined) ?? DEFAULT_SKILL_SIMILARITY_THRESHOLD,
	};

	const turnsSection = asConfigSection(base["turns"]);
	const turns: TurnsConfig = {
		toolConcurrency: (turnsSection["toolConcurrency"] as number | undefined) ?? DEFAULT_TOOL_CONCURRENCY,
		toolResultBudgetChars: (turnsSection["toolResultBudgetChars"] as number | undefined) ?? DEFAULT_TOOL_RESULT_BUDGET,
		maxWallClockMs: parseNumberEnv("KAGEKO_MAX_WALL_CLOCK_MS") ?? (turnsSection["maxWallClockMs"] as number | undefined),
		maxTokens: parseNumberEnv("KAGEKO_MAX_TOKENS") ?? (turnsSection["maxTokens"] as number | undefined),
		maxCostUsd: parseNumberEnv("KAGEKO_MAX_COST_USD") ?? (turnsSection["maxCostUsd"] as number | undefined),
		inputTokenCostUsd:
			parseNumberEnv("KAGEKO_INPUT_TOKEN_COST_USD") ?? (turnsSection["inputTokenCostUsd"] as number | undefined),
		outputTokenCostUsd:
			parseNumberEnv("KAGEKO_OUTPUT_TOKEN_COST_USD") ?? (turnsSection["outputTokenCostUsd"] as number | undefined),
		maxToolExecutionMs:
			parseNumberEnv("KAGEKO_TOOL_EXECUTION_MS") ?? (turnsSection["maxToolExecutionMs"] as number | undefined),
		maxToolRetries: parseNumberEnv("KAGEKO_TOOL_RETRIES") ?? (turnsSection["maxToolRetries"] as number | undefined),
		maxRepeatedToolCalls:
			parseNumberEnv("KAGEKO_MAX_REPEATED_TOOL_CALLS") ?? (turnsSection["maxRepeatedToolCalls"] as number | undefined),
		maxNoProgressSteps:
			parseNumberEnv("KAGEKO_MAX_NO_PROGRESS_STEPS") ?? (turnsSection["maxNoProgressSteps"] as number | undefined),
		maxConsecutiveToolFailures:
			parseNumberEnv("KAGEKO_MAX_CONSECUTIVE_TOOL_FAILURES") ??
			(turnsSection["maxConsecutiveToolFailures"] as number | undefined),
		maxToolFailureLoop:
			parseNumberEnv("KAGEKO_MAX_TOOL_FAILURE_LOOP") ?? (turnsSection["maxToolFailureLoop"] as number | undefined),
	};

	const compactionSection = asConfigSection(base["compaction"]);
	const compaction: CompactionConfig = {
		thresholdRatio: (compactionSection["thresholdRatio"] as number | undefined) ?? DEFAULT_COMPACT_THRESHOLD,
		targetRatio: (compactionSection["targetRatio"] as number | undefined) ?? DEFAULT_COMPACTION_TARGET_RATIO,
		inputRatio: (compactionSection["inputRatio"] as number | undefined) ?? DEFAULT_COMPACTION_INPUT_RATIO,
		minHistoryEvents:
			(compactionSection["minHistoryEvents"] as number | undefined) ?? DEFAULT_COMPACTION_MIN_HISTORY_EVENTS,
	};

	const graphSection = asConfigSection(base["agentGraph"]);
	const parseSystemRoute = (value: unknown): SystemAgentRouteConfig => {
		const section = asConfigSection(value);
		return pruneUndefined({
			provider: section["provider"] as string | undefined,
			modelName: section["modelName"] as string | undefined,
			baseUrl: section["baseUrl"] as string | undefined,
			authMode: section["authMode"] as "api" | "oauth" | undefined,
			contextLength: section["contextLength"] as number | undefined,
			capabilities: Array.isArray(section["capabilities"]) ? (section["capabilities"] as string[]) : undefined,
			maxContextSize: section["maxContextSize"] as number | undefined,
			maxOutputTokens: section["maxOutputTokens"] as number | undefined,
			reasoningConfig: isRecord(section["reasoningConfig"]) ? section["reasoningConfig"] : undefined,
			provenance: isModelProvenance(section["provenance"]) ? section["provenance"] : undefined,
			metadataSource: isModelMetadataOrigin(section["metadataSource"]) ? section["metadataSource"] : undefined,
		}) as SystemAgentRouteConfig;
	};
	const parseAgentRole = (value: unknown): AgentRoleConfig => {
		const section = asConfigSection(value);
		return pruneUndefined({
			...parseSystemRoute(section),
			systemPrompt: section["systemPrompt"] as string | undefined,
			permissionProfile: section["permissionProfile"] as string | undefined,
			interactionMode: section["interactionMode"] as string | undefined,
			tools: Array.isArray(section["tools"]) ? (section["tools"] as string[]) : undefined,
			maxSteps: section["maxSteps"] as number | undefined,
			timeoutMs: section["timeoutMs"] as number | undefined,
		}) as AgentRoleConfig;
	};
	// Same bounds-enforcement split as parseLearnerRoute: the document schema
	// (coordinatorAgentRouteConfigSchema) rejects out-of-range values.
	const parseCoordinatorRoute = (value: unknown): CoordinatorAgentRouteConfig => {
		const section = asConfigSection(value);
		return pruneUndefined({
			...parseSystemRoute(section),
			maxSteps: section["maxSteps"] as number | undefined,
		}) as CoordinatorAgentRouteConfig;
	};
	// Range bounds for the run parameters are enforced by the document schema
	// (learnerAgentRouteConfigSchema), surfacing as ConfigError like any other
	// invalid setting; this parser only carries the validated values through.
	const parseLearnerRoute = (value: unknown): LearnerAgentRouteConfig => {
		const section = asConfigSection(value);
		return pruneUndefined({
			...parseSystemRoute(section),
			maxSteps: section["maxSteps"] as number | undefined,
			runTimeoutMs: section["runTimeoutMs"] as number | undefined,
			maxQueuedRuns: section["maxQueuedRuns"] as number | undefined,
		}) as LearnerAgentRouteConfig;
	};
	const configuredSubagents = Object.fromEntries(
		Object.entries(asConfigSection(graphSection["subagents"])).map(([id, profile]) => [
			id,
			pruneUndefined({
				...parseAgentRole(profile),
				description: asConfigSection(profile)["description"] as string | undefined,
				whenToUse: asConfigSection(profile)["whenToUse"] as string | undefined,
			}) as SubagentProfileConfig,
		]),
	) as Record<string, SubagentProfileConfig>;
	const agentGraph: AgentGraphConfig = {
		coordinator: parseCoordinatorRoute(graphSection["coordinator"]),
		executor: parseAgentRole(graphSection["executor"]),
		learner: parseLearnerRoute(graphSection["learner"]),
		// Built-ins are effective defaults, never silently persisted. User and
		// project configuration may tune them field-by-field from the TUI.
		subagents: merge(BUILTIN_SUBAGENT_PROFILES, configuredSubagents) as Record<string, SubagentProfileConfig>,
		maxConcurrentSubagents: graphSection["maxConcurrentSubagents"] as number | undefined,
	};

	const hooks = (base["hooks"] as unknown[] | undefined) ?? [];

	return {
		model: pruneUndefined(model) as ModelConfig,
		permission,
		interaction,
		shell,
		mcp,
		telemetry,
		memory,
		learning,
		turns,
		compaction,
		agentGraph,
		hooks,
	};
}

function isModelProvenance(value: unknown): value is ModelMetadataProvenance {
	if (!value || typeof value !== "object" || Array.isArray(value)) return false;
	const record = value as Record<string, unknown>;
	return ["contextLength", "capabilities", "maxContextSize", "maxOutputTokens"].every(
		(key) =>
			record[key] === "authoritative" ||
			record[key] === "catalog" ||
			record[key] === "configured" ||
			record[key] === "estimated" ||
			record[key] === "unknown",
	);
}

function isRecord(value: unknown): value is Record<string, unknown> {
	return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isModelMetadataOrigin(value: unknown): value is ModelMetadataOrigin {
	if (!value || typeof value !== "object" || Array.isArray(value)) return false;
	const record = value as Record<string, unknown>;
	if ((record["kind"] !== "provider" && record["kind"] !== "catalog") || typeof record["providerId"] !== "string")
		return false;
	if (
		record["source"] !== undefined &&
		!(["provider-live", "public-catalog", "local-cache", "static-fallback"] as readonly unknown[]).includes(
			record["source"],
		)
	)
		return false;
	if (record["authoritative"] !== undefined && typeof record["authoritative"] !== "boolean") return false;
	return record["kind"] === "provider"
		? typeof record["endpoint"] === "string" && record["endpoint"].length > 0
		: record["endpoint"] === undefined || typeof record["endpoint"] === "string";
}

/**
 * Load merged Kageko configuration and validate it.
 *
 * @param cwd - Project root to search for project config. Defaults to `process.cwd()`.
 * @returns Merged and validated config object.
 */
export async function loadConfig(cwd = process.cwd()): Promise<Config> {
	const config = await loadConfigRaw(cwd);
	validateConfig(config);
	return config;
}

async function readJson(filePath: string, source: ConfigSource): Promise<RawConfig | undefined> {
	try {
		const text = await fs.readFile(filePath, "utf-8");
		const parsed = JSON.parse(text) as unknown;
		return validateConfigDocument(parsed, filePath, source);
	} catch (err) {
		if ((err as NodeJS.ErrnoException).code === "ENOENT") return undefined;
		if (err instanceof ConfigError) throw err;
		if (err instanceof SyntaxError) {
			throw new ConfigError(filePath, [`invalid JSON: ${err.message}`], { cause: err });
		}
		throw new ConfigError(filePath, [`could not be read: ${(err as Error).message}`], { cause: err });
	}
}

export function validateConfigDocument(value: unknown, filePath: string, source: ConfigSource): RawConfig {
	if (!value || typeof value !== "object" || Array.isArray(value)) {
		throw new ConfigError(filePath, ["root must be a JSON object"]);
	}
	if (!validateDocument(value)) {
		throw new ConfigError(filePath, formatSchemaErrors(validateDocument.errors));
	}
	const document = value as RawConfig;
	const agentGraph = asConfigSection(document["agentGraph"]);
	const subagents = asConfigSection(agentGraph["subagents"]);
	for (const id of Object.keys(subagents)) {
		if (["coordinator", "learner", "default", "executor"].includes(id)) {
			throw new ConfigError(filePath, [
				`/agentGraph/subagents/${id} is reserved; coordinator and learner are fixed system roles, and default/executor are legacy internal routes`,
			]);
		}
	}
	const permission = asConfigSection(document["permission"]);
	if (Object.hasOwn(permission, "defaultMode") && Object.hasOwn(permission, "defaultProfile")) {
		throw new ConfigError(filePath, ["/permission/defaultMode cannot be combined with /permission/defaultProfile"]);
	}
	if (source === "project" && Object.hasOwn(asConfigSection(document["model"]), "apiKey")) {
		throw new ConfigError(filePath, [
			"/model/apiKey is forbidden in project configuration; use a credential reference or KAGEKO_API_KEY (custom provider only)",
		]);
	}
	return document;
}

function env(name: string): string | undefined {
	const value = process.env[name];
	const trimmed = value?.trim();
	return trimmed ? trimmed : undefined;
}

function parseNumberEnv(name: string): number | undefined {
	const value = env(name);
	if (value === undefined) return undefined;
	const parsed = Number(value);
	if (!Number.isFinite(parsed)) {
		throw new ConfigError(`<environment:${name}>`, [`must be a finite number, got ${JSON.stringify(value)}`]);
	}
	return parsed;
}

function parseBooleanEnv(name: string): boolean | undefined {
	const value = env(name)?.toLowerCase();
	if (value === undefined) return undefined;
	if (value === "1" || value === "true" || value === "yes" || value === "on") return true;
	if (value === "0" || value === "false" || value === "no" || value === "off") return false;
	throw new ConfigError(`<environment:${name}>`, [`must be a boolean (true/false, 1/0, yes/no, on/off)`]);
}

function formatSchemaErrors(errors: ErrorObject[] | null | undefined): string[] {
	return (errors ?? []).map((error) => {
		const path = error.instancePath || "/";
		if (error.keyword === "additionalProperties") {
			const property = String(error.params["additionalProperty"] ?? "unknown");
			return `${path === "/" ? "" : path}/${property} is not a recognized setting`;
		}
		return `${path} ${error.message ?? "is invalid"}`;
	});
}

const POLLUTING_KEYS = new Set(["__proto__", "constructor", "prototype"]);

function merge(target: RawConfig, source: RawConfig): RawConfig {
	const out: RawConfig = Object.assign(Object.create(null), target);
	for (const key of Object.keys(source)) {
		if (POLLUTING_KEYS.has(key)) continue;
		const value = source[key];
		if (value && typeof value === "object" && !Array.isArray(value)) {
			out[key] = merge(asConfigSection(out[key]), value as RawConfig);
		} else {
			out[key] = value;
		}
	}
	return out;
}

export function validateConfig(config: {
	model: ModelConfig;
	permission: PermissionConfig;
	interaction: InteractionConfig;
	shell: ShellConfig;
	mcp: McpConfig;
	telemetry: TelemetryConfig;
	memory: MemoryConfig;
}): void {
	const { provider, maxContextSize } = config.model ?? {};
	if (typeof provider !== "string" || provider.length === 0) {
		throw new Error("Model config must specify a non-empty `provider` (or set KAGEKO_MODEL_PROVIDER).");
	}
	if (!Number.isFinite(maxContextSize) || maxContextSize! <= 0) {
		throw new Error("Model config must specify `maxContextSize` > 0 (or set KAGEKO_MAX_CONTEXT_SIZE).");
	}
	if (!VALID_PERMISSION_PROFILES.has(config.permission?.defaultProfile as string)) {
		throw new Error(
			`Permission profile must be one of: manual, workspace, unrestricted. Got: ${config.permission?.defaultProfile}`,
		);
	}
	if (!VALID_INTERACTION_MODES.has(config.interaction?.defaultMode as string)) {
		throw new Error(
			`Interaction mode must be one of: interactive, unattended. Got: ${config.interaction?.defaultMode}`,
		);
	}
	if (!VALID_SHELL_DIALECTS.has(config.shell?.dialect as string) || !config.shell?.executable?.trim()) {
		throw new Error("Shell config must specify a valid dialect and non-empty executable.");
	}
	if (
		config.model.maxOutputTokens !== undefined &&
		(!Number.isFinite(config.model.maxOutputTokens) || config.model.maxOutputTokens <= 0)
	) {
		throw new Error("Model config `maxOutputTokens` must be a finite number > 0.");
	}
}

function legacyPermissionError(source: string, value: string): ConfigError {
	return new ConfigError(source, [
		`legacy permission mode ${JSON.stringify(value)} is ambiguous; replace it with permission.defaultProfile (manual, workspace, or unrestricted) and interaction.defaultMode (interactive or unattended)`,
	]);
}

export function pruneUndefined<T extends object>(obj: T): Partial<T> {
	return Object.fromEntries(Object.entries(obj).filter(([, v]) => v !== undefined)) as Partial<T>;
}
