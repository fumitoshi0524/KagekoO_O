import { isKaosError } from "../../ports/workspace.js";
import { readFileAccess, literalApprovalRule, matchesRuleSubject } from "../accesses.js";
import type { Tool, ToolContext } from "../types.js";

export const readTool: Tool = {
	name: "read",
	description: "Read the contents of a text file.",
	parameters: {
		type: "object",
		properties: {
			path: { type: "string", description: "Relative or absolute file path" },
		},
		required: ["path"],
	},
	resolveExecution(args: Record<string, unknown>) {
		const { path } = args as { path: string };
		return {
			accesses: readFileAccess(path),
			approvalRule: literalApprovalRule("read", path),
			matchesRule: (ruleArgs) => matchesRuleSubject(ruleArgs, path),
			execute: this.execute,
		};
	},
	async execute(args: Record<string, unknown>, context: ToolContext) {
		const { path } = args as { path: string };
		const { kaos } = context;
		if (!kaos) {
			throw new Error("kaos is not available in tool context");
		}
		try {
			return { output: await kaos.readText(path) };
		} catch (err) {
			if (isKaosError(err, "FileTooLargeError")) {
				return { output: err.message, isError: true };
			}
			if (isKaosError(err, "PathSecurityError")) {
				return { output: err.message, isError: true };
			}
			throw err;
		}
	},
};
