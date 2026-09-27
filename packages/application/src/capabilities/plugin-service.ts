import type { CapabilityService } from "./capability-service.js";
import { installPlugin as installPluginPackage, PluginManager, type PluginRoot } from "@kageko/agent-core";
import * as path from "node:path";
import { kagekoHomeDir } from "@kageko/oauth";

/** Application owner for plugin snapshots. Each session gets a fresh manager. */
export class PluginService {
	private readonly managers = new Map<string, PluginManager>();

	constructor(readonly capabilities: CapabilityService) {}

	async prepare(roots: readonly PluginRoot[]): Promise<PluginManager> {
		const manager = new PluginManager();
		await manager.loadRoots([...roots]);
		return manager;
	}

	commit(sessionId: string, manager: PluginManager): void {
		this.managers.set(sessionId, manager);
		this.capabilities.replace(
			sessionId,
			"plugin",
			manager.list().map((plugin) => ({ id: plugin.id, description: plugin.description })),
		);
	}

	get(sessionId: string): PluginManager | undefined {
		return this.managers.get(sessionId);
	}

	release(sessionId: string): void {
		this.managers.delete(sessionId);
		this.capabilities.replace(sessionId, "plugin", []);
	}

	/** Install in the workspace-local plugin root; application owns this path. */
	installForSession(source: string, pluginId: string | undefined, cwd: string): Promise<string> {
		const pluginsDir = path.join(cwd, ".kageko", "plugins");
		return installPluginPackage(source, { pluginId, pluginsDir, sourceRoot: cwd });
	}

	/** Install in the user plugin root; the caller chooses which sessions reload. */
	installGlobal(source: string, sourceRoot: string): Promise<string> {
		const pluginsDir = path.join(kagekoHomeDir(), ".kageko", "plugins");
		return installPluginPackage(source, { pluginsDir, sourceRoot });
	}
}
