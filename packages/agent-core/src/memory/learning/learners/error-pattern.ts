import { safeStringify } from "../../utils.js";
import type { KnowledgeStore } from "../../knowledge-store.js";
import type { KnowledgeEntry } from "../../types.js";
import type { LearningEvent } from "../event.js";
import type { Learner, TriageDecision } from "../types.js";

export interface ErrorPatternLearnerOptions {
	knowledgeStore: KnowledgeStore;
	/**
	 * Invoked (and awaited) after a new pattern is recorded, so the resident
	 * learner agent can inspect the fresh pattern while the processor batch is
	 * still in flight. Callback failures must not lose the recorded entry.
	 */
	onNewPattern?: (entry: KnowledgeEntry, event: LearningEvent) => void | Promise<void>;
}

/**
 * Learns from recurring tool errors by storing them as runtime knowledge.
 *
 * The {@link LearningTriage} aggregates repeated identical errors and only
 * forwards them once they look like a stable pattern.
 */
export class ErrorPatternLearner implements Learner {
	private readonly knowledgeStore: KnowledgeStore;
	private readonly onNewPattern?: (entry: KnowledgeEntry, event: LearningEvent) => void | Promise<void>;
	private readonly observedPatternKeys = new Set<string>();

	constructor({ knowledgeStore, onNewPattern }: ErrorPatternLearnerOptions) {
		this.knowledgeStore = knowledgeStore;
		this.onNewPattern = onNewPattern;
	}

	async handle(event: LearningEvent, _decision: TriageDecision): Promise<KnowledgeEntry | undefined> {
		const { toolName, result } = event.payload as { toolName: string; result?: unknown };
		const content = this._extractContent(result);
		if (!content) return undefined;

		const title = `Recurring error from ${toolName}`;
		const source = `error:${toolName}`;
		const tags = ["error-pattern", toolName];
		const summary = content.split("\n")[0]?.slice(0, 200) ?? "";

		const entry = await this.knowledgeStore.add({
			source,
			title,
			content,
			summary,
			tags,
		});
		const patternKey = `${toolName}\n${content.slice(0, 500)}`;
		if (this.onNewPattern && !this.observedPatternKeys.has(patternKey)) {
			this.observedPatternKeys.add(patternKey);
			try {
				await this.onNewPattern(entry, event);
			} catch {
				// The recorded pattern is the durable output; a failed observer
				// callback must not convert it into a processor failure.
			}
		}
		return entry;
	}

	private _extractContent(result: unknown): string {
		const r = result as { output?: unknown; content?: unknown } | string | null | undefined;
		if (typeof (r as { output?: unknown })?.output === "string") return (r as { output: string }).output;
		if (typeof (r as { content?: unknown })?.content === "string") return (r as { content: string }).content;
		if (typeof r === "string") return r;
		if (r && typeof r === "object") return safeStringify(r, { pretty: true });
		return "";
	}
}
