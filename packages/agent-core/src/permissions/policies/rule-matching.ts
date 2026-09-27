import * as path from "node:path";
import { resolveAccessPaths } from "../../tools/accesses.js";
import { safeRegexTest, safeGlobTest } from "../../utils/regex-safe.js";
import type { ToolExecution } from "../../tools/types.js";
import type { RuleEntry, RuleEntryObject } from "../types.js";

export const RELEVANT_OPERATIONS = ["read", "write", "readwrite", "search"];

export function matchesEntry(
	toolName: string,
	args: unknown,
	execution: ToolExecution | undefined,
	cwd: string | undefined,
	entry: RuleEntry,
): boolean {
	if (entry == null) return false;

	if (typeof entry === "string") {
		return matchesPattern(toolName, entry);
	}
	if (typeof entry === "object") {
		const obj = entry as RuleEntryObject;
		if (!obj.tool && !obj.path && !obj.glob && !obj.regex) return false;
		if (obj.tool && !matchesPattern(toolName, obj.tool)) return false;
		if (!obj.tool && (obj.path || obj.glob || obj.regex)) {
			return false;
		}
		if (obj.path || obj.glob || obj.regex) {
			return resolvedPaths(args, execution, cwd).some((p) => matchesPathConstraint(p, obj, cwd));
		}
		return true;
	}
	return false;
}

function matchesPathConstraint(
	resolvedPath: string,
	entry: RuleEntryObject,
	permissionCwd: string | undefined,
): boolean {
	if (!resolvedPath) return false;
	if (entry.regex) {
		return safeRegexTest(entry.regex, resolvedPath);
	}
	const pattern = entry.glob ?? entry.path;
	if (!pattern) return true;
	if (pattern.includes("*") || pattern.includes("?")) {
		const base = entry.cwd ?? permissionCwd ?? process.cwd();
		const resolvedPattern = path.isAbsolute(pattern) ? path.normalize(pattern) : path.resolve(base, pattern);
		return safeGlobTest(resolvedPattern.replaceAll("\\", "/"), resolvedPath.replaceAll("\\", "/"));
	}
	return path.resolve(entry.cwd ?? permissionCwd ?? process.cwd(), pattern) === resolvedPath;
}

function resolvedPaths(args: unknown, execution: ToolExecution | undefined, cwd: string | undefined): string[] {
	return resolveAccessPaths(execution, RELEVANT_OPERATIONS, cwd) ?? resolvedPathsFromArgs(args, cwd);
}

function resolvedPathsFromArgs(args: unknown, cwd: string | undefined): string[] {
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

function matchesPattern(value: string, pattern: string): boolean {
	if (typeof pattern !== "string") return false;
	if (pattern === value) return true;
	if (pattern.startsWith("/") && pattern.endsWith("/")) {
		return safeRegexTest(pattern.slice(1, -1), value);
	}
	if (pattern.includes("*") || pattern.includes("?")) {
		return safeGlobTest(pattern, value);
	}
	return false;
}
