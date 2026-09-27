import * as path from "node:path";
import { resolveAccessPaths } from "../../tools/accesses.js";
import type { PermissionManagerLike, PermissionPolicy, PolicyContext, PolicyResult } from "../types.js";

const MANAGED_KINDS = new Set(["tools", "mcp", "skills"]);
const MUTATION_OPERATIONS = ["write", "readwrite"];

/**
 * Generated capability directories are an application-owned publication
 * surface. Only the learner's pending -> approval path may write them; letting
 * ordinary agent tools imitate an installed artifact bypasses validation,
 * provenance, and user review.
 */
export class ManagedCapabilityPathDenyPolicy implements PermissionPolicy {
	name = "ManagedCapabilityPathDeny";

	constructor(private readonly permission: PermissionManagerLike) {}

	evaluate({ toolName, args, execution }: PolicyContext): PolicyResult | undefined {
		const paths = resolveAccessPaths(execution, MUTATION_OPERATIONS, this.permission.cwd) ?? resolvePaths(args);
		const commandMentionsManagedPath = toolName === "bash" && mentionsManagedPath(commandFrom(args));
		if (!commandMentionsManagedPath && !paths.some(isManagedCapabilityPath)) return undefined;
		return {
			kind: "deny",
			message:
				"Generated capability directories are learner-managed. Use need_capability and the pending learning approval flow; do not create or edit .kageko/{tools,mcp,skills}/auto directly.",
		};
	}
}

export function isManagedCapabilityPath(value: string): boolean {
	const segments = path
		.normalize(value)
		.toLowerCase()
		.split(/[\\/]+/)
		.filter(Boolean);
	for (let index = 0; index <= segments.length - 3; index += 1) {
		if (segments[index] === ".kageko" && MANAGED_KINDS.has(segments[index + 1]!) && segments[index + 2] === "auto")
			return true;
	}
	return false;
}

function resolvePaths(args: unknown): string[] {
	if (!args || typeof args !== "object") return [];
	const candidate = (args as Record<string, unknown>)["path"];
	return typeof candidate === "string" ? [candidate] : [];
}

function commandFrom(args: unknown): string {
	if (!args || typeof args !== "object") return "";
	const command = (args as Record<string, unknown>)["command"];
	return typeof command === "string" ? command : "";
}

function mentionsManagedPath(command: string): boolean {
	const normalized = command.toLowerCase().replaceAll("\\", "/");
	return [...MANAGED_KINDS].some((kind) => normalized.includes(`.kageko/${kind}/auto`));
}
