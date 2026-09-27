import * as path from "node:path";
import { safeGlobTest } from "../utils/regex-safe.js";
import type { ToolAccess, ToolExecution } from "./types.js";

/**
 * Helpers for declaring the resources a tool call will access.
 *
 * Mirrors kimi-code's ToolAccesses shape so permission policies can reason
 * about file reads/writes/search without parsing raw tool arguments.
 */

export function fileAccess(
	operation: "read" | "write" | "readwrite" | "search",
	filePath: string,
	recursive = false,
): ToolAccess[] {
	return [{ kind: "file", operation, path: filePath, recursive }];
}

export function readFileAccess(filePath: string): ToolAccess[] {
	return fileAccess("read", filePath);
}

export function writeFileAccess(filePath: string): ToolAccess[] {
	return fileAccess("write", filePath);
}

export function readWriteFileAccess(filePath: string): ToolAccess[] {
	return fileAccess("readwrite", filePath);
}

export function searchTreeAccess(filePath: string): ToolAccess[] {
	return fileAccess("search", filePath, true);
}

export function allAccess(): ToolAccess[] {
	return [{ kind: "all" }];
}

export function noAccess(): ToolAccess[] {
	return [{ kind: "none" }];
}

export function capabilityAccess(
	kind: "process" | "session" | "durable_state" | "extension" | "delegation" | "credential" | "interaction",
	operation: "read" | "mutate" | "create" | "delete" | "execute" | "use" | "control",
	target: string,
): ToolAccess[] {
	return [{ kind, operation, target }];
}

export function publicNetworkAccess(
	operation: "search" | "fetch",
	target: string,
	options: { sendsContent?: boolean } = {},
): ToolAccess[] {
	return [
		{
			kind: "network",
			operation,
			target,
			method: "GET",
			credentialed: false,
			sendsContent: options.sendsContent ?? operation === "search",
		},
	];
}

export function literalApprovalRule(toolName: string, arg: string): string {
	return `${toolName}(literal:${JSON.stringify(arg)})`;
}

export function matchesRuleSubject(ruleArgs: string, subject: string): boolean {
	if (typeof ruleArgs !== "string" || typeof subject !== "string") return false;
	if (ruleArgs.startsWith("literal:")) {
		try {
			return JSON.parse(ruleArgs.slice("literal:".length)) === subject;
		} catch {
			return false;
		}
	}
	if (ruleArgs === subject) return true;
	// Wildcards are honored only for rules deliberately authored as wildcard
	// rules. literalApprovalRule always uses the encoded branch above.
	if (ruleArgs.includes("*") || ruleArgs.includes("?")) {
		return safeGlobTest(ruleArgs, subject);
	}
	return false;
}

/**
 * Extract absolute file paths from execution.accesses for the given operations.
 * Returns null when execution.accesses is not present, signaling callers to
 * fall back to parsing raw args.
 */
export function resolveAccessPaths(
	execution: ToolExecution | undefined,
	operations: string[] | undefined,
	cwd: string | undefined,
): string[] | null {
	if (!execution || !Array.isArray(execution.accesses)) return null;
	// An all-access wildcard provides no usable path information; fall back to
	// parsing the raw tool arguments so path-based policies can still reason
	// about the real targets.
	if (execution.accesses.some((a) => a?.kind === "all")) return null;

	const root = cwd ?? process.cwd();
	const paths: string[] = [];
	for (const access of execution.accesses) {
		if (access?.kind !== "file") continue;
		if (operations && !operations.includes(access.operation!)) continue;
		if (typeof access.path !== "string") continue;
		paths.push(path.isAbsolute(access.path) ? path.normalize(access.path) : path.resolve(root, access.path));
	}
	return paths;
}

export async function canonicalizeFileAccesses(
	accesses: ToolAccess[] | undefined,
	resolver: { resolveForPolicy(filePath: string): Promise<string> } | undefined,
): Promise<ToolAccess[] | undefined> {
	if (!accesses || !resolver) return accesses;
	return Promise.all(
		accesses.map(async (access) => {
			if (access.kind !== "file" || typeof access.path !== "string") return access;
			return { ...access, path: await resolver.resolveForPolicy(access.path) };
		}),
	);
}
