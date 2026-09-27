import type { PermissionPolicy, PolicyContext, PolicyResult } from "../types.js";
import { hasOnlyLocallySafeAccesses } from "./access-safety.js";

const DEFAULT_APPROVE_TOOLS = new Set([
	"read",
	"ls",
	"grep",
	"glob",
	"get_goal",
	"ask_user",
	"todo_list",
	"task_list",
	"task_output",
	"cron_list",
]);

export class DefaultToolApprovePolicy implements PermissionPolicy {
	name = "DefaultToolApprove";

	evaluate({ toolName, execution }: PolicyContext): PolicyResult | undefined {
		if (
			execution?.provenance?.kind === "builtin" &&
			DEFAULT_APPROVE_TOOLS.has(toolName) &&
			hasOnlyLocallySafeAccesses(execution.accesses)
		) {
			return { kind: "approve", reason: "locally safe built-in tool" };
		}
		return undefined;
	}
}
