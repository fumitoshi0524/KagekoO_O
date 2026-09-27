/**
 * Minimal plugin manager.
 *
 * Loads local plugins from caller-supplied roots (the application layer
 * provides the user-level and project-level plugin directories).
 * Each plugin is a directory containing a `kageko-plugin.json` manifest.
 *
 * Supported capabilities:
 * - skills: absolute paths to skill directories
 * - mcpServers: Record<string, McpServerConfig>
 * - commands: directory of markdown command files
 * - hooks: list of hook definitions (future)
 */
import * as fs from "node:fs/promises";
import * as path from "node:path";
import { filterMcpServers } from "../mcp/mcp-manager.js";
import type { McpServerConfig } from "../mcp/mcp-manager.js";

export interface PluginManifest {
	name: string;
	version?: string;
	description?: string;
	skills?: string[];
	commands?: string;
	mcpServers?: Record<string, unknown>;
	hooks?: unknown[];
	[key: string]: unknown;
}

export interface PluginCommand {
	name: string;
	path: string;
}

export interface Plugin {
	id: string;
	root: string;
	source: string;
	manifest: PluginManifest;
	skills: string[];
	commands: PluginCommand[];
}

export interface PluginDiagnostic {
	plugin: string;
	message: string;
}

export interface PluginRoot {
	path: string;
	source: string;
}

export interface PluginListItem {
	id: string;
	name: string;
	version?: string;
	description?: string;
	source: string;
	root: string;
	skillCount: number;
	commandCount: number;
	mcpServerCount: number;
}

export interface PluginSkillDir {
	pluginId: string;
	path: string;
	source: string;
}

function assertContained(parent: string, target: string, label: string): void {
	const rel = path.relative(parent, target);
	if (path.isAbsolute(rel) || rel.startsWith("..")) {
		throw new Error(`${label} escapes plugin directory: ${target}`);
	}
}

export class PluginManager {
	readonly plugins: Plugin[] = [];
	readonly diagnostics: PluginDiagnostic[] = [];

	/** Reset an owned capability snapshot before a fresh session reload. */
	clear(): void {
		this.plugins.splice(0, this.plugins.length);
		this.diagnostics.splice(0, this.diagnostics.length);
	}

	async loadRoots(roots: PluginRoot[]): Promise<void> {
		for (const { path: root, source } of roots) {
			await this.loadRoot(root, source);
		}
	}

	async loadRoot(root: string, source: string): Promise<void> {
		const entries = await safeReaddir(root);
		for (const entry of entries) {
			const pluginDir = path.join(root, entry);
			const manifestPath = path.join(pluginDir, "kageko-plugin.json");
			if (await fileExists(manifestPath)) {
				await this.loadPlugin(pluginDir, manifestPath, source);
			}
		}
	}

	async loadPlugin(pluginDir: string, manifestPath: string, source: string): Promise<void> {
		let manifest: PluginManifest;
		try {
			const text = await fs.readFile(manifestPath, "utf-8");
			manifest = JSON.parse(text) as PluginManifest;
		} catch (err) {
			this.diagnostics.push({ plugin: pluginDir, message: `Invalid manifest: ${(err as Error).message}` });
			return;
		}

		if (!manifest.name || typeof manifest.name !== "string") {
			this.diagnostics.push({ plugin: pluginDir, message: "Missing plugin name" });
			return;
		}

		const plugin: Plugin = {
			// The directory name is the installer-normalized, filesystem-safe plugin
			// id.  The manifest name is presentation text and may contain spaces;
			// using it as the id made a successfully installed plugin impossible to
			// uninstall through the public API.
			id: path.basename(pluginDir),
			root: pluginDir,
			source,
			manifest,
			skills: [],
			commands: [],
		};

		try {
			if (manifest.skills) {
				for (const skillDir of manifest.skills) {
					const resolved = path.resolve(pluginDir, skillDir);
					assertContained(pluginDir, resolved, "plugin skill directory");
					plugin.skills.push(resolved);
				}
			}

			if (manifest.commands) {
				const commandsDir = path.resolve(pluginDir, manifest.commands);
				assertContained(pluginDir, commandsDir, "plugin commands directory");
				const commandFiles = await collectMarkdownFiles(commandsDir);
				for (const cmdPath of commandFiles) {
					const rel = path.relative(commandsDir, cmdPath);
					const name = rel.replace(/\.md$/, "").replace(/\\/g, "/");
					plugin.commands.push({ name, path: cmdPath });
				}
			}
		} catch (err) {
			this.diagnostics.push({ plugin: pluginDir, message: (err as Error).message });
			return;
		}

		this.plugins.push(plugin);
	}

	get(id: string): Plugin | undefined {
		return this.plugins.find((p) => p.id === id.toLowerCase());
	}

	list(): PluginListItem[] {
		return this.plugins.map((p) => ({
			id: p.id,
			name: p.manifest.name,
			version: p.manifest.version,
			description: p.manifest.description,
			source: p.source,
			root: p.root,
			skillCount: p.skills.length,
			commandCount: p.commands.length,
			mcpServerCount: Object.keys(p.manifest.mcpServers ?? {}).length,
		}));
	}

	*skillDirs(): Generator<PluginSkillDir> {
		for (const plugin of this.plugins) {
			for (const dir of plugin.skills) {
				yield { pluginId: plugin.id, path: dir, source: plugin.source };
			}
		}
	}

	mcpServers(): Record<string, McpServerConfig> {
		const servers: Record<string, McpServerConfig> = {};
		for (const plugin of this.plugins) {
			if (plugin.manifest.mcpServers) {
				for (const [name, config] of Object.entries(filterMcpServers(plugin.manifest.mcpServers))) {
					if (servers[name]) {
						this.diagnostics.push({
							plugin: plugin.id,
							message: `MCP server "${name}" conflicts with an earlier plugin and was ignored.`,
						});
						continue;
					}
					servers[name] = config;
				}
			}
		}
		return servers;
	}

	getCommand(name: string): (PluginCommand & { pluginId: string }) | undefined {
		for (const plugin of this.plugins) {
			const cmd = plugin.commands.find((c) => c.name === name);
			if (cmd) return { ...cmd, pluginId: plugin.id };
		}
		return undefined;
	}

	allCommands(): Array<PluginCommand & { pluginId: string }> {
		return this.plugins.flatMap((p) => p.commands.map((c) => ({ ...c, pluginId: p.id })));
	}
}

export interface PluginLoader {
	load(): Promise<readonly Plugin[]>;
}
export class FilePluginLoader implements PluginLoader {
	constructor(private readonly roots: readonly PluginRoot[]) {}
	async load(): Promise<readonly Plugin[]> {
		const manager = new PluginManager();
		await manager.loadRoots([...this.roots]);
		return manager.plugins;
	}
}

async function safeReaddir(dir: string): Promise<string[]> {
	try {
		return await fs.readdir(dir);
	} catch (error) {
		if ((error as NodeJS.ErrnoException).code === "ENOENT") return [];
		throw error;
	}
}

async function fileExists(filePath: string): Promise<boolean> {
	try {
		await fs.access(filePath);
		return true;
	} catch (error) {
		if ((error as NodeJS.ErrnoException).code === "ENOENT") return false;
		throw error;
	}
}

const MAX_COMMAND_DEPTH = 10;

async function collectMarkdownFiles(dir: string, out: string[] = [], depth = 0): Promise<string[]> {
	if (depth > MAX_COMMAND_DEPTH) {
		return out;
	}
	const entries = await safeReaddir(dir);
	for (const entry of entries) {
		const full = path.join(dir, entry);
		const stat = await fs.lstat(full).catch(() => null);
		if (!stat) continue;
		if (stat.isSymbolicLink()) {
			continue;
		}
		if (stat.isDirectory()) {
			await collectMarkdownFiles(full, out, depth + 1);
		} else if (entry.endsWith(".md")) {
			out.push(full);
		}
	}
	return out;
}
