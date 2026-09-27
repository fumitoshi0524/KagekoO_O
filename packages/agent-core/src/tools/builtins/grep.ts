import * as fs from "node:fs/promises";
import type { Dirent } from "node:fs";
import * as path from "node:path";
import { searchTreeAccess, literalApprovalRule, matchesRuleSubject } from "../accesses.js";
import { compileSafeRegex, compileGlobRegex, globToRegex } from "../../utils/regex-safe.js";
import type { KaosPort } from "../../ports/workspace.js";
import type { Tool, ToolContext } from "../types.js";
import { isSensitiveContentPath } from "../../security/sensitive-path.js";

interface GrepArgs {
	pattern: string;
	path: string;
	glob?: string;
	include_sensitive?: boolean;
}

const MAX_GREP_MATCHES = 1_000;
const MAX_GREP_LINE_CHARS = 2_000;

export const grepTool: Tool<GrepArgs> = {
	name: "grep",
	description: "Search file contents with a regular expression.",
	parameters: {
		type: "object",
		properties: {
			pattern: { type: "string", description: "Regular expression pattern" },
			path: { type: "string", description: "Directory or file to search" },
			glob: { type: "string", description: "Optional glob pattern to filter files (e.g. '*.mjs')" },
			include_sensitive: { type: "boolean", description: "Include sensitive files after explicit approval" },
		},
		required: ["pattern", "path"],
	},
	resolveExecution({ pattern, path: targetPath = "." }: GrepArgs) {
		return {
			accesses: searchTreeAccess(targetPath),
			approvalRule: literalApprovalRule("grep", pattern),
			matchesRule: (ruleArgs) => matchesRuleSubject(ruleArgs, pattern),
			execute: this.execute,
		};
	},
	async execute({ pattern, path: targetPath, glob, include_sensitive = false }: GrepArgs, { kaos }: ToolContext) {
		if (!kaos) return { output: "Workspace filesystem is not available.", isError: true };
		// Use the multiline flag without `g` so `regex.test()` per line does not
		// advance `lastIndex` and skip matches.
		const regex = compileSafeRegex(pattern, "m");
		if (!regex) {
			return {
				output: "Pattern looks prone to catastrophic backtracking or is invalid and has been rejected.",
				isError: true,
			};
		}
		const maxBytes = kaos.maxFileSizeBytes;

		const matches: string[] = [];
		const skipped: string[] = [];
		try {
			const root = await kaos.resolveReal(targetPath);
			const stat = await fs.stat(root).catch(() => null);
			if (stat?.isFile()) {
				if (include_sensitive || !isSensitiveContentPath(root))
					await searchFile(root, regex, matches, skipped, maxBytes);
				else skipped.push(root);
			} else if (stat?.isDirectory()) {
				await searchDir(targetPath, regex, glob, matches, skipped, maxBytes, kaos, include_sensitive);
			} else {
				return { output: `Path not found: ${targetPath}`, isError: true };
			}
		} catch (err) {
			if ((err as Error).name === "PathSecurityError") {
				return { output: (err as Error).message, isError: true };
			}
			throw err;
		}

		const capNote = matches.length >= MAX_GREP_MATCHES ? `\n\nResults capped at ${MAX_GREP_MATCHES} matches.` : "";
		const note =
			(skipped.length > 0 ? `\n\nSkipped ${skipped.length} file(s) over the ${maxBytes} byte size limit.` : "") +
			capNote;
		if (matches.length === 0) {
			return { output: (skipped.length > 0 ? "No matches found in searchable files." : "No matches found.") + note };
		}
		return { output: matches.join("\n") + note };
	},
};

async function searchFile(
	filePath: string,
	regex: RegExp,
	matches: string[],
	skipped: string[],
	maxBytes: number,
): Promise<void> {
	let text: string;
	try {
		const stat = await fs.stat(filePath);
		if (stat.size > maxBytes) {
			skipped.push(filePath);
			return;
		}
		text = await fs.readFile(filePath, "utf-8");
	} catch {
		return;
	}
	const lines = text.split("\n");
	for (let i = 0; i < lines.length; i++) {
		if (matches.length >= MAX_GREP_MATCHES) return;
		if (regex.test(lines[i]!)) {
			const line = lines[i]!;
			const capped = line.length > MAX_GREP_LINE_CHARS ? `${line.slice(0, MAX_GREP_LINE_CHARS)}…` : line;
			matches.push(`${filePath}:${i + 1}: ${capped}`);
		}
	}
}

async function searchDir(
	rootRel: string,
	regex: RegExp,
	glob: string | undefined,
	matches: string[],
	skipped: string[],
	maxBytes: number,
	kaos: KaosPort,
	includeSensitive: boolean,
): Promise<void> {
	const queue = [rootRel];
	while (queue.length > 0) {
		if (matches.length >= MAX_GREP_MATCHES) return;
		const currentRel = queue.shift()!;
		let entries: Dirent[];
		try {
			entries = await kaos.readdir(currentRel);
		} catch {
			continue;
		}
		for (const entry of entries) {
			if (matches.length >= MAX_GREP_MATCHES) return;
			if (entry.name === ".git" || entry.name === "node_modules") continue;
			const childRel = path.join(currentRel, entry.name);
			if (!includeSensitive && isSensitiveContentPath(childRel)) {
				skipped.push(childRel);
				continue;
			}
			if (entry.isSymbolicLink()) {
				// Skip symlinks to prevent traversal outside the workspace.
				continue;
			} else if (entry.isDirectory()) {
				queue.push(childRel);
			} else if (entry.isFile()) {
				if (glob) {
					const relPath = path.relative(rootRel, childRel).replace(/\\/g, "/");
					if (!minimatch(relPath, glob)) continue;
				}
				const fullPath = await kaos.resolveReal(childRel).catch(() => null);
				if (!fullPath) continue;
				await searchFile(fullPath, regex, matches, skipped, maxBytes);
			}
		}
	}
}

function minimatch(filename: string, pattern: string): boolean {
	const regex = compileGlobRegex(`^${globToRegex(pattern)}$`);
	if (!regex) return false;
	return regex.test(filename);
}
