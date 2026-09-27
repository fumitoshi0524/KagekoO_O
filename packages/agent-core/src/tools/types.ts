import type { ValidateFunction } from "ajv";
import type { KaosPort } from "../ports/workspace.js";
import type { ProcessTrackerPort } from "../ports/process.js";
import type { McpManager } from "../capabilities/mcp/mcp-manager.js";
import type { SubagentHost } from "../subagents/subagent-host.js";
import type { CommandAnalysis } from "../security/command-analysis/index.js";
import type { ToolRegistry } from "./registry.js";
import type { AgentLlm } from "../turn/turn-runner.js";
import type { JournalPort } from "../ports/repository.js";
import type { SkillRegistry } from "../capabilities/skills/skill-loader.js";
import type { PluginManager } from "../capabilities/plugins/plugin-loader.js";
import type { McpTokenStore } from "../capabilities/mcp/mcp-auth.js";
import type { MemoryEngine } from "../memory/engine.js";
import type { PlanMode } from "../agent/plan/plan-mode.js";
import type { LearningBus, LearningProcessor } from "../memory/learning/index.js";
import type { TodoState } from "../planning/todo-state.js";

export interface FileToolAccess {
	kind: "file";
	operation?: "read" | "write" | "readwrite" | "search";
	path?: string;
	recursive?: boolean;
}

export interface NetworkToolAccess {
	kind: "network";
	operation: "search" | "fetch" | "send";
	target: string;
	method: string;
	credentialed: boolean;
	sendsContent: boolean;
}

export interface AllToolAccess {
	kind: "all";
}

export interface NoToolAccess {
	kind: "none";
}

export interface CapabilityToolAccess {
	kind: "process" | "session" | "durable_state" | "extension" | "delegation" | "credential" | "interaction";
	operation: "read" | "mutate" | "create" | "delete" | "execute" | "use" | "control";
	target: string;
}

/** A single resource access declaration for a tool call. */
export type ToolAccess = FileToolAccess | NetworkToolAccess | CapabilityToolAccess | NoToolAccess | AllToolAccess;

export type ToolOriginKind = "builtin" | "skill" | "project_auto" | "plugin" | "mcp" | "user";

export interface ToolProvenance {
	kind: ToolOriginKind;
	ownerId: string;
	registrationId: string;
}

/** Application-owned scheduler contract consumed by the cron tools. */
export interface CronPort {
	list(): readonly CronListItem[];
	create(options: CronCreateOptions): CronCreateResult;
	remove(id: string): boolean;
	flushPersist(): Promise<void>;
}

export interface CronCreateOptions {
	cron: string;
	prompt: string;
	recurring?: boolean;
}

export interface CronCreateResult {
	id: string;
	cron: string;
	humanSchedule: string;
	recurring: boolean;
	nextFireAt: string | null;
}

export interface CronListItem extends CronCreateResult {
	prompt: string;
	ageDays: number;
	stale: boolean;
}

export interface TodoStorePort {
	todos: TodoState[];
	save?(): Promise<void>;
}

/**
 * The narrow session capability required by tools.
 *
 * Application runtimes adapt their richer session objects to this port.  The
 * core must never depend on an application implementation type.
 */
export interface ToolSessionPort {
	cwd: string;
	kaos: KaosPort;
	registry?: ToolRegistry;
	llm?: AgentLlm;
	goalStore?: Record<string, unknown>;
	todoStore?: TodoStorePort;
	recordStore?: JournalPort;
	tracker?: ProcessTrackerPort;
	mcp?: McpManager;
	skills?: SkillRegistry;
	plugins?: PluginManager;
	cron?: CronPort;
	memory?: MemoryEngine;
	planMode?: PlanMode;
	subagentHost?: SubagentHost;
	learningBus?: LearningBus;
	learningProcessor?: LearningProcessor;
	interaction?: {
		ask(question: string, options?: readonly string[]): Promise<string | readonly string[]>;
	};
	/** Host-owned diagnostic/interaction presentation; core never writes a terminal. */
	reportDiagnostic?: (diagnostic: {
		readonly code: string;
		readonly message: string;
		readonly error?: unknown;
	}) => void | Promise<void>;
	pluginOperations?: { install(source: string, pluginId?: string): Promise<string> };
	mcpTokenStore?: McpTokenStore;
}

export interface ToolRegistrationOptions {
	origin: ToolOriginKind;
	ownerId?: string;
	/** Static access plan for tools whose resource scope does not depend on arguments. */
	accesses?: ToolAccess[];
}

export interface RegisteredTool {
	tool: Tool<Record<string, unknown>>;
	provenance: ToolProvenance;
	staticAccesses?: ToolAccess[];
}

export interface ToolResult {
	output: unknown;
	isError?: boolean;
	truncated?: boolean;
	[key: string]: unknown;
}

export interface ToolContext {
	kaos?: KaosPort;
	session?: ToolSessionPort;
	tracker?: ProcessTrackerPort;
	mcp?: McpManager;
	signal?: AbortSignal;
	subagentHost?: SubagentHost;
	parentActivityId?: string;
	parentToolCallId?: string;
	[key: string]: unknown;
}

export type ToolExecute<TArgs = Record<string, unknown>> = (
	args: TArgs,
	context: ToolContext,
) => Promise<ToolResult> | ToolResult;

/** Resolved execution plan for a single tool call. */
export interface ToolExecution<TArgs = Record<string, unknown>> {
	accesses?: ToolAccess[];
	approvalRule?: string;
	matchesRule?: (ruleArgs: string) => boolean;
	execute?: ToolExecute<TArgs>;
	stopBatchAfterThis?: boolean;
	/** Assigned by ToolRegistry after resolution; tool implementations cannot choose their own identity. */
	provenance?: ToolProvenance;
	/** Deterministic shell analysis, when this execution launches a command. */
	commandAnalysis?: CommandAnalysis;
}

/** JSON Schema object (loosely typed; validated with ajv). */
export type ToolParameters = Record<string, unknown>;

export interface Tool<TArgs = Record<string, unknown>> {
	name: string;
	description?: string;
	parameters?: ToolParameters;
	execute?: ToolExecute<TArgs>;
	resolveExecution?: (args: TArgs, context?: ToolContext) => ToolExecution<TArgs>;
}

export interface McpToolDescriptor {
	name: string;
	description?: string;
	inputSchema?: ToolParameters;
}

export type { ValidateFunction };
