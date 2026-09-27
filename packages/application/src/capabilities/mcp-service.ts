import type { CapabilityService } from "./capability-service.js";
import { McpManager, type McpManagerTimeoutOptions, type McpServerConfig } from "@kageko/agent-core";
import { scrubEnvironment } from "@kageko/kaos";
export class McpService {
	readonly managers = new Map<string, McpManager>();
	/** Managers superseded by a successful reload but not yet fully retired. */
	private readonly retiring = new Map<string, Set<McpManager>>();
	/** Prepared graphs whose construction path failed before publication. */
	private readonly unpublished = new Set<McpManager>();
	constructor(
		readonly capabilities: CapabilityService,
		private readonly onDiagnostic?: (diagnostic: { readonly message: string; readonly error?: unknown }) => void,
	) {}
	/** Build an isolated candidate; composition root decides when to publish it. */
	createCandidate(configs: Record<string, McpServerConfig>, timeouts?: McpManagerTimeoutOptions): McpManager {
		return new McpManager(configs, scrubEnvironment, timeouts);
	}
	get(sessionId: string): McpManager | undefined {
		return this.managers.get(sessionId);
	}
	/** Dispose an unpublished candidate without dropping a failed close owner. */
	async discardCandidate(manager: McpManager): Promise<void> {
		try {
			await manager.close();
			this.unpublished.delete(manager);
		} catch (error) {
			this.unpublished.add(manager);
			throw error;
		}
	}
	async replaceSessionManager(sessionId: string, manager: McpManager): Promise<void> {
		const previous = this.managers.get(sessionId);
		if (previous === manager) return;
		this.managers.set(sessionId, manager);
		this.capabilities.replace(
			sessionId,
			"mcp",
			Object.entries(manager.configs).map(([id, config]) => ({
				id,
				...(typeof config["description"] === "string" ? { description: config["description"] } : {}),
				authSupported: config.oauth !== undefined,
			})),
		);
		// The prepared manager is already connected.  Once it is published it is
		// the authoritative session graph; failure while retiring an old manager
		// must not invalidate that graph or turn an otherwise successful reload
		// into a partial rollback.
		if (previous) {
			this.retire(sessionId, previous);
			await this.closeRetiring(sessionId).catch((error: unknown) => {
				// The failed manager stays in the retiring map, so close/closeAll
				// can retry it; surface the failure instead of swallowing it.
				this.onDiagnostic?.({ message: `Failed to retire MCP capabilities for session ${sessionId}`, error });
			});
		}
	}
	async close(sessionId: string): Promise<void> {
		const manager = this.managers.get(sessionId);
		const results = await Promise.allSettled([manager?.close(), this.closeRetiring(sessionId)]);
		if (results[0]?.status === "fulfilled") {
			this.managers.delete(sessionId);
			// The capability catalog is only cleared once the owning manager is
			// actually gone; a failed close keeps both for the retry.
			this.capabilities.replace(sessionId, "mcp", []);
		}
		const failures = results.filter((result): result is PromiseRejectedResult => result.status === "rejected");
		if (failures.length)
			throw new AggregateError(
				failures.map((failure) => failure.reason),
				`Failed to close MCP capabilities for session ${sessionId}`,
			);
	}
	async closeAll(): Promise<void> {
		const ids = [...new Set([...this.managers.keys(), ...this.retiring.keys()])];
		const candidates = [...this.unpublished];
		const results = await Promise.allSettled([
			...ids.map((id) => this.close(id)),
			...candidates.map((candidate) => this.discardCandidate(candidate)),
		]);
		const failures = results.filter((result): result is PromiseRejectedResult => result.status === "rejected");
		if (failures.length)
			throw new AggregateError(
				failures.map((failure) => failure.reason),
				"Failed to close MCP capabilities",
			);
	}

	private retire(sessionId: string, manager: McpManager): void {
		const managers = this.retiring.get(sessionId) ?? new Set<McpManager>();
		managers.add(manager);
		this.retiring.set(sessionId, managers);
	}

	private async closeRetiring(sessionId: string): Promise<void> {
		const managers = this.retiring.get(sessionId);
		if (!managers?.size) return;
		const entries = [...managers];
		const results = await Promise.allSettled(entries.map((manager) => manager.close()));
		for (const [index, result] of results.entries()) {
			if (result.status === "fulfilled") managers.delete(entries[index]!);
		}
		if (managers.size === 0) this.retiring.delete(sessionId);
		const failures = results.filter((result): result is PromiseRejectedResult => result.status === "rejected");
		if (failures.length)
			throw new AggregateError(
				failures.map((failure) => failure.reason),
				`Failed to retire MCP capabilities for session ${sessionId}`,
			);
	}
}
