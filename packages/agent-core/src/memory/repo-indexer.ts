import * as fs from "node:fs/promises";
import * as path from "node:path";
import * as crypto from "node:crypto";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { mapConcurrent, readJsonlLines } from "./utils.js";
import { compileGlobRegex, globToRegex } from "../utils/regex-safe.js";
import type { LlmClient, RepoChunk, RepoIndexEntry, RepoSymbol } from "./types.js";
import { isSensitiveContentPath } from "../security/sensitive-path.js";

const execFileAsync = promisify(execFile);
const GIT_TIMEOUT_MS = 10_000;
const SUMMARY_TIMEOUT_MS = 10_000;

const TEXT_EXTENSIONS = new Set([
	".js",
	".mjs",
	".cjs",
	".ts",
	".mts",
	".cts",
	".jsx",
	".tsx",
	".json",
	".jsonc",
	".md",
	".yml",
	".yaml",
	".py",
	".rs",
	".go",
	".java",
	".kt",
	".swift",
	".c",
	".cpp",
	".h",
	".hpp",
	".cs",
	".rb",
	".php",
	".sh",
	".bash",
	".zsh",
	".ps1",
	".html",
	".css",
	".scss",
	".sass",
	".less",
	".xml",
	".toml",
	".ini",
	".cfg",
	".txt",
	".log",
	".sql",
	".graphql",
]);

const ALWAYS_IGNORE_DIRS = new Set([
	"node_modules",
	".git",
	".github",
	".kageko",
	".venv",
	"venv",
	"__pycache__",
	".pytest_cache",
	".ruff_cache",
	".mypy_cache",
	"dist",
	"build",
	"out",
	"target",
	"coverage",
	".next",
	".nuxt",
	".turbo",
	".parcel-cache",
	".cache",
]);

const LANGUAGE_BY_EXT: Record<string, string> = {
	".js": "javascript",
	".mjs": "javascript",
	".cjs": "javascript",
	".ts": "typescript",
	".mts": "typescript",
	".cts": "typescript",
	".jsx": "jsx",
	".tsx": "tsx",
	".py": "python",
	".rs": "rust",
	".go": "go",
	".java": "java",
	".kt": "kotlin",
	".swift": "swift",
	".c": "c",
	".cpp": "cpp",
	".h": "c",
	".hpp": "cpp",
	".cs": "csharp",
	".rb": "ruby",
	".php": "php",
	".sh": "shell",
	".bash": "shell",
	".zsh": "shell",
	".ps1": "powershell",
	".html": "html",
	".css": "css",
	".scss": "scss",
	".sass": "sass",
	".less": "less",
	".json": "json",
	".jsonc": "jsonc",
	".yml": "yaml",
	".yaml": "yaml",
	".toml": "toml",
	".ini": "ini",
	".xml": "xml",
	".md": "markdown",
	".sql": "sql",
	".graphql": "graphql",
};

export interface RepoIndexerOptions {
	cwd: string;
	memoryDir: string;
	llm?: LlmClient;
	maxFileSize?: number;
	summaryMaxSize?: number;
	concurrency?: number;
	maxFiles?: number;
}

export interface IndexOptions {
	summarize?: boolean;
	paths?: string[];
	includeSensitive?: boolean;
}

export interface IndexStats {
	indexed: number;
	unchanged: number;
	ignored: number;
	deleted: number;
	errors: number;
}

export interface IndexResult extends IndexStats {
	total: number;
	byLanguage: Record<string, number>;
	warning?: string;
}

export interface WalkResult {
	files: string[];
	ignored: number;
}

/**
 * Index a local repository: walk files concurrently, extract metadata and symbols,
 * use SHA-256 for change detection, respect `.kagekoignore`, and persist a JSONL index.
 */
export class RepoIndexer {
	readonly cwd: string;
	readonly memoryDir: string;
	readonly llm?: LlmClient;
	readonly maxFileSize: number;
	readonly summaryMaxSize: number;
	readonly concurrency: number;
	readonly maxFiles: number;
	private _lock: Promise<unknown> = Promise.resolve();

	constructor({
		cwd,
		memoryDir,
		llm,
		maxFileSize = 1024 * 1024,
		summaryMaxSize = 16 * 1024,
		concurrency = 4,
		maxFiles = 10000,
	}: RepoIndexerOptions) {
		this.cwd = cwd;
		this.memoryDir = memoryDir;
		this.llm = llm;
		this.maxFileSize = maxFileSize;
		this.summaryMaxSize = summaryMaxSize;
		this.concurrency = concurrency;
		this.maxFiles = maxFiles;
	}

	private _runLocked<T>(fn: () => Promise<T>): Promise<T> {
		const result = this._lock.then(() => fn());
		this._lock = result.catch(() => {});
		return result;
	}

	async index({ summarize = true, paths, includeSensitive = false }: IndexOptions = {}): Promise<IndexResult> {
		return this._runLocked(async () => {
			await fs.mkdir(this.memoryDir, { recursive: true });
			const ignorePatterns = await loadIgnorePatterns(this.cwd);
			const existing = await this._loadExistingUnsafe();
			if (!includeSensitive) {
				for (const indexedPath of existing.keys()) {
					if (isSensitiveContentPath(indexedPath)) existing.delete(indexedPath);
				}
			}

			let filePaths: string[] = [];
			let ignoredWalk = 0;
			let deletedPaths: string[] = [];
			let warning: string | undefined;

			if (paths && paths.length > 0) {
				const resolved = paths
					.map((p) => path.resolve(this.cwd, p))
					.filter((p) => isInsideWorkspace(p, this.cwd) && (includeSensitive || !isSensitiveContentPath(p)));
				for (const p of resolved) {
					if (await statOrNull(p)) {
						filePaths.push(p);
					} else {
						// An explicitly requested path that no longer exists is a
						// deletion: prune its stale index entry. (The git-diff
						// branch below already does this; the paths branch did not.)
						const relPath = path.relative(this.cwd, p).replace(/\\/g, "/");
						if (existing.delete(relPath)) deletedPaths.push(relPath);
					}
				}
			} else {
				const gitRoot = await detectGitRoot(this.cwd);
				if (gitRoot) {
					const gitChanges = await gitChangedFiles(gitRoot, this.cwd);
					deletedPaths = gitChanges.deleted;
					for (const p of deletedPaths) {
						existing.delete(p);
					}
					filePaths = gitChanges.changed
						.map((p) => path.join(this.cwd, p))
						.filter((p) => isInsideWorkspace(p, this.cwd) && (includeSensitive || !isSensitiveContentPath(p)));
				} else {
					const walkResult = await this.walk(this.cwd, ignorePatterns, includeSensitive);
					filePaths = walkResult.files;
					ignoredWalk = walkResult.ignored;
				}
			}

			if (filePaths.length > this.maxFiles) {
				warning = `Repository contains ${filePaths.length} text files; indexing capped at ${this.maxFiles}.`;
				filePaths = filePaths.slice(0, this.maxFiles);
			}

			const stats: IndexStats = {
				indexed: 0,
				unchanged: 0,
				ignored: ignoredWalk,
				deleted: deletedPaths.length,
				errors: 0,
			};

			await mapConcurrent(filePaths, this.concurrency, async (fullPath) => {
				const relPath = path.relative(this.cwd, fullPath).replace(/\\/g, "/");
				if (!includeSensitive && isSensitiveContentPath(relPath)) {
					stats.ignored++;
					return;
				}
				if (isIgnored(relPath, false, ignorePatterns)) {
					stats.ignored++;
					return;
				}
				try {
					const entry = await this.indexFile(fullPath, existing.get(relPath), summarize);
					if (entry) {
						existing.set(entry.path, entry);
						if (entry._unchanged) {
							stats.unchanged++;
						} else {
							stats.indexed++;
						}
						delete entry._unchanged;
					}
				} catch {
					stats.errors++;
				}
			});

			// `unchanged` counts only files examined in THIS run and confirmed
			// unchanged — never derived from the index size, which would count
			// errored files as unchanged.
			const finalEntries = [...existing.values()];
			finalEntries.sort((a, b) => a.path.localeCompare(b.path));
			await this._writeIndexUnsafe(finalEntries);
			const result: IndexResult = {
				...stats,
				// Size of the resulting index. Not `previous + examined`: that
				// double-counted, reporting 2N for an unchanged N-file repo.
				total: finalEntries.length,
				byLanguage: countBy(finalEntries, (e) => e.language ?? "unknown"),
			};
			if (warning) result.warning = warning;
			return result;
		});
	}

	async walk(dir: string, ignorePatterns: string[], includeSensitive = false): Promise<WalkResult> {
		const files: string[] = [];
		let ignored = 0;
		const queue = [dir];
		while (queue.length > 0) {
			const current = queue.shift() as string;
			const entries = await safeReaddir(current);
			for (const entry of entries) {
				if (entry.name === "." || entry.name === "..") continue;
				if (entry.isSymbolicLink()) continue;
				const fullPath = path.join(current, entry.name);
				const relPath = path.relative(this.cwd, fullPath).replace(/\\/g, "/");
				if (!includeSensitive && isSensitiveContentPath(relPath)) {
					ignored++;
					continue;
				}
				if (entry.isDirectory()) {
					if (this.shouldIgnoreDir(entry.name, relPath, ignorePatterns)) {
						ignored++;
						continue;
					}
					queue.push(fullPath);
				} else if (entry.isFile()) {
					if (this.shouldIgnoreFile(entry.name, relPath, (await statOrNull(fullPath))?.size ?? 0, ignorePatterns)) {
						ignored++;
						continue;
					}
					files.push(fullPath);
				}
			}
		}
		return { files, ignored };
	}

	shouldIgnoreDir(name: string, relPath: string, ignorePatterns: string[]): boolean {
		if (ALWAYS_IGNORE_DIRS.has(name)) return true;
		return isIgnored(relPath, true, ignorePatterns);
	}

	shouldIgnoreFile(name: string, relPath: string, size: number, ignorePatterns: string[]): boolean {
		if (size > this.maxFileSize) return true;
		if (ALWAYS_IGNORE_DIRS.has(name)) return true;
		const ext = path.extname(name).toLowerCase();
		if (!TEXT_EXTENSIONS.has(ext)) {
			if (!/^\.?[a-z0-9_-]+$/i.test(name)) return true;
		}
		return isIgnored(relPath, false, ignorePatterns);
	}

	async indexFile(
		fullPath: string,
		existing: RepoIndexEntry | undefined,
		summarize: boolean,
	): Promise<RepoIndexEntry | undefined> {
		const relPath = path.relative(this.cwd, fullPath).replace(/\\/g, "/");
		const stat = await fs.lstat(fullPath).catch(() => null);
		if (!stat) return undefined;
		if (stat.isSymbolicLink()) return undefined;
		if (stat.size > this.maxFileSize) return undefined;

		const ext = path.extname(fullPath).toLowerCase();
		const language = LANGUAGE_BY_EXT[ext] ?? "text";

		let content: string;
		try {
			content = await fs.readFile(fullPath, "utf-8");
		} catch {
			return undefined;
		}
		if (content.includes("\0")) return undefined;

		const hash = hashContent(content);
		if (existing && existing.hash === hash) {
			return { ...existing, _unchanged: true };
		}

		const symbols = extractSymbols(content, language);
		const chunks = buildChunks(content, symbols);
		let summary = existing?.summary;
		let summaryAt = existing?.summaryAt;

		const needsSummary = summarize && (!summary || existing?.hash !== hash);
		if (needsSummary && stat.size <= this.summaryMaxSize && this.llm) {
			const generated = await this.summarize(content, relPath, language);
			if (generated) {
				summary = generated;
				summaryAt = Date.now();
			}
		}
		if (!summary) {
			summary = firstSentence(content) ?? "";
		}

		return {
			path: relPath,
			size: stat.size,
			mtime: stat.mtimeMs,
			hash,
			language,
			symbols,
			chunks,
			summary,
			summaryAt,
		};
	}

	async summarize(content: string, relPath: string, language: string): Promise<string | undefined> {
		const prompt = `Summarize the following ${language} file (${relPath}) in one concise sentence. Focus on its purpose, not implementation details.\n\n${content.slice(0, 4000)}`;
		const abortController = new AbortController();
		try {
			const response = await withTimeout(
				this.llm!.chat({ messages: [{ role: "user", content: prompt }], tools: [], signal: abortController.signal }),
				SUMMARY_TIMEOUT_MS,
				abortController,
			);
			const text = response.content?.trim();
			if (text && text.length > 5 && !text.toLowerCase().includes("don't know")) {
				return text;
			}
		} catch {
			// Fall through to default summary.
		}
		return undefined;
	}

	async loadExisting(): Promise<Map<string, RepoIndexEntry>> {
		return this._runLocked(() => this._loadExistingUnsafe());
	}

	private async _loadExistingUnsafe(): Promise<Map<string, RepoIndexEntry>> {
		const lines = await readJsonlLines<RepoIndexEntry>(this.indexPath);
		const map = new Map<string, RepoIndexEntry>();
		for (const entry of lines) {
			if (entry?.path) map.set(entry.path, entry);
		}
		return map;
	}

	private async _writeIndexUnsafe(entries: RepoIndexEntry[]): Promise<void> {
		const lines = entries.map((e) => JSON.stringify(e)).join("\n") + "\n";
		const tmpPath = `${this.indexPath}.tmp`;
		try {
			await fs.writeFile(tmpPath, lines, "utf-8");
			await fs.rename(tmpPath, this.indexPath);
		} catch (err) {
			await fs.unlink(tmpPath).catch(() => {});
			throw err;
		}
	}

	get indexPath(): string {
		return path.join(this.memoryDir, "repo.index.jsonl");
	}
}

async function loadIgnorePatterns(cwd: string): Promise<string[]> {
	const filePath = path.join(cwd, ".kagekoignore");
	try {
		const text = await fs.readFile(filePath, "utf-8");
		return text
			.split(/\r?\n/)
			.map((line) => line.trim())
			.filter((line) => line && !line.startsWith("#"));
	} catch (err) {
		if ((err as NodeJS.ErrnoException).code === "ENOENT") return [];
		throw err;
	}
}

function isIgnored(relPath: string, isDir: boolean, patterns: string[]): boolean {
	const parts = relPath.split("/");
	for (const pattern of patterns) {
		if (pattern.endsWith("/")) {
			if (!isDir) continue;
			const dirPattern = pattern.slice(0, -1);
			if (matchPattern(relPath, dirPattern, true)) return true;
		} else {
			if (matchPattern(relPath, pattern, isDir)) return true;
		}
	}
	// Always ignore memory/skills/auto directories to avoid self-indexing.
	for (let i = 0; i < parts.length; i++) {
		if (parts[i] === ".kageko") return true;
	}
	return false;
}

function matchPattern(relPath: string, pattern: string, _isDir: boolean): boolean {
	const parts = relPath.split("/");
	const hasSlash = pattern.includes("/");
	if (hasSlash) {
		return globMatch(relPath, pattern);
	}
	// Pattern without slash matches any path component.
	for (const part of parts) {
		if (globMatch(part, pattern)) return true;
	}
	return false;
}

function globMatch(text: string, pattern: string): boolean {
	const regex = compileGlobRegex(`^${globToRegex(pattern)}$`);
	if (!regex) return false;
	return regex.test(text);
}

async function detectGitRoot(cwd: string): Promise<string | undefined> {
	try {
		const { stdout } = await execFileAsync("git", ["rev-parse", "--show-toplevel"], { cwd, timeout: GIT_TIMEOUT_MS });
		return stdout.trim();
	} catch {
		return undefined;
	}
}

async function gitChangedFiles(gitRoot: string, cwd: string): Promise<{ changed: string[]; deleted: string[] }> {
	try {
		const { stdout } = await execFileAsync("git", ["status", "--porcelain"], { cwd: gitRoot, timeout: GIT_TIMEOUT_MS });
		const changed = new Set<string>();
		const deleted = new Set<string>();
		const lines = stdout.split(/\r?\n/).filter((line) => line.length > 3);
		for (const line of lines) {
			const status = line.slice(0, 2).trim();
			const rawPath = line.slice(3).trim();
			// Renames: "R  old/path -> new/path"
			if (rawPath.includes(" -> ")) {
				const [oldPath, newPath] = rawPath.split(" -> ").map((p) => p.trim());
				if (status.includes("D")) {
					deleted.add(relativeFromGitRoot(oldPath as string, gitRoot, cwd));
				}
				changed.add(relativeFromGitRoot(newPath as string, gitRoot, cwd));
			} else if (status.includes("D")) {
				deleted.add(relativeFromGitRoot(rawPath, gitRoot, cwd));
			} else {
				changed.add(relativeFromGitRoot(rawPath, gitRoot, cwd));
			}
		}
		return {
			changed: [...changed],
			deleted: [...deleted],
		};
	} catch {
		return { changed: [], deleted: [] };
	}
}

function relativeFromGitRoot(gitRelPath: string, gitRoot: string, cwd: string): string {
	const absolute = path.resolve(gitRoot, gitRelPath);
	return path.relative(cwd, absolute).replace(/\\/g, "/");
}

function buildChunks(content: string, symbols: RepoSymbol[]): RepoChunk[] {
	const lines = content.split(/\r?\n/);
	const chunks: RepoChunk[] = [];

	if (content.length > 0) {
		chunks.push({ name: "head", content: content.slice(0, 2000) });
	}

	const seen = new Set<number>();
	for (const symbol of symbols.slice(0, 8)) {
		const lineIndex = lines.findIndex((line) => line.includes(symbol.name));
		if (lineIndex === -1 || seen.has(lineIndex)) continue;
		seen.add(lineIndex);
		const start = Math.max(0, lineIndex - 2);
		const end = Math.min(lines.length, lineIndex + 20);
		const chunkContent = lines.slice(start, end).join("\n");
		chunks.push({
			name: `${symbol.type}:${symbol.name}`,
			content: chunkContent.length > 1200 ? chunkContent.slice(0, 1200) + "\n..." : chunkContent,
		});
	}

	return chunks.slice(0, 6);
}

function extractSymbols(content: string, language: string): RepoSymbol[] {
	const symbols: RepoSymbol[] = [];
	if (["javascript", "typescript", "jsx", "tsx"].includes(language)) {
		const re =
			/(?:export\s+(?:async\s+)?function|export\s+(?:default\s+)?class|export\s+const|export\s+let|export\s+var|function|class)\s+([A-Za-z0-9_$]+)/g;
		let m: RegExpExecArray | null;
		while ((m = re.exec(content)) !== null) {
			symbols.push({ type: m[0].startsWith("export") ? "export" : "symbol", name: m[1] as string });
		}
	} else if (language === "python") {
		const re = /^(?:async\s+)?def\s+([A-Za-z0-9_]+)|^class\s+([A-Za-z0-9_]+)/gm;
		let m: RegExpExecArray | null;
		while ((m = re.exec(content)) !== null) {
			symbols.push({ type: m[1] ? "function" : "class", name: (m[1] ?? m[2]) as string });
		}
	}
	return symbols.slice(0, 50);
}

function firstSentence(text: string): string | undefined {
	const line = text.split(/\r?\n/).find((l) => l.trim().length > 0);
	if (!line) return undefined;
	const trimmed = line.trim();
	const end = Math.min(trimmed.length, 240);
	return trimmed.slice(0, end);
}

function hashContent(content: string): string {
	return crypto.createHash("sha256").update(content).digest("hex");
}

function countBy<T>(items: T[], fn: (item: T) => string): Record<string, number> {
	const counts: Record<string, number> = {};
	for (const item of items) {
		const key = fn(item) ?? "unknown";
		counts[key] = (counts[key] ?? 0) + 1;
	}
	return counts;
}

async function safeReaddir(dir: string) {
	try {
		return await fs.readdir(dir, { withFileTypes: true });
	} catch {
		return [];
	}
}

async function statOrNull(filePath: string) {
	try {
		return await fs.stat(filePath);
	} catch {
		return null;
	}
}

function isInsideWorkspace(filePath: string, cwd: string): boolean {
	const rel = path.relative(cwd, filePath);
	return !rel.startsWith("..") && !path.isAbsolute(rel);
}

function withTimeout<T>(promise: Promise<T>, ms: number, abortController?: AbortController): Promise<T> {
	let timer: ReturnType<typeof setTimeout> | undefined;
	const timeout = new Promise<never>((_, reject) => {
		timer = setTimeout(() => {
			abortController?.abort(new Error("repo summary timeout"));
			reject(new Error("repo summary timeout"));
		}, ms);
	});
	const clearTimer = () => clearTimeout(timer);
	promise.then(clearTimer).catch(clearTimer);
	return Promise.race([promise, timeout]);
}
