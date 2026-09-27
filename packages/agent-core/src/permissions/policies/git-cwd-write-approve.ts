import * as path from "node:path";
import { resolveAccessPaths } from "../../tools/accesses.js";
import type { PermissionManagerLike, PermissionPolicy, PolicyContext, PolicyResult } from "../types.js";

const RELEVANT_TOOLS = new Set(["write", "edit"]);
const RELEVANT_OPERATIONS = ["write", "readwrite"];

export class GitCwdWriteApprovePermissionPolicy implements PermissionPolicy {
	name = "GitCwdWriteApprove";
	permission: PermissionManagerLike;

	constructor(permission: PermissionManagerLike) {
		this.permission = permission;
	}

	evaluate({ toolName, args, execution }: PolicyContext): PolicyResult | undefined {
		if (this.permission.profile !== "workspace") return undefined;
		if (!RELEVANT_TOOLS.has(toolName)) return undefined;

		const paths = resolveAccessPaths(execution, RELEVANT_OPERATIONS, this.permission.cwd) ?? extractPaths(args);
		if (paths.length === 0) return undefined;

		const cwd = path.resolve(this.permission.cwd ?? process.cwd());
		const allInside = paths.every((p) => {
			const resolved = path.resolve(cwd, p);
			return resolved === cwd || resolved.startsWith(cwd + path.sep);
		});
		if (allInside) {
			return { kind: "approve", reason: "write is inside the current working directory" };
		}
		return undefined;
	}
}

function extractPaths(args: unknown): string[] {
	if (!args || typeof args !== "object") return [];
	const paths: string[] = [];
	for (const value of Object.values(args as Record<string, unknown>)) {
		if (typeof value === "string") {
			paths.push(value);
		} else if (Array.isArray(value)) {
			for (const item of value) {
				if (typeof item === "string") paths.push(item);
			}
		}
	}
	return paths;
}
