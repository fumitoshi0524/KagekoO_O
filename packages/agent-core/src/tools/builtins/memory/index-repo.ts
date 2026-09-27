import type { Tool, ToolContext } from "../../types.js";

export const indexRepoTool: Tool<{ summarize?: boolean; include_sensitive?: boolean }> = {
	name: "index_repo",
	description:
		"Index the current project repository for later querying. Builds a local file/symbol/summary index in .kageko/memory.",
	parameters: {
		type: "object",
		properties: {
			summarize: {
				type: "boolean",
				description: "Whether to generate per-file summaries with the LLM (default true).",
			},
			include_sensitive: { type: "boolean", description: "Include sensitive files after explicit approval" },
		},
	},
	async execute(
		{ summarize = true, include_sensitive = false }: { summarize?: boolean; include_sensitive?: boolean },
		{ session }: ToolContext,
	) {
		if (!session?.memory) {
			return { output: "Memory engine is not available.", isError: true };
		}
		const result = await session.memory.indexRepo({ summarize, includeSensitive: include_sensitive });
		return {
			output: [
				`Indexed ${result.indexed} files.`,
				`Unchanged skipped: ${result.unchanged}`,
				`Ignored: ${result.ignored}`,
				`Errors: ${result.errors}`,
				"By language:",
				...Object.entries(result.byLanguage).map(([lang, count]) => `  ${lang}: ${count}`),
			].join("\n"),
		};
	},
};
