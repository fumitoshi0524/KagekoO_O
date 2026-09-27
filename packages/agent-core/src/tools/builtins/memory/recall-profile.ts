import type { Tool, ToolContext } from "../../types.js";
import type { ProfileEntry } from "../../../memory/types.js";

interface RecallProfileArgs {
	query: string;
	scope?: "user" | "project";
	limit?: number;
}

export const recallProfileTool: Tool<RecallProfileArgs> = {
	name: "recall_profile",
	description: "Recall previously remembered user preferences or project conventions.",
	parameters: {
		type: "object",
		properties: {
			query: { type: "string", description: "What to recall" },
			scope: {
				type: "string",
				enum: ["user", "project"],
				description: "Limit recall to user or project scope",
			},
			limit: { type: "number", description: "Maximum results (default 5)" },
		},
		required: ["query"],
	},
	async execute({ query, scope, limit = 5 }: RecallProfileArgs, { session }: ToolContext) {
		if (!session?.memory?.profile) {
			return { output: "Memory engine is not available.", isError: true };
		}
		const results = await session.memory.recall(query, { scope, limit });
		if (results.length === 0) {
			return { output: "No remembered facts matched." };
		}
		const lines = results.map((r: ProfileEntry) => `[${r.scope}] ${r.fact}`);
		return { output: lines.join("\n") };
	},
};
