import type { PermissionManagerLike, PermissionPolicy, PolicyContext, PolicyResult } from "../types.js";

export class FallbackAskPolicy implements PermissionPolicy {
	name = "FallbackAsk";
	permission: PermissionManagerLike;

	constructor(permission: PermissionManagerLike) {
		this.permission = permission;
	}

	evaluate({ toolName, reason }: PolicyContext): PolicyResult | undefined {
		return {
			kind: "ask",
			reason: reason ?? `${this.permission.profile} profile requires approval`,
			deniedMessage: `User denied ${toolName}`,
		};
	}
}
