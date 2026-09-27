import { safeStringify } from "../../utils.js";
import type { KnowledgeStore } from "../../knowledge-store.js";
import type { KnowledgeEntry } from "../../types.js";
import type { LearningEvent } from "../event.js";
import type { Learner, TriageDecision } from "../types.js";

export interface ToolResultLearnerOptions {
	knowledgeStore: KnowledgeStore;
}

interface NormalizedKnowledge {
	source: string;
	title: string;
	content: string;
	tags: string[];
}

/**
 * Learns from valuable tool results by storing them in the KnowledgeStore.
 */
export class ToolResultLearner implements Learner {
	private readonly knowledgeStore: KnowledgeStore;

	constructor({ knowledgeStore }: ToolResultLearnerOptions) {
		this.knowledgeStore = knowledgeStore;
	}

	async handle(event: LearningEvent, _decision: TriageDecision): Promise<KnowledgeEntry | undefined> {
		const { source, title, content, tags } = this._normalize(event);
		if (!content) return undefined;

		const summary = content.split("\n")[0]?.slice(0, 200) ?? "";
		return this.knowledgeStore.add({
			source,
			title,
			content,
			summary,
			tags,
		});
	}

	private _normalize(event: LearningEvent): NormalizedKnowledge {
		if (event.source === "external_fetch") {
			const { kind, url, topic, title, content } = event.payload as {
				kind?: string;
				url?: string;
				topic?: string;
				title?: string;
				content?: unknown;
			};
			const text = typeof content === "string" ? content : safeStringify(content ?? "");
			return {
				source: url ?? topic ?? `external:${kind}`,
				title: title ?? (url ? `Fetched ${url}` : (topic ?? `External ${kind}`)),
				content: text,
				tags: ["external-fetch", kind].filter((t): t is string => Boolean(t)),
			};
		}

		const {
			toolName,
			arguments: args,
			result,
		} = event.payload as {
			toolName: string;
			arguments?: Record<string, unknown>;
			result?: unknown;
		};
		return {
			source: `tool:${toolName}`,
			title: this._buildTitle(toolName, args),
			content: this._extractContent(result),
			tags: ["auto-learned", toolName],
		};
	}

	private _extractContent(result: unknown): string {
		const r = result as { output?: unknown; content?: unknown } | string | null | undefined;
		if (typeof (r as { output?: unknown })?.output === "string") return (r as { output: string }).output;
		if (typeof (r as { content?: unknown })?.content === "string") return (r as { content: string }).content;
		if (typeof r === "string") return r;
		if (r && typeof r === "object") return safeStringify(r, { pretty: true });
		return "";
	}

	private _buildTitle(toolName: string, args?: Record<string, unknown>): string {
		if (!args || typeof args !== "object") return `Result from ${toolName}`;
		const keys = Object.keys(args);
		if (keys.length === 0) return `Result from ${toolName}`;
		return `Result from ${toolName} (${keys.join(", ")})`;
	}
}
