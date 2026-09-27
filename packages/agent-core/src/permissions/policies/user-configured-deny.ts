import { matchesEntry } from "./rule-matching.js";
import type { PermissionManagerLike, PermissionPolicy, PolicyContext, PolicyResult } from "../types.js";

export class UserConfiguredDenyPermissionPolicy implements PermissionPolicy {
	name = "UserConfiguredDeny";
	permission: PermissionManagerLike;

	constructor(permission: PermissionManagerLike) {
		this.permission = permission;
	}

	evaluate({ toolName, args, execution }: PolicyContext): PolicyResult | undefined {
		for (const entry of this.permission.denyList ?? []) {
			if (matchesEntry(toolName, args, execution, this.permission.cwd, entry)) {
				return { kind: "deny", message: `Tool ${toolName} is in the configured deny list` };
			}
		}
		return undefined;
	}
}
