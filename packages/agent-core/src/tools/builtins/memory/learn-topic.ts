import { webSearchTool } from "../web-search.js";
import { fetchUrlTool } from "../fetch-url.js";
import type { Tool, ToolContext } from "../../types.js";
import type { KnowledgeEntry } from "../../../memory/types.js";
import { capabilityAccess, publicNetworkAccess } from "../../accesses.js";

const DEFAULT_TIMEOUT = 30000;

function withTimeout<T>(promise: Promise<T>, ms: number): Promise<T> {
	return new Promise((resolve, reject) => {
		const timer = setTimeout(() => reject(new Error("Operation timed out.")), ms);
		promise.then(resolve, reject).finally(() => clearTimeout(timer));
	});
}

interface LearnTopicArgs {
	topic: string;
	results?: number;
	tags?: string[];
}

export const learnTopicTool: Tool<LearnTopicArgs> = {
	name: "learn_topic",
	description: "Search the web for a topic, summarize the top results, and store them in durable knowledge memory.",
	parameters: {
		type: "object",
		properties: {
			topic: { type: "string", description: "Topic to learn about" },
			results: { type: "number", description: "Number of search results to fetch and learn (default 3, max 5)" },
			tags: {
				type: "array",
				items: { type: "string" },
				description: "Optional tags for the stored knowledge entries",
			},
		},
		required: ["topic"],
	},
	resolveExecution() {
		return {
			accesses: [
				...publicNetworkAccess("search", "https://lite.duckduckgo.com", { sendsContent: true }),
				...capabilityAccess("durable_state", "mutate", "knowledge_memory"),
			],
		};
	},
	async execute({ topic, results = 3, tags }: LearnTopicArgs, { session }: ToolContext) {
		if (!session?.memory) {
			return { output: "Memory engine is not available.", isError: true };
		}
		try {
			const count = Math.min(Math.max(Number(results) || 3, 1), 5);
			const searchResult = await withTimeout(
				Promise.resolve(webSearchTool.execute!({ query: topic, limit: count }, { session })),
				DEFAULT_TIMEOUT,
			);
			if (searchResult.isError) {
				return searchResult;
			}

			const lines = String(searchResult.output)
				.split("\n")
				.filter((line) => line.trim().startsWith("http"));
			const urls = lines.map((line) => line.trim()).slice(0, count);
			if (urls.length === 0) {
				return { output: `No URLs found for topic "${topic}".` };
			}

			const learned: KnowledgeEntry[] = [];
			for (const url of urls) {
				try {
					const fetched = await withTimeout(
						Promise.resolve(fetchUrlTool.execute!({ url, maxLength: 12000 }, { session })),
						DEFAULT_TIMEOUT,
					);
					if (fetched.isError) continue;
					const entry = await session.memory.learn({
						source: url,
						content: fetched.output as string,
						tags: [...(tags ?? []), topic],
					});
					learned.push(entry);
				} catch {
					// Skip individual sources that time out.
				}
			}

			return {
				output: `Learned ${learned.length} sources for "${topic}":\n${learned.map((e) => `- ${e.title} (${e.id})`).join("\n")}`,
			};
		} catch (err) {
			return { output: `Learn topic failed: ${(err as Error).message}`, isError: true };
		}
	},
};
