import { RepoIndexer, type IndexOptions, type IndexResult } from "./repo-indexer.js";
import { KnowledgeStore, type AddKnowledgeInput } from "./knowledge-store.js";
import { MemoryQuery, type QueryOptions, type MemoryQueryResponse } from "./query.js";
import { SkillSynthesizer } from "./skill-synthesizer.js";
import { ProfileMemory, type RecallOptions } from "./profile-memory.js";
import { GraphBuilder } from "./graph-builder.js";
import type {
	KnowledgeEntry,
	LlmClient,
	ProfileEntry,
	ProfileScope,
	RepoGraph,
	SessionEvent,
	SynthesizedSkill,
} from "./types.js";

export interface MemoryEngineOptions {
	cwd: string;
	/** User-level Kageko directory (profile/knowledge), injected by the composition root. */
	kagekoDir: string;
	/** Project-level memory directory (repo index, graph, conventions), injected by the composition root. */
	projectMemoryDir: string;
	/** Directory for auto-generated skills, injected by the composition root. */
	autoSkillDir: string;
	llm?: LlmClient;
	/** Receives non-fatal diagnostics (e.g. a corrupt persisted graph that was rebuilt). */
	onDiagnostic?: (message: string, error?: unknown) => void | Promise<void>;
}

export interface GenerateSkillResult extends SynthesizedSkill {
	filePath: string;
}

/**
 * Unified memory engine for Kageko.
 *
 * Combines repository indexing, external knowledge, skill synthesis,
 * cross-session profile memory, and code graph reasoning into one local,
 * dependency-free system.
 */
export class MemoryEngine {
	readonly cwd: string;
	readonly kagekoDir: string;
	readonly llm?: LlmClient;
	readonly memoryDir: string;
	readonly indexer: RepoIndexer;
	readonly knowledge: KnowledgeStore;
	readonly query: MemoryQuery;
	readonly synthesizer: SkillSynthesizer;
	readonly profile: ProfileMemory;
	readonly graph: GraphBuilder;

	constructor({ cwd, kagekoDir, projectMemoryDir, autoSkillDir, llm, onDiagnostic }: MemoryEngineOptions) {
		this.cwd = cwd;
		this.kagekoDir = kagekoDir;
		this.llm = llm;
		this.memoryDir = projectMemoryDir;
		this.indexer = new RepoIndexer({ cwd, memoryDir: this.memoryDir, llm });
		this.knowledge = new KnowledgeStore({ kagekoDir, llm });
		this.query = new MemoryQuery({ cwd, kagekoDir, projectMemoryDir, llm });
		this.synthesizer = new SkillSynthesizer({ cwd, autoSkillDir, llm });
		this.profile = new ProfileMemory({ kagekoDir, projectMemoryDir });
		this.graph = new GraphBuilder({ cwd, memoryDir: this.memoryDir, onDiagnostic });
	}

	async indexRepo(options?: IndexOptions): Promise<IndexResult> {
		const result = await this.indexer.index(options);
		const entries = [...(await this.indexer.loadExisting()).values()];
		await this.graph.build(entries);
		return result;
	}

	async learn(input: AddKnowledgeInput): Promise<KnowledgeEntry> {
		return this.knowledge.add(input);
	}

	async ask(question: string, options?: QueryOptions): Promise<MemoryQueryResponse> {
		return this.query.query(question, options);
	}

	async generateSkill(events: SessionEvent[], options?: { name?: string }): Promise<GenerateSkillResult | undefined> {
		const skill = await this.synthesizer.synthesize(events, options);
		if (!skill) return undefined;
		const filePath = await this.synthesizer.writeSkill(skill);
		return { ...skill, filePath };
	}

	async remember(scope: ProfileScope | string, fact: string): Promise<ProfileEntry> {
		return this.profile.remember(scope, fact);
	}

	async recall(query: string, options?: RecallOptions): Promise<ProfileEntry[]> {
		return this.profile.recall(query, options);
	}

	async profileSystemPrompt(): Promise<string> {
		return this.profile.formatForSystemPrompt();
	}

	async loadGraph(): Promise<RepoGraph> {
		return this.graph.load();
	}

	async summarizeSession(events: SessionEvent[]): Promise<string | undefined> {
		if (!this.llm || events.length === 0) {
			return undefined;
		}
		const transcript = events
			.map((e) => {
				if (e.type === "user.prompt" && (e.data.origin === undefined || e.data.origin === "user"))
					return `User: ${e.data.content}`;
				if (e.type === "assistant.text") return `Assistant: ${e.data.content}`;
				if (e.type === "tool.call") return `Tool: ${e.data.call.name}`;
				return "";
			})
			.filter(Boolean)
			.join("\n");
		const prompt = `Summarize the following coding-agent session in 1-2 concise sentences. Focus on what was done, decided, or learned.\n\n${transcript.slice(0, 6000)}`;
		const abortController = new AbortController();
		try {
			const response = await withTimeout(
				this.llm.chat({ messages: [{ role: "user", content: prompt }], tools: [], signal: abortController.signal }),
				10_000,
				abortController,
			);
			const text = response.content?.trim();
			if (text && text.length > 5) return text;
		} catch {
			// Ignore.
		}
		return undefined;
	}
}

function withTimeout<T>(promise: Promise<T>, ms: number, abortController?: AbortController): Promise<T> {
	let timer: ReturnType<typeof setTimeout> | undefined;
	const timeout = new Promise<never>((_, reject) => {
		timer = setTimeout(() => {
			abortController?.abort(new Error("summarize session timeout"));
			reject(new Error("summarize session timeout"));
		}, ms);
	});
	const clearTimer = () => clearTimeout(timer);
	promise.then(clearTimer).catch(clearTimer);
	return Promise.race([promise, timeout]);
}
