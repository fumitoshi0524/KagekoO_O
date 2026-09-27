import { safeStringify } from "../../utils.js";
import type { KnowledgeStore } from "../../knowledge-store.js";
import type { KnowledgeEntry } from "../../types.js";
import type { LearningEvent } from "../event.js";
import type { Learner, TriageDecision } from "../types.js";

export interface McpLearnerOptions {
	knowledgeStore: KnowledgeStore;
}

/**
 * Learns from MCP tool invocations.
 *
 * Stores useful MCP outputs as knowledge tagged by server and tool so the
 * agent can later recall which external capabilities it has used.
 */
export class McpLearner implements Learner {
	private readonly knowledgeStore: KnowledgeStore;

	constructor({ knowledgeStore }: McpLearnerOptions) {
		this.knowledgeStore = knowledgeStore;
	}

	async handle(event: LearningEvent, _decision: TriageDecision): Promise<KnowledgeEntry | undefined> {
		const {
			toolName,
			arguments: args,
			result,
		} = event.payload as {
			toolName: string;
			arguments?: Record<string, unknown>;
			result?: unknown;
		};
		const content = this._extractContent(result);
		if (!content) return undefined;

		const { server, tool } = parseMcpToolName(toolName);
		const title = this._buildTitle(server, tool, args);
		const source = `mcp:${server}:${tool}`;
		const tags = ["mcp", server, tool];
		const summary = content.split("\n")[0]?.slice(0, 200) ?? "";

		return this.knowledgeStore.add({
			source,
			title,
			content,
			summary,
			tags,
		});
	}

	private _extractContent(result: unknown): string {
		const r = result as { output?: unknown; content?: unknown } | string | null | undefined;
		if (typeof (r as { output?: unknown })?.output === "string") return (r as { output: string }).output;
		if (typeof (r as { content?: unknown })?.content === "string") return (r as { content: string }).content;
		if (typeof r === "string") return r;
		if (r && typeof r === "object") return safeStringify(r, { pretty: true });
		return "";
	}

	private _buildTitle(server: string, tool: string, args?: Record<string, unknown>): string {
		if (!args || typeof args !== "object") return `${server}/${tool}`;
		const keys = Object.keys(args);
		if (keys.length === 0) return `${server}/${tool}`;
		return `${server}/${tool} (${keys.join(", ")})`;
	}
}

function parseMcpToolName(toolName: string): { server: string; tool: string } {
	const parts = String(toolName).split("__");
	if (parts.length >= 3 && parts[0] === "mcp") {
		return { server: parts[1] as string, tool: parts.slice(2).join("__") };
	}
	return { server: "unknown", tool: toolName };
}
