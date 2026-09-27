import * as fs from "node:fs";
import * as fsPromises from "node:fs/promises";
import * as path from "node:path";
import type { EnvironmentScrubber } from "../../ports/workspace.js";
import { McpClient, type McpCallOptions, type McpToolInfo } from "./mcp-client.js";

export const DEFAULT_MCP_CONNECT_TIMEOUT_MS = 30_000;
export const DEFAULT_MCP_CALL_TIMEOUT_MS = 30_000;
const MCP_CLOSE_TIMEOUT_MS = 5_000;
const UNSAFE_SHELLS = new Set([
	"sh",
	"bash",
	"zsh",
	"fish",
	"csh",
	"ksh",
	"cmd",
	"cmd.exe",
	"powershell",
	"powershell.exe",
	"pwsh",
	"pwsh.exe",
]);
const SHELL_META_RE = /[;&|<>$`\\"\r\n\t]/;
const WINDOWS_DRIVE_PATH_META_RE = /[;&|<>$`"\r\n\t]/;
const DANGEROUS_EVAL_FLAGS = new Set(["-e", "--eval", "-c", "-p", "--print", "-r", "--require"]);
const DANGEROUS_EVAL_PREFIXES = ["--eval=", "--print=", "--require="];
const DANGEROUS_ENV_KEYS = new Set(["PATH", "LD_PRELOAD", "DYLD_INSERT_LIBRARIES"]);
const MAX_MANIFEST_BYTES = 1024 * 1024;
const VALID_MANIFEST_NAME_RE = /^[a-zA-Z0-9_-]{1,64}$/;
const RESERVED_MANIFEST_NAMES = new Set(["__proto__", "constructor", "prototype"]);

export interface McpServerConfig {
	command?: string;
	args?: string[];
	cwd?: string;
	env?: Record<string, string>;
	allowSensitiveEnv?: boolean;
	oauth?: unknown;
	[key: string]: unknown;
}
export interface AutoMcpManifest {
	name: string;
	description: string;
	command: string;
	args: string[];
	env?: Record<string, string>;
}
export interface AutoMcpDiagnostic {
	readonly path: string;
	readonly message: string;
}
export type McpManagerState = "idle" | "connecting" | "connected" | "closing" | "closed";
export interface McpManagerTimeoutOptions {
	/** Bound on each server connect handshake. */
	connectTimeoutMs?: number;
	/** Bound on each tools/list and tools/call operation. */
	callTimeoutMs?: number;
}
export interface ServerTool {
	server: string;
	tool: McpToolInfo;
}

export function validateEnv(env: unknown): boolean {
	if (env === undefined || env === null) return true;
	if (typeof env !== "object" || Array.isArray(env)) return false;
	for (const key of Object.keys(env)) {
		if (
			DANGEROUS_ENV_KEYS.has(key) ||
			key.startsWith("LD_") ||
			typeof (env as Record<string, unknown>)[key] !== "string"
		)
			return false;
	}
	return true;
}
function commandBasename(command: string): string {
	return path.basename(command.replaceAll("\\", "/"), path.extname(command)).toLowerCase();
}
function resolveCommandBasename(command: string): string {
	try {
		return commandBasename(fs.realpathSync(command));
	} catch {
		return commandBasename(command);
	}
}
export function isSafeMcpCommand(command: unknown): boolean {
	if (typeof command !== "string" || command.length === 0) return false;
	const meta = /^[A-Za-z]:\\/.test(command) ? WINDOWS_DRIVE_PATH_META_RE : SHELL_META_RE;
	return !meta.test(command) && !UNSAFE_SHELLS.has(resolveCommandBasename(command));
}
export function validateMcpServerConfig(config: unknown): boolean {
	if (!config || typeof config !== "object") return false;
	const c = config as { command?: unknown; args?: unknown; env?: unknown; allowSensitiveEnv?: unknown };
	const interpreter = typeof c.command === "string" && isInterpreterCommand(resolveCommandBasename(c.command));
	const evaluates = Array.isArray(c.args) && c.args.some((arg) => typeof arg === "string" && hasDangerousEvalFlag(arg));
	return (
		typeof c.command === "string" &&
		isSafeMcpCommand(c.command) &&
		Array.isArray(c.args) &&
		c.args.every((arg) => typeof arg === "string") &&
		!(interpreter && evaluates) &&
		validateEnv(c.env) &&
		(c.allowSensitiveEnv === undefined || typeof c.allowSensitiveEnv === "boolean")
	);
}

function isInterpreterCommand(command: string): boolean {
	return /^(?:python|node|ruby|perl|php)[\d.]*$/.test(command) || /^nodejs[\d.]*$/.test(command);
}

function hasDangerousEvalFlag(arg: string): boolean {
	if (DANGEROUS_EVAL_FLAGS.has(arg) || DANGEROUS_EVAL_PREFIXES.some((prefix) => arg.startsWith(prefix))) return true;
	return /^-[^-]+$/.test(arg) && [...arg.slice(1)].some((flag) => "ecpr".includes(flag));
}
export function filterMcpServers(servers?: Record<string, unknown> | null): Record<string, McpServerConfig> {
	const out: Record<string, McpServerConfig> = {};
	for (const [name, config] of Object.entries(servers ?? {}))
		if (validateMcpServerConfig(config)) out[name] = config as McpServerConfig;
	return out;
}
export async function loadAutoMcpServers(
	root: string,
	onDiagnostic?: (diagnostic: AutoMcpDiagnostic) => void,
): Promise<Record<string, McpServerConfig>> {
	const servers: Record<string, McpServerConfig> = {};
	let entries: string[];
	try {
		entries = await fsPromises.readdir(root);
	} catch (error) {
		if (isNotFound(error)) return servers;
		throw error;
	}
	for (const entry of entries) {
		const entryPath = path.join(root, entry);
		try {
			const stat = await fsPromises.stat(entryPath);
			const filePath = stat.isDirectory()
				? path.join(entryPath, "manifest.json")
				: entry.endsWith(".json")
					? entryPath
					: undefined;
			if (!filePath) continue;
			if ((await fsPromises.stat(filePath)).size > MAX_MANIFEST_BYTES) {
				reportAutoMcpDiagnostic(onDiagnostic, filePath, `Manifest exceeds the ${MAX_MANIFEST_BYTES}-byte limit`);
				continue;
			}
			const manifest = JSON.parse(await fsPromises.readFile(filePath, "utf-8")) as AutoMcpManifest;
			if (
				VALID_MANIFEST_NAME_RE.test(manifest.name) &&
				!RESERVED_MANIFEST_NAMES.has(manifest.name) &&
				typeof manifest.description === "string" &&
				validateMcpServerConfig({ command: manifest.command, args: manifest.args })
			) {
				servers[manifest.name] = { description: manifest.description, command: manifest.command, args: manifest.args };
			} else {
				reportAutoMcpDiagnostic(onDiagnostic, filePath, "Manifest failed MCP capability validation");
			}
		} catch (error) {
			if (!isNotFound(error)) reportAutoMcpDiagnostic(onDiagnostic, entryPath, (error as Error).message);
		}
	}
	return servers;
}

function isNotFound(error: unknown): boolean {
	return (error as NodeJS.ErrnoException).code === "ENOENT";
}

function reportAutoMcpDiagnostic(
	onDiagnostic: ((diagnostic: AutoMcpDiagnostic) => void) | undefined,
	filePath: string,
	message: string,
): void {
	try {
		onDiagnostic?.({ path: filePath, message });
	} catch {
		// Diagnostics never control capability loading.
	}
}

function withTimeout<T>(factory: (signal: AbortSignal) => Promise<T> | T, ms: number): Promise<T> {
	const controller = new AbortController();
	const timer = setTimeout(() => controller.abort(new Error(`MCP operation timed out after ${ms}ms`)), ms);
	return Promise.resolve(factory(controller.signal)).finally(() => clearTimeout(timer));
}
function combineSignals(signals: Array<AbortSignal | undefined>): { signal: AbortSignal; cleanup(): void } {
	const controller = new AbortController();
	const handlers: Array<{ signal: AbortSignal; handler: () => void }> = [];
	for (const signal of signals) {
		if (!signal) continue;
		if (signal.aborted) {
			controller.abort(signal.reason ?? new Error("MCP operation aborted"));
			break;
		}
		const handler = () => controller.abort(signal.reason ?? new Error("MCP operation aborted"));
		signal.addEventListener("abort", handler, { once: true });
		handlers.push({ signal, handler });
	}
	return {
		signal: controller.signal,
		cleanup: () => handlers.forEach(({ signal, handler }) => signal.removeEventListener("abort", handler)),
	};
}

/** Owns configured MCP processes, connection lifecycle, and tool calls. */
export class McpManager {
	readonly configs: Record<string, McpServerConfig>;
	readonly clients: Map<string, McpClient> = new Map();
	readonly connectTimeoutMs: number;
	readonly callTimeoutMs: number;
	private state: McpManagerState = "idle";
	private closePromise: Promise<void> | undefined;
	constructor(
		servers: Record<string, McpServerConfig> | undefined = {},
		scrubEnvironment: EnvironmentScrubber,
		{ connectTimeoutMs = DEFAULT_MCP_CONNECT_TIMEOUT_MS, callTimeoutMs = DEFAULT_MCP_CALL_TIMEOUT_MS }: McpManagerTimeoutOptions = {},
	) {
		this.configs = { ...servers };
		this.connectTimeoutMs = connectTimeoutMs;
		this.callTimeoutMs = callTimeoutMs;
		for (const [name, config] of Object.entries(servers))
			this.clients.set(name, new McpClient(name, config, scrubEnvironment));
	}
	private transition(from: McpManagerState[], to: McpManagerState): void {
		if (!from.includes(this.state)) throw new Error(`Invalid MCP manager transition from ${this.state} to ${to}`);
		this.state = to;
	}
	async connectAll(): Promise<void> {
		this.transition(["idle"], "connecting");
		const connected: McpClient[] = [];
		try {
			for (const [name, client] of this.clients) {
				try {
					await withTimeout((signal) => client.connect({ signal }), this.connectTimeoutMs);
					connected.push(client);
				} catch (error) {
					await Promise.all(connected.map((item) => item.close().catch(() => {})));
					await client.close().catch(() => {});
					throw new Error(`Failed to connect MCP server ${name}: ${(error as Error).message}`);
				}
			}
			this.transition(["connecting"], "connected");
		} catch (error) {
			if (this.state === "connecting") this.state = "idle";
			throw error;
		}
	}
	async listTools(options: McpCallOptions = {}): Promise<ServerTool[]> {
		this.assertOpen();
		const all: ServerTool[] = [];
		for (const [server, client] of this.clients) {
			const tools = await this.withCombinedSignal(options.signal, (signal) => client.listTools({ signal }));
			all.push(...tools.map((tool) => ({ server, tool })));
		}
		return all;
	}
	async callTool(
		server: string,
		name: string,
		args: Record<string, unknown>,
		options: McpCallOptions = {},
	): Promise<unknown> {
		this.assertOpen();
		const client = this.clients.get(server);
		if (!client) throw new Error(`Unknown MCP server: ${server}`);
		return this.withCombinedSignal(options.signal, (signal) => client.callTool(name, args, { signal }));
	}
	private async withCombinedSignal<T>(
		signal: AbortSignal | undefined,
		operation: (signal: AbortSignal) => Promise<T>,
	): Promise<T> {
		return withTimeout((timeoutSignal) => {
			const combined = combineSignals([signal, timeoutSignal]);
			return operation(combined.signal).finally(combined.cleanup);
		}, this.callTimeoutMs);
	}
	async close(): Promise<void> {
		if (this.state === "closed") return;
		if (this.closePromise) return this.closePromise;
		this.closePromise = (async () => {
			this.transition(["idle", "connecting", "connected"], "closing");
			const results = await Promise.allSettled(
				[...this.clients.values()].map((client) => withTimeout(() => client.close(), MCP_CLOSE_TIMEOUT_MS)),
			);
			const failures = results.filter((result): result is PromiseRejectedResult => result.status === "rejected");
			if (failures.length) {
				// Keep the manager reachable for a later application close/retry. A
				// failed transport cleanup must not be represented as a successful
				// terminal state that silently strands a child process.
				this.state = "connected";
				throw new AggregateError(
					failures.map((failure) => failure.reason),
					"Failed to close MCP clients",
				);
			}
			this.state = "closed";
		})();
		try {
			await this.closePromise;
		} catch (error) {
			this.closePromise = undefined;
			throw error;
		}
	}
	getDiagnostics(): Record<string, string> {
		return Object.fromEntries([...this.clients].map(([name, client]) => [name, client.getDiagnostics()]));
	}
	private assertOpen(): void {
		if (this.state !== "connected") throw new Error(`McpManager is not connected (state: ${this.state})`);
	}
}
