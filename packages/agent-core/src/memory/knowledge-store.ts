import * as fs from "node:fs/promises";
import * as path from "node:path";
import * as crypto from "node:crypto";
import { tokenize, fingerprint, readJsonlLines, ensureJsonlSizeCap } from "./utils.js";
import type { KnowledgeEntry, LlmClient } from "./types.js";

const MAX_KNOWLEDGE_JSONL_BYTES = 128 * 1024 * 1024;
const MAX_ENTRY_CONTENT_CHARS = 1024 * 1024;

export interface KnowledgeStoreOptions {
	kagekoDir: string;
	llm?: LlmClient;
}

export interface AddKnowledgeInput {
	source: string;
	title?: string;
	content?: string;
	summary?: string;
	tags?: string[];
}

/**
 * Append-only knowledge store for external facts with deduplication.
 *
 * Entries are persisted as JSONL at `~/.kageko/memory/knowledge.jsonl`.
 * Retrieval uses simple keyword/term-frequency scoring (plain TF — no IDF,
 * no embeddings) so the system stays dependency-free.
 */
export class KnowledgeStore {
	readonly kagekoDir: string;
	readonly llm?: LlmClient;
	readonly storePath: string;
	private _lock: Promise<unknown> = Promise.resolve();

	constructor({ kagekoDir, llm }: KnowledgeStoreOptions) {
		this.kagekoDir = kagekoDir;
		this.llm = llm;
		this.storePath = path.join(kagekoDir, "memory", "knowledge.jsonl");
	}

	private _runLocked<T>(fn: () => Promise<T>): Promise<T> {
		const result = this._lock.then(() => fn());
		this._lock = result.catch(() => {});
		return result;
	}

	async add({ source, title = "", content, summary, tags = [] }: AddKnowledgeInput): Promise<KnowledgeEntry> {
		// Compute the LLM summary outside the lock so slow LLM calls do not block
		// concurrent add/dedupe operations.
		if (!summary && content && this.llm) {
			summary = await this.summarizeWithTimeout(content);
		}

		return this._runLocked(async () => {
			await fs.mkdir(path.dirname(this.storePath), { recursive: true });
			await ensureJsonlSizeCap(this.storePath, MAX_KNOWLEDGE_JSONL_BYTES);

			const normalizedTitle = title || source;
			const normalizedSummary = summary || firstParagraph(content) || "";
			const print = [normalizedTitle, normalizedSummary, (content || "").slice(0, 500)].join("\n");
			const fp = fingerprint(print);

			const entries = await this.list();
			const existing = entries.find((e) => e._fp === fp);
			if (existing) {
				const updated: KnowledgeEntry = {
					...existing,
					source,
					title: normalizedTitle,
					summary: normalizedSummary,
					content: content || "",
					tags: Array.isArray(tags) ? tags : [],
					updatedAt: Date.now(),
				};
				const idx = entries.indexOf(existing);
				entries[idx] = updated;
				await this.writeEntries(entries);
				return updated;
			}

			const entry: KnowledgeEntry = {
				id: crypto.randomUUID(),
				source,
				title: normalizedTitle,
				summary: normalizedSummary,
				content: content || "",
				tags: Array.isArray(tags) ? tags : [],
				createdAt: Date.now(),
				updatedAt: Date.now(),
				_fp: fp,
			};

			entries.push(entry);
			await this.writeEntries(entries);
			return entry;
		});
	}

	async list(): Promise<KnowledgeEntry[]> {
		const entries = await readJsonlLines<KnowledgeEntry>(this.storePath);
		return entries.map((e) => ({ ...e }));
	}

	async dedupe(): Promise<{ removed: number; kept: number }> {
		return this._runLocked(async () => {
			const entries = await this.list();
			const seen = new Map<string, KnowledgeEntry>();
			const kept: KnowledgeEntry[] = [];
			for (const entry of entries) {
				const fp = entry._fp ?? fingerprint([entry.title, entry.summary, entry.content.slice(0, 500)].join("\n"));
				const older = seen.get(fp);
				if (older) {
					// Keep the newer one, merging tags.
					const chosen = entry.updatedAt > (older.updatedAt ?? 0) ? entry : older;
					const merged: KnowledgeEntry = {
						...chosen,
						tags: [...new Set([...(older.tags ?? []), ...(entry.tags ?? [])])],
					};
					seen.set(fp, merged);
				} else {
					entry._fp = fp;
					seen.set(fp, { ...entry });
				}
			}
			for (const entry of seen.values()) {
				kept.push(entry);
			}
			kept.sort((a, b) => (b.updatedAt ?? b.createdAt) - (a.updatedAt ?? a.createdAt));
			await this.writeEntries(kept);
			return { removed: entries.length - kept.length, kept: kept.length };
		});
	}

	async writeEntries(entries: KnowledgeEntry[]): Promise<void> {
		const cappedEntries = entries.map((e) => {
			if (!e.content || e.content.length <= MAX_ENTRY_CONTENT_CHARS) return e;
			return { ...e, content: e.content.slice(0, MAX_ENTRY_CONTENT_CHARS) };
		});
		const lines = cappedEntries.map((e) => JSON.stringify(e)).join("\n") + (cappedEntries.length > 0 ? "\n" : "");
		if (Buffer.byteLength(lines, "utf8") > MAX_KNOWLEDGE_JSONL_BYTES) {
			throw new Error(`KnowledgeStore write would exceed the ${MAX_KNOWLEDGE_JSONL_BYTES} byte cap`);
		}
		await writeFileAtomic(this.storePath, lines);
	}

	async search(query: string, { limit = 5 }: { limit?: number } = {}): Promise<KnowledgeEntry[]> {
		const entries = await this.list();
		if (entries.length === 0) return [];
		const terms = tokenize(query);
		const scored = entries
			.map((entry) => ({
				entry,
				score: scoreEntry(entry, terms),
			}))
			.filter((s) => s.score > 0)
			.sort((a, b) => b.score - a.score)
			.slice(0, limit);
		return scored.map((s) => s.entry);
	}

	async summarizeWithTimeout(content: string, timeoutMs = 30000): Promise<string | undefined> {
		if (!this.llm) return undefined;
		const prompt = `Summarize the following text in one concise sentence:\n\n${content.slice(0, 4000)}`;
		try {
			const response = await withTimeout(
				this.llm.chat({ messages: [{ role: "user", content: prompt }], tools: [] }),
				timeoutMs,
			);
			const text = response.content?.trim();
			if (text && text.length > 5 && !text.toLowerCase().includes("don't know")) {
				return text;
			}
		} catch {
			// Ignore.
		}
		return undefined;
	}
}

async function writeFileAtomic(filePath: string, data: string): Promise<void> {
	const tmpPath = `${filePath}.tmp`;
	await fs.writeFile(tmpPath, data, "utf-8");
	await fs.rename(tmpPath, filePath);
}

function withTimeout<T>(promise: Promise<T>, ms: number): Promise<T> {
	return new Promise((resolve, reject) => {
		const timer = setTimeout(() => reject(new Error("Knowledge summary timed out.")), ms);
		promise.then(resolve, reject).finally(() => clearTimeout(timer));
	});
}

function scoreEntry(entry: KnowledgeEntry, terms: string[]): number {
	const haystack = [entry.title, entry.summary, entry.content, entry.tags.join(" ")].join(" ");
	const hayTokens = tokenize(haystack);
	const freq: Record<string, number> = {};
	for (const t of hayTokens) {
		freq[t] = (freq[t] ?? 0) + 1;
	}
	let score = 0;
	for (const term of terms) {
		if (freq[term]) {
			score += freq[term] as number;
		}
	}
	return score;
}

function firstParagraph(text?: string): string | undefined {
	if (!text) return undefined;
	const paragraph = text.split(/\n\s*\n/)[0]?.trim();
	if (!paragraph) return undefined;
	return paragraph.length > 240 ? `${paragraph.slice(0, 239)}…` : paragraph;
}
