import { fetchUrlTool } from "../fetch-url.js";
import type { Tool, ToolContext } from "../../types.js";
import { capabilityAccess, publicNetworkAccess } from "../../accesses.js";

const DEFAULT_TIMEOUT = 30000;

export const learnUrlTool: Tool<{ url: string; title?: string; tags?: string[] }> = {
	name: "learn_url",
	description: "Fetch a URL, summarize it, and store the result in durable knowledge memory for later queries.",
	parameters: {
		type: "object",
		properties: {
			url: { type: "string", description: "URL to learn from" },
			title: { type: "string", description: "Optional title for the knowledge entry" },
			tags: {
				type: "array",
				items: { type: "string" },
				description: "Optional tags",
			},
		},
		required: ["url"],
	},
	resolveExecution({ url }) {
		return {
			accesses: [
				...publicNetworkAccess("fetch", url),
				...capabilityAccess("durable_state", "mutate", "knowledge_memory"),
			],
		};
	},
	async execute({ url, title, tags }: { url: string; title?: string; tags?: string[] }, { session }: ToolContext) {
		if (!session?.memory) {
			return { output: "Memory engine is not available.", isError: true };
		}
		try {
			const fetched = await withTimeout(
				Promise.resolve(fetchUrlTool.execute!({ url, maxLength: 12000 }, { session })),
				DEFAULT_TIMEOUT,
			);
			if (fetched.isError) {
				return fetched;
			}
			const entry = await session.memory.learn({
				source: url,
				title,
				content: fetched.output as string,
				tags,
			});
			return {
				output: `Learned "${entry.title}" (${entry.id}). Summary: ${entry.summary}`,
			};
		} catch (err) {
			return { output: `Learn URL failed: ${(err as Error).message}`, isError: true };
		}
	},
};

function withTimeout<T>(promise: Promise<T>, ms: number): Promise<T> {
	return new Promise((resolve, reject) => {
		const timer = setTimeout(() => reject(new Error("Operation timed out.")), ms);
		promise.then(resolve, reject).finally(() => clearTimeout(timer));
	});
}
