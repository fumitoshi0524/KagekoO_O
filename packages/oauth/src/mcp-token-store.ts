import * as path from "node:path";
import { createJsonFileStore, type JsonFileStore } from "./json-file-store.js";
import { kagekoHomeDir } from "./home-dir.js";

export interface McpTokenStoreOptions {
	/** Override the default `~/.kageko/mcp-tokens.json` path. */
	filePath?: string;
}

/**
 * One persisted MCP server OAuth token. Mirrors the shape agent-core's
 * `McpOAuthClient` produces; the record is schemaless beyond these fields so
 * legacy files on disk keep parsing.
 */
export interface McpToken extends Record<string, unknown> {
	accessToken?: string;
	refreshToken?: string;
	expiresAt?: number;
	tokenType?: string;
	raw?: Record<string, unknown>;
}

/**
 * Persistence port for MCP server OAuth tokens, keyed by server name.
 * Reads and writes are whole-map; callers serialize read-modify-write access.
 */
export interface McpTokenStore {
	readAll(): Promise<Record<string, McpToken>>;
	writeAll(tokens: Record<string, McpToken>): Promise<void>;
}

/**
 * Create the file-backed MCP token store at `~/.kageko/mcp-tokens.json`.
 *
 * The oauth package owns this credential path and the on-disk format
 * (tab-indented JSON object with a trailing newline, mode 0600) so agent-core
 * never learns where tokens live.
 */
export function createMcpTokenStore(options?: McpTokenStoreOptions): McpTokenStore {
	const backend: JsonFileStore = createJsonFileStore(
		options?.filePath ?? path.join(kagekoHomeDir(), ".kageko", "mcp-tokens.json"),
	);
	return {
		readAll: () => backend.readAll<McpToken>(),
		writeAll: (tokens) => backend.writeAll(tokens),
	};
}
