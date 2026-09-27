import { readTool } from "./builtins/read.js";
import { writeTool } from "./builtins/write.js";
import { editTool } from "./builtins/edit.js";
import { lsTool } from "./builtins/ls.js";
import { bashTool, createBashTool, type BashToolOptions } from "./builtins/bash.js";
import { grepTool } from "./builtins/grep.js";
import { globTool } from "./builtins/glob.js";
import { todoListTool } from "./builtins/todo-list.js";
import { askUserTool } from "./builtins/ask-user.js";
import { webSearchTool } from "./builtins/web-search.js";
import { fetchUrlTool } from "./builtins/fetch-url.js";
import { createGoalTool, updateGoalTool, getGoalTool, setGoalBudgetTool } from "./builtins/goal.js";
import { skillTool } from "./builtins/skill.js";
import { cronCreateTool } from "./builtins/cron-create.js";
import { cronListTool } from "./builtins/cron-list.js";
import { cronDeleteTool } from "./builtins/cron-delete.js";
import { pluginTool } from "./builtins/plugin.js";
import { mcpAuthTool } from "./builtins/mcp-auth.js";
import { agentTool } from "./builtins/agent.js";
import { agentSwarmTool } from "./builtins/agent-swarm.js";
import { indexRepoTool } from "./builtins/memory/index-repo.js";
import { queryMemoryTool } from "./builtins/memory/query-memory.js";
import { learnUrlTool } from "./builtins/memory/learn-url.js";
import { learnTopicTool } from "./builtins/memory/learn-topic.js";
import { summarizeFileTool } from "./builtins/memory/summarize-file.js";
import { generateSkillTool } from "./builtins/memory/generate-skill.js";
import { rememberTool } from "./builtins/memory/remember.js";
import { recallProfileTool } from "./builtins/memory/recall-profile.js";
import { queryGraphTool } from "./builtins/memory/query-graph.js";
import { exploreRepoTool } from "./builtins/memory/explore-repo.js";
import { readMediaTool } from "./builtins/read-media.js";
import { taskListTool } from "./builtins/background/task-list.js";
import { taskOutputTool } from "./builtins/background/task-output.js";
import { taskStopTool } from "./builtins/background/task-stop.js";
import { enterPlanModeTool } from "./builtins/planning/enter-plan-mode.js";
import { exitPlanModeTool } from "./builtins/planning/exit-plan-mode.js";
import { reviewPendingTool } from "./builtins/review-pending.js";
import { needCapabilityTool } from "./builtins/need-capability.js";
import { ToolRegistry } from "./registry.js";
import { capabilityAccess, noAccess, searchTreeAccess } from "./accesses.js";
import type { Tool, ToolAccess } from "./types.js";

export interface BuiltinRegistryOptions {
	/** Per-tool construction options for the bash builtin; absent values keep its built-in defaults. */
	bash?: BashToolOptions;
}

export function createBuiltinRegistry(options: BuiltinRegistryOptions = {}): ToolRegistry {
	const registry = new ToolRegistry();
	const registerBuiltin = (tool: Tool<never>): void => {
		registry.register(tool, {
			origin: "builtin",
			ownerId: "@kageko/agent-core",
			accesses: tool.resolveExecution ? undefined : builtinStaticAccesses(tool.name),
		});
	};
	for (const tool of [
		readTool,
		writeTool,
		editTool,
		lsTool,
		options.bash ? createBashTool(options.bash) : bashTool,
		grepTool,
		globTool,
		todoListTool,
		askUserTool,
		webSearchTool,
		fetchUrlTool,
		createGoalTool,
		updateGoalTool,
		getGoalTool,
		setGoalBudgetTool,
		skillTool,
		cronCreateTool,
		cronListTool,
		cronDeleteTool,
		pluginTool,
		mcpAuthTool,
		agentTool,
		agentSwarmTool,
		indexRepoTool,
		queryMemoryTool,
		learnUrlTool,
		learnTopicTool,
		summarizeFileTool,
		generateSkillTool,
		rememberTool,
		recallProfileTool,
		queryGraphTool,
		exploreRepoTool,
		readMediaTool,
		taskListTool,
		taskOutputTool,
		taskStopTool,
		enterPlanModeTool,
		exitPlanModeTool,
		reviewPendingTool,
		needCapabilityTool,
	])
		registerBuiltin(tool);
	return registry;
}

function builtinStaticAccesses(name: string): ToolAccess[] {
	switch (name) {
		case "ask_user":
			return capabilityAccess("interaction", "use", "user");
		case "agent":
			return capabilityAccess("delegation", "create", "subagent");
		case "agent_swarm":
			return capabilityAccess("delegation", "create", "swarm");
		case "cron_list":
			return capabilityAccess("durable_state", "read", "cron");
		case "cron_create":
			return capabilityAccess("durable_state", "create", "cron");
		case "cron_delete":
			return capabilityAccess("durable_state", "delete", "cron");
		case "task_list":
		case "task_output":
			return capabilityAccess("process", "read", "background_tasks");
		case "task_stop":
			return capabilityAccess("process", "control", "background_task");
		case "create_goal":
			return capabilityAccess("session", "create", "goal");
		case "update_goal":
		case "set_goal_budget":
			return capabilityAccess("session", "mutate", "goal");
		case "get_goal":
			return capabilityAccess("session", "read", "goal");
		case "todo_list":
			return capabilityAccess("session", "mutate", "todo");
		case "enter_plan_mode":
		case "exit_plan_mode":
			return capabilityAccess("session", "mutate", "plan_mode");
		case "mcp_auth":
			return capabilityAccess("credential", "use", "mcp_oauth");
		case "need_capability":
			return capabilityAccess("extension", "create", "capability_request");
		case "plugin":
			return capabilityAccess("extension", "execute", "plugin_manager");
		case "skill":
			return noAccess();
		case "review_pending":
			return capabilityAccess("durable_state", "mutate", "learning_queue");
		case "index_repo":
			return [...searchTreeAccess("."), ...capabilityAccess("durable_state", "mutate", "repository_index")];
		case "generate_skill":
			return capabilityAccess("extension", "create", "generated_skill");
		case "query_memory":
		case "query_graph":
		case "recall_profile":
			return capabilityAccess("durable_state", "read", "memory");
		case "remember":
			return capabilityAccess("durable_state", "mutate", "memory");
		default:
			throw new Error(`Built-in tool ${name} has no explicit access declaration`);
	}
}

export { ToolRegistry } from "./registry.js";
export { loadAutoTools } from "./auto-loader.js";
export type { AutoToolManifest } from "./auto-loader.js";
export { createBashTool, BASH_DEFAULT_TIMEOUT_MS, BASH_MAX_TIMEOUT_MS } from "./builtins/bash.js";
export type { BashToolOptions } from "./builtins/bash.js";
export type {
	Tool,
	ToolAccess,
	FileToolAccess,
	NetworkToolAccess,
	AllToolAccess,
	NoToolAccess,
	CapabilityToolAccess,
	ToolOriginKind,
	ToolProvenance,
	ToolRegistrationOptions,
	RegisteredTool,
	ToolContext,
	ToolExecution,
	ToolParameters,
	ToolResult,
} from "./types.js";
