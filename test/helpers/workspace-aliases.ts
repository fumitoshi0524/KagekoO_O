/**
 * Shared Vitest aliases. Tests resolve workspace packages to TypeScript source
 * rather than a potentially stale dist build.
 */
import path from "node:path";

export interface WorkspaceAliasEntry {
	readonly find: string | RegExp;
	readonly replacement: string;
}

/** @param repoRoot Absolute path of the repository root. */
export function workspaceSrcAliases(repoRoot: string): WorkspaceAliasEntry[] {
	const helpers = path.resolve(repoRoot, "test/helpers");
	const pkg = (name: string): string => path.resolve(repoRoot, "packages", name, "src/index.ts");
	return [
		{ find: /^#test-helpers\/(.+)$/, replacement: `${helpers}/$1` },
		{ find: "@kageko/tui-kit", replacement: pkg("tui-kit") },
		{ find: "@kageko/agent-core", replacement: pkg("agent-core") },
		{ find: "@kageko/kaos", replacement: pkg("kaos") },
		{ find: "@kageko/kosong", replacement: pkg("kosong") },
		{ find: "@kageko/oauth", replacement: pkg("oauth") },
		{ find: "@kageko/process-supervisor", replacement: pkg("process-supervisor") },
		{ find: "@kageko/protocol", replacement: pkg("protocol") },
		{ find: "@kageko/session-store", replacement: pkg("session-store") },
		{ find: "@kageko/application", replacement: pkg("application") },
		{ find: "@kageko/node-sdk", replacement: pkg("node-sdk") },
		{ find: "@kageko/telemetry", replacement: pkg("telemetry") },
	];
}
