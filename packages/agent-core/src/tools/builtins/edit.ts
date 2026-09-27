import { isKaosError } from "../../ports/workspace.js";
import { readWriteFileAccess, literalApprovalRule, matchesRuleSubject } from "../accesses.js";
import { createFileChangeEvent } from "../../memory/learning/event.js";
import type { Tool, ToolContext } from "../types.js";

export const editTool: Tool = {
	name: "edit",
	description: "Replace one exact string with another in a file.",
	parameters: {
		type: "object",
		properties: {
			path: { type: "string", description: "Relative or absolute file path" },
			oldString: { type: "string", description: "Exact text to replace" },
			newString: { type: "string", description: "Replacement text" },
		},
		required: ["path", "oldString", "newString"],
	},
	resolveExecution(args: Record<string, unknown>) {
		const { path } = args as { path: string };
		return {
			accesses: readWriteFileAccess(path),
			approvalRule: literalApprovalRule("edit", path),
			matchesRule: (ruleArgs) => matchesRuleSubject(ruleArgs, path),
			execute: this.execute,
		};
	},
	async execute(args: Record<string, unknown>, context: ToolContext) {
		const { path, oldString, newString } = args as { path: string; oldString: string; newString: string };
		const { kaos, session } = context;
		if (!kaos) {
			return { output: "Workspace filesystem is not available.", isError: true };
		}
		if (oldString.length === 0) {
			return { output: "oldString must not be empty", isError: true };
		}
		let content: string;
		try {
			content = await kaos.readText(path);
		} catch (err) {
			if (isKaosError(err, "FileTooLargeError") || isKaosError(err, "PathSecurityError")) {
				return { output: (err as Error).message, isError: true };
			}
			throw err;
		}
		const firstMatch = content.indexOf(oldString);
		if (firstMatch === -1) {
			return { output: "oldString not found", isError: true };
		}
		if (content.indexOf(oldString, firstMatch + oldString.length) !== -1) {
			return { output: "oldString is not unique; provide more surrounding context", isError: true };
		}
		const updated = content.slice(0, firstMatch) + newString + content.slice(firstMatch + oldString.length);
		try {
			await kaos.writeText(path, updated);
		} catch (err) {
			if (isKaosError(err, "FileTooLargeError") || isKaosError(err, "PathSecurityError")) {
				return { output: (err as Error).message, isError: true };
			}
			throw err;
		}
		session?.learningBus?.enqueue(createFileChangeEvent(path, "edit", { toolName: "edit" }));
		return { output: `Edited ${path}` };
	},
};
