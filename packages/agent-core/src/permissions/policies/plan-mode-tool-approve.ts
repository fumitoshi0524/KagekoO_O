import * as path from "node:path";
import type { PermissionManagerLike, PermissionPolicy, PolicyContext, PolicyResult } from "../types.js";

const WRITE_TOOLS = new Set(["write", "edit"]);

/**
 * Approve plan-mode-specific tool calls when plan mode is active.
 *
 * - enter_plan_mode is approved (harmless because the guard already denied it).
 * - exit_plan_mode is approved.
 * - write/edit are approved when the target resolves to the current plan file.
 */
export class PlanModeToolApprovePermissionPolicy implements PermissionPolicy {
	name = "PlanModeToolApprove";
	permission: PermissionManagerLike;

	constructor(permission: PermissionManagerLike) {
		this.permission = permission;
	}

	evaluate({ toolName, args }: PolicyContext): PolicyResult | undefined {
		const planMode = this.permission.planMode;
		if (!planMode?.active) return undefined;

		if (toolName === "enter_plan_mode" || toolName === "exit_plan_mode") {
			return { kind: "approve", reason: "plan mode transition" };
		}

		if (WRITE_TOOLS.has(toolName)) {
			const target = extractPath(args);
			if (target && planMode.isPlanFile(resolvePath(target, this.permission.cwd))) {
				planMode.markWrite();
				return { kind: "approve", reason: "target is the plan file" };
			}
		}

		return undefined;
	}
}

function extractPath(args: unknown): string | undefined {
	if (!args || typeof args !== "object") return undefined;
	const record = args as Record<string, unknown>;
	const candidate = record["path"] ?? record["file"] ?? undefined;
	if (typeof candidate !== "string") return undefined;
	return candidate;
}

function resolvePath(targetPath: string, cwd: string | undefined): string {
	if (path.isAbsolute(targetPath)) return targetPath;
	return path.resolve(cwd ?? process.cwd(), targetPath);
}
