import type { Tool, ToolContext } from "../../types.js";

interface QueryMemoryArgs {
	question: string;
	limit?: number;
	synthesize?: boolean;
}

export const queryMemoryTool: Tool<QueryMemoryArgs> = {
	name: "query_memory",
	description: "Ask a natural-language question over the indexed repository and learned external knowledge.",
	parameters: {
		type: "object",
		properties: {
			question: { type: "string", description: "Question to answer" },
			limit: { type: "number", description: "Maximum number of sources to retrieve (default 8)" },
			synthesize: { type: "boolean", description: "Whether to synthesize an answer with the LLM (default true)" },
		},
		required: ["question"],
	},
	async execute({ question, limit = 8, synthesize = true }: QueryMemoryArgs, { session }: ToolContext) {
		if (!session?.memory) {
			return { output: "Memory engine is not available.", isError: true };
		}
		const result = await session.memory.ask(question, { limit, synthesize });
		const sourceLines: string[] = [];
		for (const s of result.sources) {
			if (s.type === "repo") {
				sourceLines.push(`${sourceLines.length + 1}. [repo] ${s.path} — ${s.summary}`);
				for (const chunk of s.chunks ?? []) {
					const preview = chunk.content.split("\n").slice(0, 6).join("\n");
					sourceLines.push(
						`   chunk [${chunk.name}]:\n${preview
							.split("\n")
							.map((l: string) => "      " + l)
							.join("\n")}`,
					);
				}
			} else {
				sourceLines.push(`${sourceLines.length + 1}. [knowledge] ${s.title || s.source} — ${s.summary}`);
			}
		}
		const parts = ["Sources:"];
		if (sourceLines.length === 0) {
			parts.push("  No relevant sources found.");
		} else {
			parts.push(...sourceLines);
		}
		if (result.answer) {
			parts.push("", `Answer: ${result.answer}`);
		}
		return { output: parts.join("\n") };
	},
};
