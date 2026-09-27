import type { Tool, ToolContext } from "../../types.js";
import type { GraphNode } from "../../../memory/types.js";

interface QueryGraphArgs {
	path: string;
	mode?: "dependents" | "dependencies" | "related";
	limit?: number;
}

export const queryGraphTool: Tool<QueryGraphArgs> = {
	name: "query_graph",
	description: "Query the code relationship graph: find dependents, dependencies, or related files for a given file.",
	parameters: {
		type: "object",
		properties: {
			path: { type: "string", description: "Relative file path to query" },
			mode: {
				type: "string",
				enum: ["dependents", "dependencies", "related"],
				description: "What to query (default related)",
			},
			limit: { type: "number", description: "Maximum results (default 10)" },
		},
		required: ["path"],
	},
	async execute({ path: filePath, mode = "related", limit = 10 }: QueryGraphArgs, { session }: ToolContext) {
		if (!session?.memory?.graph) {
			return { output: "Graph engine is not available.", isError: true };
		}
		const graph = await session.memory.loadGraph();
		if (graph.nodes.length === 0) {
			return { output: "No code graph available. Run index_repo first.", isError: true };
		}
		const normalizedPath = filePath.replace(/\\/g, "/");
		const hasNode = graph.nodes.some((n: GraphNode) => n.id === normalizedPath);
		if (!hasNode) {
			return { output: `File "${normalizedPath}" is not in the graph.`, isError: true };
		}

		let results: string[] | { id: string; strength: number }[];
		if (mode === "dependents") {
			results = session.memory.graph.dependents(graph, normalizedPath);
		} else if (mode === "dependencies") {
			results = session.memory.graph.dependencies(graph, normalizedPath);
		} else {
			results = session.memory.graph.related(graph, normalizedPath, { limit });
		}

		if (Array.isArray(results) && results.length === 0) {
			return { output: `No ${mode} found for "${normalizedPath}".` };
		}

		let output: string;
		if (mode === "related") {
			output = (results as { id: string; strength: number }[])
				.map((r) => `- ${r.id} (strength ${r.strength})`)
				.join("\n");
		} else {
			output = [...new Set<string>(results as string[])]
				.slice(0, limit)
				.map((id) => `- ${id}`)
				.join("\n");
		}
		return { output };
	},
};
