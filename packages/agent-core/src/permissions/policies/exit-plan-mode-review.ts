import type { PermissionManagerLike, PermissionPolicy, PolicyContext, PolicyResult } from "../types.js";

export class ExitPlanModeReviewAskPermissionPolicy implements PermissionPolicy {
	name = "ExitPlanModeReviewAsk";
	permission: PermissionManagerLike;

	constructor(permission: PermissionManagerLike) {
		this.permission = permission;
	}

	evaluate({ toolName }: PolicyContext): PolicyResult | undefined {
		if (toolName !== "exit_plan_mode") return undefined;
		const planMode = this.permission.planMode;
		if (!planMode?.active) return undefined;
		if (this.permission.profile === "unrestricted") return undefined;
		// If the plan file has received writes, confirm before discarding plan mode.
		if (!planMode.hasWrites) return undefined;

		return {
			kind: "ask",
			reason: "The plan file has content; confirm exiting plan mode",
			deniedMessage: "User denied exiting plan mode",
		};
	}
}
