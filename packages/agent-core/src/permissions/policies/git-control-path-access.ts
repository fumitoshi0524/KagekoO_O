import * as path from "node:path";
import { resolveAccessPaths } from "../../tools/accesses.js";
import type { PermissionManagerLike, PermissionPolicy, PolicyContext, PolicyResult } from "../types.js";

const RELEVANT_TOOLS = new Set(["write", "edit", "bash"]);
const RELEVANT_OPERATIONS = ["write", "readwrite"];

function isGitControlPath(resolvedPath: string): boolean {
	if (!resolvedPath || typeof resolvedPath !== "string") return false;
	const normalized = path.normalize(resolvedPath).toLowerCase();
	return (
		normalized.includes("/.git/") ||
		normalized.includes("\\.git\\") ||
		normalized.endsWith("/.git") ||
		normalized.endsWith("\\.git")
	);
}

export class GitControlPathAccessAskPermissionPolicy implements PermissionPolicy {
	name = "GitControlPathAccessAsk";
	permission: PermissionManagerLike;

	constructor(permission: PermissionManagerLike) {
		this.permission = permission;
	}

	evaluate({ toolName, args, execution }: PolicyContext): PolicyResult | undefined {
		if (!RELEVANT_TOOLS.has(toolName)) return undefined;

		const paths =
			resolveAccessPaths(execution, RELEVANT_OPERATIONS, this.permission.cwd) ??
			resolvePaths(args, this.permission.cwd);
		if (!paths.some(isGitControlPath)) return undefined;

		if (this.permission.profile === "unrestricted") return undefined;
		return {
			kind: "ask",
			reason: "accessing a .git control path",
			deniedMessage: `User denied ${toolName} on .git path`,
		};
	}
}

function resolvePaths(args: unknown, cwd: string | undefined): string[] {
	if (!args || typeof args !== "object") return [];
	const root = cwd ?? process.cwd();
	const paths: string[] = [];
	for (const value of Object.values(args as Record<string, unknown>)) {
		if (typeof value === "string") {
			paths.push(path.isAbsolute(value) ? path.normalize(value) : path.resolve(root, value));
		} else if (Array.isArray(value)) {
			for (const item of value) {
				if (typeof item === "string") {
					paths.push(path.isAbsolute(item) ? path.normalize(item) : path.resolve(root, item));
				}
			}
		}
	}
	return paths;
}
