import type { PermissionManagerLike, PermissionPolicy, PolicyContext, PolicyResult } from "../types.js";

/** Tools whose purpose is interactive cannot run in an unattended session. */
export class InteractionRequiredDenyPolicy implements PermissionPolicy {
	name = "InteractionRequiredDeny";

	constructor(private readonly permission: PermissionManagerLike) {}

	evaluate({ toolName }: PolicyContext): PolicyResult | undefined {
		if (this.permission.interaction === "unattended" && toolName === "ask_user") {
			return { kind: "deny", message: "ask_user is unavailable in an unattended session" };
		}
		return undefined;
	}
}
