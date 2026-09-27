import * as fs from "node:fs/promises";
import * as path from "node:path";
import type { GraphEdge, GraphNode, RepoGraph, RepoIndexEntry } from "./types.js";

const MAX_SOURCE_READ_BYTES = 512 * 1024;

export interface GraphBuilderOptions {
	cwd: string;
	memoryDir: string;
	onDiagnostic?: (message: string, error?: unknown) => void | Promise<void>;
}

interface ExtractedImport {
	path?: string;
	type: string;
	symbol?: string;
}

/**
 * Build a dependency/import graph from repository index entries.
 *
 * Uses regex heuristics (no AST dependencies) for JS/TS, Python, and Rust.
 * Rust resolution is limited to the common cases: `mod x;` sibling files and
 * `use self::/super::/crate::` paths; external crate paths are not resolved.
 */
export class GraphBuilder {
	readonly cwd: string;
	readonly memoryDir: string;
	readonly graphPath: string;
	private _lock: Promise<unknown> = Promise.resolve();
	private readonly onDiagnostic?: (message: string, error?: unknown) => void | Promise<void>;

	constructor({ cwd, memoryDir, onDiagnostic }: GraphBuilderOptions) {
		this.cwd = cwd;
		this.memoryDir = memoryDir;
		this.graphPath = path.join(memoryDir, "repo.graph.json");
		this.onDiagnostic = onDiagnostic;
	}

	private _runLocked<T>(fn: () => Promise<T>): Promise<T> {
		const result = this._lock.then(() => fn());
		this._lock = result.catch(() => {});
		return result;
	}

	async build(entries: RepoIndexEntry[]): Promise<RepoGraph> {
		const { nodes, edges } = await this._extractGraph(entries);
		return this._writeGraph({ nodes, edges, generatedAt: Date.now() });
	}

	/**
	 * Incrementally patch the persisted graph with freshly re-indexed entries.
	 *
	 * Nodes and outgoing edges for the changed paths are replaced; nodes and
	 * edges belonging to unchanged files are kept, so a single edit does not
	 * cost a full-repo rebuild. Paths listed in `removedPaths` (deleted files)
	 * drop out of the graph together with all of their edges.
	 */
	async patch(entries: RepoIndexEntry[], options: { removedPaths?: string[] } = {}): Promise<RepoGraph> {
		const removedIds = new Set(options.removedPaths ?? []);
		if (entries.length === 0 && removedIds.size === 0) return this.load();
		const changedIds = new Set(entries.map((e) => e.path));
		const existing = await this.load();
		const { nodes, edges } = await this._extractGraph(entries);
		// _extractGraph pushes symbol-less stub nodes for import targets; never
		// let a stub displace the existing symbol-rich node for the same file.
		const existingById = new Map(existing.nodes.map((n) => [n.id, n]));
		const freshNodes = nodes.map((n) => {
			if (!changedIds.has(n.id) && n.symbols.length === 0) {
				return existingById.get(n.id) ?? n;
			}
			return n;
		});
		const freshNodeIds = new Set(freshNodes.map((n) => n.id));
		const mergedNodes = [
			...existing.nodes.filter((n) => !changedIds.has(n.id) && !freshNodeIds.has(n.id)),
			...freshNodes,
		].filter((n) => !removedIds.has(n.id));
		// Only edges LEAVING a changed file are stale (its imports may have
		// changed); edges from unchanged files are still valid. All edges
		// touching a removed file go away with it.
		const mergedEdges = [
			...existing.edges.filter((e) => !changedIds.has(e.from) && !removedIds.has(e.from) && !removedIds.has(e.to)),
			...edges,
		];
		return this._writeGraph({ nodes: mergedNodes, edges: mergedEdges, generatedAt: Date.now() });
	}

	private async _extractGraph(entries: RepoIndexEntry[]): Promise<{ nodes: GraphNode[]; edges: GraphEdge[] }> {
		const nodes: GraphNode[] = [];
		const nodeById = new Map<string, GraphNode>();
		const edges: GraphEdge[] = [];

		for (const entry of entries) {
			const id = entry.path;
			const existingNode = nodeById.get(id);
			if (existingNode) {
				// The id may already exist as a symbol-less stub pushed for an
				// import target below; upgrade it with the real entry metadata.
				existingNode.language = entry.language;
				existingNode.symbols = (entry.symbols ?? []).map((s) => s.name);
			} else {
				const node: GraphNode = { id, language: entry.language, symbols: (entry.symbols ?? []).map((s) => s.name) };
				nodes.push(node);
				nodeById.set(id, node);
			}

			let content = entry.content;
			if (!content) {
				const absPath = path.resolve(this.cwd, id);
				if (isInsideWorkspace(absPath, this.cwd)) {
					try {
						const stat = await fs.lstat(absPath);
						if (stat.isFile() && stat.size <= MAX_SOURCE_READ_BYTES) {
							content = await fs.readFile(absPath, "utf-8");
						} else {
							content = (entry.chunks ?? []).map((c) => c.content).join("\n");
						}
					} catch {
						content = (entry.chunks ?? []).map((c) => c.content).join("\n");
					}
				} else {
					content = (entry.chunks ?? []).map((c) => c.content).join("\n");
				}
			}
			const imports = extractImports(content ?? "", entry.language);
			for (const imp of imports) {
				if (!imp.path) continue;
				const resolved = await resolveImportPath(imp.path, entry.path, this.cwd, entry.language, imp.type);
				if (!resolved || !isInsideWorkspace(resolved, this.cwd)) continue;
				const resolvedRel = path.relative(this.cwd, resolved).replace(/\\/g, "/");
				if (!nodeById.has(resolvedRel)) {
					const stub: GraphNode = { id: resolvedRel, language: languageFromPath(resolvedRel), symbols: [] };
					nodes.push(stub);
					nodeById.set(resolvedRel, stub);
				}
				edges.push({
					from: id,
					to: resolvedRel,
					type: imp.type,
					symbol: imp.symbol || undefined,
				});
			}
		}
		return { nodes, edges };
	}

	private async _writeGraph(graph: RepoGraph): Promise<RepoGraph> {
		return this._runLocked(async () => {
			await fs.mkdir(this.memoryDir, { recursive: true });
			const tmpPath = `${this.graphPath}.tmp`;
			try {
				await fs.writeFile(tmpPath, JSON.stringify(graph, null, 2), "utf-8");
				await fs.rename(tmpPath, this.graphPath);
			} catch (err) {
				await fs.unlink(tmpPath).catch(() => {});
				throw err;
			}
			return graph;
		});
	}

	async load(): Promise<RepoGraph> {
		let data: string;
		try {
			data = await fs.readFile(this.graphPath, "utf-8");
		} catch (err) {
			if ((err as NodeJS.ErrnoException).code === "ENOENT") return { nodes: [], edges: [], generatedAt: 0 };
			throw err;
		}
		try {
			const parsed = JSON.parse(data) as RepoGraph;
			if (!parsed || !Array.isArray(parsed.nodes) || !Array.isArray(parsed.edges)) {
				throw new Error("graph JSON has an unexpected shape");
			}
			return parsed;
		} catch (err) {
			// A corrupt graph must not permanently kill incremental updates:
			// fall back to an empty graph so the next patch can rebuild from it.
			this._reportDiagnostic(`Repo graph ${this.graphPath} is corrupt; resetting to an empty graph.`, err);
			return { nodes: [], edges: [], generatedAt: 0 };
		}
	}

	private _reportDiagnostic(message: string, error?: unknown): void {
		try {
			void Promise.resolve(this.onDiagnostic?.(message, error)).catch(() => {});
		} catch {
			/* diagnostics are non-fatal */
		}
	}

	dependents(graph: RepoGraph, targetId: string): string[] {
		return graph.edges.filter((e) => e.to === targetId).map((e) => e.from);
	}

	dependencies(graph: RepoGraph, sourceId: string): string[] {
		return graph.edges.filter((e) => e.from === sourceId).map((e) => e.to);
	}

	related(graph: RepoGraph, id: string, { limit = 10 }: { limit?: number } = {}): { id: string; strength: number }[] {
		const counts: Record<string, number> = {};
		for (const e of graph.edges) {
			if (e.from === id) {
				counts[e.to] = (counts[e.to] ?? 0) + 1;
			} else if (e.to === id) {
				counts[e.from] = (counts[e.from] ?? 0) + 1;
			}
		}
		return Object.entries(counts)
			.sort((a, b) => b[1] - a[1])
			.slice(0, limit)
			.map(([nodeId, strength]) => ({ id: nodeId, strength }));
	}
}

function extractImports(content: string, language: string): ExtractedImport[] {
	const imports: ExtractedImport[] = [];
	if (["javascript", "typescript", "jsx", "tsx"].includes(language)) {
		const esmRe =
			/import\s+(?:(?:\{[^}]*\}|\*\s+as\s+\w+|\w+(?:\s*,\s*(?:\{[^}]*\}|\*\s+as\s+\w+))?)\s+from\s+)?['"]([^'"]+)['"];?/g;
		const cjsRe = /require\s*\(\s*['"]([^'"]+)['"]\s*\)/g;
		const dynamicRe = /import\s*\(\s*['"]([^'"]+)['"]\s*\)/g;
		collectMatches(content, esmRe, "esm", imports);
		collectMatches(content, cjsRe, "require", imports);
		collectMatches(content, dynamicRe, "dynamic", imports);
	} else if (language === "python") {
		const pyRe = /^(?:from\s+([a-zA-Z0-9_.]+)\s+import|import\s+([a-zA-Z0-9_.]+(?:\s*,\s*[a-zA-Z0-9_.]+)*))/gm;
		let m: RegExpExecArray | null;
		while ((m = pyRe.exec(content)) !== null) {
			const mod = m[1] || m[2];
			if (mod) {
				for (const part of mod
					.split(",")
					.map((s) => s.trim())
					.filter(Boolean)) {
					// Keep the raw module path (dots included); resolveImportPath
					// interprets python module semantics.
					imports.push({ path: part, type: "import" });
				}
			}
		}
	} else if (language === "rust") {
		const useRe = /^\s*use\s+([a-zA-Z0-9_:{} ]+);/gm;
		const modRe = /^\s*mod\s+([a-zA-Z0-9_]+)\s*;/gm;
		let m: RegExpExecArray | null;
		while ((m = useRe.exec(content)) !== null) {
			const parts = (m[1] as string).split("::").filter((p) => !p.startsWith("{") && !p.includes("}"));
			if (parts.length > 0) {
				imports.push({ path: parts.join("/"), type: "use" });
			}
		}
		while ((m = modRe.exec(content)) !== null) {
			imports.push({ path: m[1], type: "mod" });
		}
	}
	return imports.slice(0, 100);
}

function collectMatches(content: string, regex: RegExp, type: string, out: ExtractedImport[]): void {
	let m: RegExpExecArray | null;
	while ((m = regex.exec(content)) !== null) {
		out.push({ path: m[1], type });
	}
}

async function resolveImportPath(
	importPath: string,
	importerPath: string,
	cwd: string,
	language: string,
	kind?: string,
): Promise<string | undefined> {
	const importerDir = path.resolve(cwd, path.dirname(importerPath));
	const isJs = ["javascript", "typescript", "jsx", "tsx"].includes(language);
	let bases: string[];
	if (language === "python") {
		bases = pythonModuleBases(importPath, importerDir, cwd);
	} else if (language === "rust") {
		bases = await rustModuleBases(importPath, importerDir, cwd, kind);
	} else {
		if (!importPath.startsWith(".")) {
			// External/package imports and absolute paths are not resolved to local files.
			return undefined;
		}
		bases = [path.resolve(importerDir, importPath)];
	}

	const candidates: string[] = [];
	for (const base of bases) {
		if (!isInsideWorkspace(base, cwd)) continue;
		if (isJs) {
			candidates.push(
				base,
				`${base}.js`,
				`${base}.mjs`,
				`${base}.cjs`,
				`${base}.ts`,
				`${base}.jsx`,
				`${base}.tsx`,
				path.join(base, "index.js"),
				path.join(base, "index.mjs"),
				path.join(base, "index.ts"),
			);
		} else if (language === "python") {
			candidates.push(`${base}.py`, path.join(base, "__init__.py"));
		} else if (language === "rust") {
			candidates.push(`${base}.rs`, path.join(base, "mod.rs"));
		} else {
			candidates.push(base);
		}
	}

	for (const candidate of candidates) {
		try {
			const real = await fs.realpath(candidate);
			const stat = await fs.lstat(real);
			if (stat.isFile() && isInsideWorkspace(real, cwd)) {
				return real;
			}
		} catch {
			// Continue trying.
		}
	}
	return undefined;
}

/**
 * Python imports are module paths, not filesystem paths: `foo.bar` means
 * `foo/bar`, and leading dots are package-relative (`from .x import y`,
 * `from ..pkg import z`). Resolve against the importing file's directory
 * first, then the repo root.
 */
function pythonModuleBases(importPath: string, importerDir: string, cwd: string): string[] {
	const leadingDots = importPath.length - importPath.replace(/^\.+/, "").length;
	const rest = importPath.slice(leadingDots).replace(/\./g, "/");
	if (!rest) return [];
	if (leadingDots > 0) {
		let dir = importerDir;
		for (let i = 1; i < leadingDots; i++) dir = path.dirname(dir);
		return [path.resolve(dir, rest)];
	}
	return [path.resolve(importerDir, rest), path.resolve(cwd, rest)];
}

/**
 * Rust resolution covers the common cases only: `mod x;` resolves to a
 * sibling `x.rs` or `x/mod.rs`; `use self::x` / `use super::x` resolve
 * relative to the importing file; `use crate::x` resolves from the crate
 * source root (the `src/` directory next to the nearest Cargo.toml). External
 * crate paths (`use foo::bar`) are not resolved.
 */
async function rustModuleBases(importPath: string, importerDir: string, cwd: string, kind?: string): Promise<string[]> {
	const segs = importPath.split("/").filter(Boolean);
	if (segs.length === 0) return [];
	let dir: string | undefined;
	if (kind === "mod") {
		dir = importerDir;
	} else if (segs[0] === "crate") {
		dir = await findCrateSourceDir(importerDir, cwd);
		segs.shift();
	} else if (segs[0] === "self") {
		dir = importerDir;
		segs.shift();
	} else if (segs[0] === "super") {
		dir = path.dirname(importerDir);
		segs.shift();
	} else {
		// External crate path — not resolvable to a workspace file.
		return [];
	}
	if (!dir || segs.length === 0) return [];
	const bases = [path.resolve(dir, segs.join("/"))];
	// The last segment of a `use` path is often an item (fn/struct/const)
	// rather than a module, so also try the path minus its last segment.
	if (kind !== "mod" && segs.length > 1) {
		bases.push(path.resolve(dir, segs.slice(0, -1).join("/")));
	}
	return bases;
}

/**
 * Locate the directory `crate::` paths resolve against: the `src/` directory
 * next to the nearest Cargo.toml, walking up from the importer to the
 * workspace root.
 */
async function findCrateSourceDir(startDir: string, cwd: string): Promise<string | undefined> {
	let dir = startDir;
	for (;;) {
		try {
			if ((await fs.lstat(path.join(dir, "Cargo.toml"))).isFile()) {
				const srcDir = path.join(dir, "src");
				try {
					if ((await fs.lstat(srcDir)).isDirectory()) return srcDir;
				} catch {
					// No src/ directory; resolve relative to the manifest dir.
				}
				return dir;
			}
		} catch {
			// No Cargo.toml here; keep walking up.
		}
		if (dir === cwd || !isInsideWorkspace(dir, cwd)) return undefined;
		dir = path.dirname(dir);
	}
}

function isInsideWorkspace(filePath: string, cwd: string): boolean {
	const rel = path.relative(cwd, filePath);
	return !rel.startsWith("..") && !path.isAbsolute(rel);
}

function languageFromPath(filePath: string): string {
	const ext = path.extname(filePath).toLowerCase();
	const map: Record<string, string> = {
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
	};
	return map[ext] ?? "text";
}
