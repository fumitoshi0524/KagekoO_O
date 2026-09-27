import type { PermissionManagerLike, PermissionPolicy, PolicyContext, PolicyResult } from "../types.js";

export class GoalStartReviewAskPermissionPolicy implements PermissionPolicy {
	name = "GoalStartReviewAsk";
	permission: PermissionManagerLike;

	constructor(permission: PermissionManagerLike) {
		this.permission = permission;
	}

	evaluate({ toolName, session }: PolicyContext): PolicyResult | undefined {
		if (toolName !== "create_goal") return undefined;
		if (this.permission.profile === "unrestricted") return undefined;

		const goalStore = getGoalStore(session);
		const activeGoal = goalStore?.["activeGoal"];
		if (
			activeGoal !== null &&
			typeof activeGoal === "object" &&
			(activeGoal as Record<string, unknown>)["status"] === "active"
		)
			return undefined;

		return { kind: "ask", reason: "starting a new goal", deniedMessage: "User denied starting a new goal" };
	}
}

function getGoalStore(session: unknown): Record<string, unknown> | undefined {
	if (session === null || typeof session !== "object") return undefined;
	const record = session as Record<string, unknown>;
	const goalStore = record["goalStore"];
	if (goalStore === null || typeof goalStore !== "object") return undefined;
	return goalStore as Record<string, unknown>;
}
