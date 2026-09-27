import type { Tool, ToolContext } from "../types.js";
import { fileAccess } from "../accesses.js";

const MAX_LS_ENTRIES = 10_000;

export const lsTool: Tool<{ path?: string }> = {
	name: "ls",
	description: "List the contents of a directory.",
	parameters: {
		type: "object",
		properties: {
			path: { type: "string", description: "Directory path; defaults to current directory" },
		},
	},
	resolveExecution({ path = "." }) {
		return { accesses: fileAccess("read", path) };
	},
	async execute({ path = "." }: { path?: string }, { kaos }: ToolContext) {
		if (!kaos) return { output: "Workspace filesystem is not available.", isError: true };
		let entries;
		try {
			entries = await kaos.readdir(path);
		} catch (error) {
			return { output: `Failed to list directory: ${(error as Error).message}`, isError: true };
		}
		const capped = entries.slice(0, MAX_LS_ENTRIES);
		const lines = capped.map((e) => `${e.isDirectory() ? "d" : "-"} ${e.name}`);
		if (entries.length > capped.length) lines.push(`[entries truncated at ${MAX_LS_ENTRIES}]`);
		return { output: lines.join("\n") };
	},
};
