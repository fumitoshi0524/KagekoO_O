import type { PermissionPolicy, PlanModeState, PolicyContext, PolicyResult } from "../types.js";
import type { ToolAccess } from "../../tools/types.js";

export class PlanModeGuardDenyPolicy implements PermissionPolicy {
	name = "PlanModeGuardDeny";
	planMode?: PlanModeState;

	constructor(planMode?: PlanModeState) {
		this.planMode = planMode;
	}

	evaluate({ toolName, args, execution }: PolicyContext): PolicyResult | undefined {
		if (!this.planMode?.active) return undefined;

		if (toolName === "enter_plan_mode") {
			return { kind: "deny", message: "Already in plan mode" };
		}
		if (toolName === "exit_plan_mode") {
			return undefined;
		}

		if (toolName === "bash") {
			return { kind: "deny", message: "bash is blocked in plan mode" };
		}

		if (["write", "edit"].includes(toolName)) {
			const target = extractPath(args);
			if (target && this.planMode.isPlanFile(target)) {
				return undefined;
			}
			return { kind: "deny", message: "writes are blocked in plan mode except to the plan file" };
		}

		if (["task_stop", "cron_create", "cron_delete"].includes(toolName)) {
			return { kind: "deny", message: "Blocked in plan mode" };
		}

		if (["agent", "agent_swarm"].includes(toolName)) {
			return { kind: "deny", message: "Subagents are blocked in plan mode" };
		}

		if (toolName === "plugin" && ["run", "install"].includes(getStringAction(args) ?? "")) {
			return { kind: "deny", message: "Plugin mutation or execution is blocked in plan mode" };
		}

		if (toolName.startsWith("mcp__") && !isReadOnlyExecution(execution)) {
			return { kind: "deny", message: "Write-capable or unclassified MCP tools are blocked in plan mode" };
		}

		if (execution?.accesses?.some(isMutationAccess) || MEMORY_MUTATION_TOOLS.has(toolName)) {
			return { kind: "deny", message: "Memory and durable-state mutations are blocked in plan mode" };
		}

		return undefined;
	}
}

const MEMORY_MUTATION_TOOLS = new Set([
	"remember",
	"index_repo",
	"learn_url",
	"learn_topic",
	"summarize_file",
	"generate_skill",
	"explore_repo",
	"review_pending",
]);

function isMutationAccess(access: ToolAccess): boolean {
	if (access.kind === "file") return ["write", "readwrite"].includes(access.operation ?? "");
	if (access.kind === "all") return true;
	if (access.kind === "none" || access.kind === "network") return false;
	return ["mutate", "create", "delete", "execute", "control"].includes(access.operation);
}

function isReadOnlyExecution(execution: PolicyContext["execution"]): boolean {
	return Boolean(execution?.accesses?.length) && !execution!.accesses!.some(isMutationAccess);
}

function extractPath(args: unknown): string | undefined {
	if (!args || typeof args !== "object") return undefined;
	const record = args as Record<string, unknown>;
	const candidate = record["path"] ?? record["file"];
	if (typeof candidate !== "string") return undefined;
	return candidate;
}

function getStringAction(args: unknown): string | undefined {
	if (!args || typeof args !== "object") return undefined;
	const action = (args as Record<string, unknown>)["action"];
	return typeof action === "string" ? action : undefined;
}
