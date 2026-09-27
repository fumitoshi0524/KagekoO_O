import * as fs from "node:fs/promises";
import * as path from "node:path";
import type { Tool, ToolContext } from "../../types.js";
import { searchTreeAccess } from "../../accesses.js";
import { capabilityAccess } from "../../accesses.js";
import { isSensitiveContentPath } from "../../../security/sensitive-path.js";

const TEXT_EXTENSIONS = new Set([
	".js",
	".mjs",
	".cjs",
	".ts",
	".mts",
	".cts",
	".jsx",
	".tsx",
	".py",
	".rs",
	".go",
	".java",
	".md",
	".json",
	".yml",
	".yaml",
	".toml",
]);
const MAX_CONCURRENCY = 5;

interface FileSummary {
	path: string;
	summary: string;
}

export const exploreRepoTool: Tool<{ directory: string; limit?: number; include_sensitive?: boolean }> = {
	name: "explore_repo",
	description:
		"Explore a directory by spawning subagents to summarize its files in parallel, then update the repo index and graph.",
	parameters: {
		type: "object",
		properties: {
			directory: { type: "string", description: "Relative directory path to explore" },
			limit: { type: "number", description: "Maximum files to explore (default 20)" },
			include_sensitive: { type: "boolean", description: "Include sensitive files after explicit approval" },
		},
		required: ["directory"],
	},
	resolveExecution({ directory }) {
		return {
			accesses: [
				...searchTreeAccess(directory),
				...capabilityAccess("delegation", "create", "exploration_subagents"),
				...capabilityAccess("durable_state", "mutate", "repository_index"),
			],
		};
	},
	async execute(
		{
			directory,
			limit = 20,
			include_sensitive = false,
		}: { directory: string; limit?: number; include_sensitive?: boolean },
		context: ToolContext,
	) {
		const { session } = context;
		const parentActivityId = typeof context.parentActivityId === "string" ? context.parentActivityId : undefined;
		const parentToolCallId = typeof context.parentToolCallId === "string" ? context.parentToolCallId : undefined;
		if (!session?.memory) {
			return { output: "Memory engine is not available.", isError: true };
		}
		if (!session?.llm) {
			return { output: "LLM is not available for exploration.", isError: true };
		}
		const subagentHost = session.subagentHost;
		if (!subagentHost) {
			return { output: "Subagent runtime is not available in this session.", isError: true };
		}

		let targetDir: string;
		try {
			targetDir = await session.kaos.resolveReal(directory);
		} catch (err) {
			return { output: `Invalid directory: ${(err as Error).message}`, isError: true };
		}
		const cwd = session.kaos?.cwd ?? session.cwd;
		let files: string[];
		try {
			files = await listTextFiles(targetDir, cwd, include_sensitive);
		} catch (err) {
			return { output: `Could not list directory: ${(err as Error).message}`, isError: true };
		}
		files = files.slice(0, Math.max(1, limit));
		if (files.length === 0) {
			return { output: `No text files found in ${directory}.` };
		}

		const summaries: FileSummary[] = [];
		await runWithConcurrency(files, MAX_CONCURRENCY, async (relPath) => {
			try {
				const result = await subagentHost.run({
					prompt: `Read the file at ${relPath} and summarize its purpose in one concise sentence. Return only the summary.`,
					systemPrompt: "You are a codebase explorer. Be concise.",
					parentActivityId,
					parentToolCallId,
				});
				summaries.push({ path: relPath, summary: String(result.content ?? "").trim() });
			} catch {
				// Ignore individual exploration failures.
			}
		});

		await saveExplorationSummary(session.memory.memoryDir, directory, summaries);

		// Refresh index/graph so the exploration is immediately available.
		await session.memory.indexRepo({ summarize: false });

		return {
			output: `Explored ${summaries.length} files in ${directory}:\n${summaries
				.map((s) => `- ${s.path}: ${s.summary}`)
				.join("\n")}`,
		};
	},
};

async function listTextFiles(dir: string, cwd: string, includeSensitive: boolean): Promise<string[]> {
	const files: string[] = [];
	const queue = [dir];
	const seen = new Set([dir]);
	while (queue.length > 0) {
		const current = queue.shift()!;
		const entries = await fs.readdir(current, { withFileTypes: true });
		for (const entry of entries) {
			if (entry.name === ".kageko" || entry.name === "node_modules" || entry.name === ".git") continue;
			if (entry.isSymbolicLink()) continue;
			const fullPath = path.join(current, entry.name);
			if (!includeSensitive && isSensitiveContentPath(fullPath)) continue;
			if (entry.isDirectory()) {
				const real = await fs.realpath(fullPath).catch(() => fullPath);
				if (!seen.has(real)) {
					seen.add(real);
					queue.push(fullPath);
				}
			} else if (entry.isFile()) {
				const ext = path.extname(entry.name).toLowerCase();
				if (TEXT_EXTENSIONS.has(ext)) {
					files.push(path.relative(cwd, fullPath).replace(/\\/g, "/"));
				}
			}
		}
	}
	return files;
}

async function runWithConcurrency<T>(items: T[], concurrency: number, fn: (item: T) => Promise<void>): Promise<void> {
	if (concurrency <= 0) concurrency = 1;
	return new Promise((resolve, reject) => {
		let index = 0;
		let running = 0;
		let failed = false;
		function next(): void {
			if (failed) return;
			if (index >= items.length) {
				if (running === 0) resolve();
				return;
			}
			const item = items[index++]!;
			running++;
			Promise.resolve(fn(item))
				.then(() => {
					running--;
					next();
				})
				.catch((err) => {
					failed = true;
					reject(err);
				});
			if (running < concurrency) next();
		}
		next();
	});
}

async function saveExplorationSummary(memoryDir: string, directory: string, summaries: FileSummary[]): Promise<void> {
	await fs.mkdir(memoryDir, { recursive: true });
	const filePath = path.join(memoryDir, "exploration.jsonl");
	const entry = {
		directory,
		summaries,
		count: summaries.length,
		createdAt: Date.now(),
	};
	await fs.appendFile(filePath, JSON.stringify(entry) + "\n", "utf-8");
}
