import type { KnowledgeStore } from "../../knowledge-store.js";
import type { KnowledgeEntry } from "../../types.js";
import type { LearningEvent } from "../event.js";
import type { Learner, TriageDecision } from "../types.js";

export interface PluginLearnerOptions {
	knowledgeStore: KnowledgeStore;
}

/**
 * Learns from plugin command invocations.
 *
 * When a plugin command is run, its rendered prompt body is stored as
 * knowledge so the agent can recall reusable plugin workflows later.
 */
export class PluginLearner implements Learner {
	private readonly knowledgeStore: KnowledgeStore;

	constructor({ knowledgeStore }: PluginLearnerOptions) {
		this.knowledgeStore = knowledgeStore;
	}

	async handle(event: LearningEvent, _decision: TriageDecision): Promise<KnowledgeEntry | undefined> {
		const { kind, pluginId, command, content } = event.payload as {
			kind?: string;
			pluginId?: string;
			command?: string;
			content?: string;
		};
		if (kind !== "command.run") return undefined;
		if (!content) return undefined;

		const title = command ? `Plugin command: ${command}` : "Plugin command output";
		const source = pluginId && command ? `plugin:${pluginId}:${command}` : `plugin:${command ?? "unknown"}`;
		const tags = ["plugin", pluginId, command].filter((t): t is string => Boolean(t));
		const summary = content.split("\n")[0]?.slice(0, 200) ?? "";

		return this.knowledgeStore.add({
			source,
			title,
			content,
			summary,
			tags,
		});
	}
}
