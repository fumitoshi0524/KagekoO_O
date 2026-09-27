import { matchesEntry } from "./rule-matching.js";
import type { PermissionManagerLike, PermissionPolicy, PolicyContext, PolicyResult } from "../types.js";

export class UserConfiguredAskPermissionPolicy implements PermissionPolicy {
	name = "UserConfiguredAsk";
	permission: PermissionManagerLike;

	constructor(permission: PermissionManagerLike) {
		this.permission = permission;
	}

	evaluate({ toolName, args, execution }: PolicyContext): PolicyResult | undefined {
		for (const entry of this.permission.askList ?? []) {
			if (matchesEntry(toolName, args, execution, this.permission.cwd, entry)) {
				return { kind: "ask", reason: "tool is in the configured ask list", deniedMessage: `User denied ${toolName}` };
			}
		}
		return undefined;
	}
}
