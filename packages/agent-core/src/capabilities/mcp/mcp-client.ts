import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import type { EnvironmentScrubber } from "../../ports/workspace.js";
import { validateEnv, type McpServerConfig } from "./mcp-manager.js";

const STDERR_HISTORY = 4096;

export interface McpToolInfo {
	name: string;
	description?: string;
	inputSchema?: Record<string, unknown>;
	[key: string]: unknown;
}

export interface McpCallOptions {
	signal?: AbortSignal;
}

/** Stdio MCP client owned by the frozen capabilities boundary. */
export class McpClient {
	readonly name: string;
	readonly config: McpServerConfig;
	client: Client;
	transport: StdioClientTransport | null = null;
	stderrHistory: Buffer[] = [];
	historySize = 0;
	private stderrListener: ((chunk: Buffer | string) => void) | null = null;

	constructor(
		name: string,
		config: McpServerConfig,
		readonly scrubEnvironment: EnvironmentScrubber,
	) {
		this.name = name;
		this.config = config;
		this.client = createClient();
	}

	async connect({ signal }: McpCallOptions = {}): Promise<void> {
		if (!validateEnv(this.config.env)) throw new Error(`MCP server "${this.name}" has unsafe environment variables`);
		if (!this.config.command) throw new Error(`MCP server "${this.name}" has no executable command`);
		this.transport = new StdioClientTransport({
			command: this.config.command,
			args: this.config.args ?? [],
			env: this.scrubEnvironment(
				{ ...process.env, ...(this.config.env ?? {}) },
				{ allowSensitive: this.config.allowSensitiveEnv === true },
			),
			stderr: "pipe",
			cwd: this.config.cwd,
		});
		if (this.transport.stderr) {
			this.stderrListener = (chunk) => this.captureStderr(chunk);
			this.transport.stderr.on("data", this.stderrListener);
		}
		const onAbort = () => {
			void this.close().catch(() => {});
		};
		if (signal?.aborted) {
			onAbort();
			throw signal.reason ?? new Error("MCP connect was aborted");
		}
		signal?.addEventListener("abort", onAbort, { once: true });
		try {
			await this.client.connect(this.transport, { signal });
		} catch (error) {
			await this.close().catch(() => {});
			throw error;
		} finally {
			signal?.removeEventListener("abort", onAbort);
		}
	}

	async listTools({ signal }: McpCallOptions = {}): Promise<McpToolInfo[]> {
		return (await this.client.listTools(undefined, { signal })).tools as McpToolInfo[];
	}
	async callTool(toolName: string, args: Record<string, unknown>, { signal }: McpCallOptions = {}): Promise<unknown> {
		return this.client.callTool({ name: toolName, arguments: args }, undefined, { signal });
	}
	async close(): Promise<void> {
		// The SDK client and its transport both own resources. Attempt both even
		// when one rejects, and keep this instance intact after failure so the
		// manager can retry rather than silently losing a live child process.
		const results = await Promise.allSettled([this.client.close(), this.transport?.close()]);
		const failures = results.filter((result): result is PromiseRejectedResult => result.status === "rejected");
		if (failures.length)
			throw new AggregateError(
				failures.map((failure) => failure.reason),
				`Failed to close MCP client ${this.name}`,
			);
		if (this.stderrListener && this.transport?.stderr)
			this.transport.stderr.removeListener("data", this.stderrListener);
		this.stderrListener = null;
		this.transport = null;
		this.client = createClient();
	}
	getDiagnostics(): string {
		return Buffer.concat(this.stderrHistory).toString("utf-8");
	}
	captureStderr(chunk: Buffer | string): void {
		const buffer = Buffer.isBuffer(chunk) ? chunk : Buffer.from(String(chunk), "utf-8");
		this.stderrHistory.push(buffer);
		this.historySize += buffer.length;
		while (this.historySize > STDERR_HISTORY && this.stderrHistory.length > 0) {
			const removed = this.stderrHistory.shift();
			if (removed) this.historySize -= removed.length;
		}
		if (this.stderrHistory.length === 1 && this.historySize > STDERR_HISTORY) {
			const tail = this.stderrHistory[0]!.slice(-STDERR_HISTORY);
			this.stderrHistory = [tail];
			this.historySize = tail.length;
		}
	}
}

export { McpClient as StdioMcpClient };
function createClient(): Client {
	return new Client({ name: "kageko", version: "0.1.0" });
}
