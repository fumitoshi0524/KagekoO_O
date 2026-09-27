import { isKaosError } from "../../ports/workspace.js";
import { writeFileAccess, literalApprovalRule, matchesRuleSubject } from "../accesses.js";
import { createFileChangeEvent } from "../../memory/learning/event.js";
import type { Tool, ToolContext } from "../types.js";

export const writeTool: Tool = {
	name: "write",
	description: "Write text to a file, creating parent directories if needed.",
	parameters: {
		type: "object",
		properties: {
			path: { type: "string", description: "Relative or absolute file path" },
			content: { type: "string", description: "Full file content" },
		},
		required: ["path", "content"],
	},
	resolveExecution(args: Record<string, unknown>) {
		const { path } = args as { path: string };
		return {
			accesses: writeFileAccess(path),
			approvalRule: literalApprovalRule("write", path),
			matchesRule: (ruleArgs) => matchesRuleSubject(ruleArgs, path),
			execute: this.execute,
		};
	},
	async execute(args: Record<string, unknown>, context: ToolContext) {
		const { path, content } = args as { path: string; content: string };
		const { kaos, session } = context;
		if (!kaos) {
			throw new Error("kaos is not available in tool context");
		}
		try {
			await kaos.writeText(path, content);
		} catch (err) {
			if (isKaosError(err, "FileTooLargeError") || isKaosError(err, "PathSecurityError")) {
				return { output: err.message, isError: true };
			}
			throw err;
		}
		session?.learningBus?.enqueue(createFileChangeEvent(path, "write", { toolName: "write" }));
		return { output: `Wrote ${path}` };
	},
};
