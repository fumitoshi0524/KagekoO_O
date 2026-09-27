import * as path from "node:path";
import { resolveAccessPaths } from "../../tools/accesses.js";
import { isSensitiveContentPath } from "../../security/sensitive-path.js";
import type { PermissionManagerLike, PermissionPolicy, PolicyContext, PolicyResult } from "../types.js";

const RELEVANT_OPERATIONS = ["read", "write", "readwrite", "search"];

export class SensitiveFileAccessAskPermissionPolicy implements PermissionPolicy {
	name = "SensitiveFileAccessAsk";
	permission: PermissionManagerLike;

	constructor(permission: PermissionManagerLike) {
		this.permission = permission;
	}

	evaluate({ toolName, args, execution }: PolicyContext): PolicyResult | undefined {
		if (hasIncludeSensitive(args)) {
			return {
				kind: "ask",
				reason: "including sensitive files in a recursive operation",
				deniedMessage: `Sensitive access denied for ${toolName}`,
				record: false,
			};
		}

		const paths =
			resolveAccessPaths(execution, RELEVANT_OPERATIONS, this.permission.cwd) ??
			resolvePaths(args, this.permission.cwd);
		if (!paths.some(isSensitiveContentPath)) return undefined;

		if (this.permission.profile === "unrestricted") return undefined;
		return {
			kind: "ask",
			reason: "accessing a sensitive file path",
			deniedMessage: `User denied ${toolName} on sensitive path`,
		};
	}
}

function hasIncludeSensitive(args: unknown): boolean {
	return Boolean(args && typeof args === "object" && (args as Record<string, unknown>)["include_sensitive"] === true);
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
