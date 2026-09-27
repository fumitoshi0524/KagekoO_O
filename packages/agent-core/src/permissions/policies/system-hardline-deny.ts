import { detectHardline } from "../../security/command-analysis/index.js";
import type { PermissionPolicy, PolicyContext, PolicyResult } from "../types.js";

/** Catastrophic host commands that no permission profile may bypass. */
export class SystemHardlineDenyPolicy implements PermissionPolicy {
	name = "SystemHardlineDeny";

	evaluate(context: PolicyContext): PolicyResult | undefined {
		const { toolName, args, execution } = context;
		if (toolName !== "bash") return undefined;
		const command = getCommand(args);
		if (!command) return undefined;
		const hardline =
			execution?.commandAnalysis?.risk === "hardline"
				? execution.commandAnalysis.hardlineRule
				: detectHardline(command, {
						kind: "local",
						hostReachable: true,
						privileged: false,
						hasHostMounts: false,
						hasCredentials: true,
					});
		if (!hardline) return undefined;
		return {
			kind: "deny",
			message: `Command is blocked by hardline rule ${typeof hardline === "string" ? hardline : hardline.id}: ${
				typeof hardline === "string" ? "catastrophic host command" : hardline.description
			}`,
		};
	}
}

function getCommand(args: unknown): string | undefined {
	if (!args || typeof args !== "object") return undefined;
	const command = (args as Record<string, unknown>)["command"];
	return typeof command === "string" ? command : undefined;
}
