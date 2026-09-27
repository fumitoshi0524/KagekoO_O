import type { Tool, ToolContext } from "../../types.js";
import { capabilityAccess, readFileAccess } from "../../accesses.js";

const DEFAULT_TIMEOUT = 30000;

function withTimeout<T>(promise: Promise<T>, ms: number): Promise<T> {
	return new Promise((resolve, reject) => {
		const timer = setTimeout(() => reject(new Error("Operation timed out.")), ms);
		promise.then(resolve, reject).finally(() => clearTimeout(timer));
	});
}

export const summarizeFileTool: Tool<{ path: string }> = {
	name: "summarize_file",
	description: "Generate or refresh a one-sentence summary for a single file and update the repository index.",
	parameters: {
		type: "object",
		properties: {
			path: { type: "string", description: "Relative path to the file" },
		},
		required: ["path"],
	},
	resolveExecution({ path: filePath }) {
		return {
			accesses: [...readFileAccess(filePath), ...capabilityAccess("durable_state", "mutate", "repository_index")],
		};
	},
	async execute({ path: filePath }: { path: string }, { kaos, session }: ToolContext) {
		if (!session?.memory?.indexer) {
			return { output: "Memory engine is not available.", isError: true };
		}
		let content: string;
		try {
			content = await kaos!.readText(filePath);
		} catch (err) {
			return { output: `Could not read file: ${(err as Error).message}`, isError: true };
		}
		try {
			const summary = await withTimeout(session.memory.indexer.summarize(content, filePath, "text"), DEFAULT_TIMEOUT);
			return {
				output: summary || "Could not generate summary.",
			};
		} catch (err) {
			return { output: `Summarize failed: ${(err as Error).message}`, isError: true };
		}
	},
};
