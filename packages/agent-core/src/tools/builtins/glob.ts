import * as fs from "node:fs/promises";
import type { Dirent } from "node:fs";
import * as nodePath from "node:path";
import { compileGlobRegex, globToRegex } from "../../utils/regex-safe.js";
import { searchTreeAccess, literalApprovalRule, matchesRuleSubject } from "../accesses.js";
import type { Tool, ToolContext } from "../types.js";
import { shouldHideSensitiveName } from "../../security/sensitive-path.js";

const MAX_GLOB_RESULTS = 10_000;

interface GlobArgs {
	pattern: string;
	path?: string;
	include_sensitive?: boolean;
}

export const globTool: Tool<GlobArgs> = {
	name: "glob",
	description: "Find files matching a glob pattern.",
	parameters: {
		type: "object",
		properties: {
			pattern: { type: "string", description: "Glob pattern (e.g. 'src/**/*.mjs')" },
			path: { type: "string", description: "Base directory; defaults to current directory" },
			include_sensitive: { type: "boolean", description: "Traverse credential directories after explicit approval" },
		},
		required: ["pattern"],
	},
	resolveExecution({ pattern, path = "." }: GlobArgs) {
		return {
			accesses: searchTreeAccess(path),
			approvalRule: literalApprovalRule("glob", pattern),
			matchesRule: (ruleArgs: string) => matchesRuleSubject(ruleArgs, pattern),
			execute: this.execute,
		};
	},
	async execute({ pattern, path = ".", include_sensitive = false }: GlobArgs, { kaos }: ToolContext) {
		if (nodePath.isAbsolute(pattern) || pattern.includes("..")) {
			return { output: "Glob pattern must be relative and not contain parent references", isError: true };
		}
		const matcher = compileGlobRegex(`^${globToRegex(pattern)}$`);
		if (!matcher) {
			return { output: "Glob pattern is unsafe or invalid", isError: true };
		}

		const matches: string[] = [];
		const queue = ["."];
		while (queue.length > 0) {
			const relDir = queue.shift()!;
			let entries: Dirent[];
			try {
				entries = await kaos!.readdir(nodePath.join(path, relDir));
			} catch {
				continue;
			}
			for (const entry of entries) {
				if (entry.name === ".git" || entry.name === "node_modules") continue;
				const childRel = nodePath.join(relDir, entry.name).replace(/\\/g, "/");
				if (!include_sensitive && shouldHideSensitiveName(childRel)) continue;
				if (entry.isSymbolicLink()) continue;
				if (entry.isDirectory()) {
					queue.push(childRel);
				} else if (entry.isFile()) {
					if (matcher.test(childRel)) {
						try {
							await kaos!.resolveReal(nodePath.join(path, childRel));
							matches.push(childRel);
							if (matches.length >= MAX_GLOB_RESULTS) {
								return { output: matches.join("\n") + "\n... (truncated at limit)", truncated: true };
							}
						} catch {
							// Skip files that resolve outside the workspace.
						}
					}
				}
			}
		}
		return { output: matches.join("\n") };
	},
};
