import type { PermissionManagerLike, PermissionPolicy, PolicyContext, PolicyResult } from "../types.js";

export class SessionApprovalHistoryPolicy implements PermissionPolicy {
	name = "SessionApprovalHistory";
	permission: PermissionManagerLike;

	constructor(permission: PermissionManagerLike) {
		this.permission = permission;
	}

	evaluate({ toolName, args, execution }: PolicyContext): PolicyResult | undefined {
		if (execution?.approvalRule) {
			if (typeof execution.matchesRule === "function") {
				for (const key of this.permission.history.keys()) {
					if (!key.startsWith(`${toolName}:`)) continue;
					const ruleString = key.slice(`${toolName}:`.length);
					const ruleArgs = parseRuleArgs(ruleString);
					try {
						if (execution.matchesRule(ruleArgs) === true) {
							return { kind: "approve", reason: "previously approved this session" };
						}
					} catch {
						// Matcher failure is not a decision; continue checking other keys.
					}
				}
				return undefined;
			}
			if (this.permission.history.get(`${toolName}:${execution.approvalRule}`) === true) {
				return { kind: "approve", reason: "previously approved this session" };
			}
			return undefined;
		}

		let key: string;
		try {
			key = this.permission.historyKey(toolName, args);
		} catch {
			// Circular or otherwise non-serializable args can't be history-matched.
			return undefined;
		}
		if (this.permission.history.get(key) === true) {
			return { kind: "approve", reason: "previously approved this session" };
		}
		return undefined;
	}
}

function parseRuleArgs(ruleString: string): string {
	if (typeof ruleString !== "string") return ruleString;
	const open = ruleString.indexOf("(");
	if (open === -1) return ruleString;
	if (!ruleString.endsWith(")")) return ruleString.slice(open + 1);
	return ruleString.slice(open + 1, -1);
}
