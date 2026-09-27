import * as fs from "node:fs/promises";
import * as path from "node:path";
import { loadConfig, loadConfigRaw, validateConfig, validateConfigDocument, type Config } from "./config-loader.js";
import { ConfigWriter } from "./config-writer.js";
import { kagekoHomeDir } from "@kageko/oauth";
import { validateMcpServerConfig } from "@kageko/agent-core";

export type ConfigScope = "user" | "project";
export type ConfigPatch = {
	[K in keyof Config]?: NonNullable<Config[K]> extends readonly unknown[]
		? NonNullable<Config[K]>
		: NonNullable<Config[K]> extends object
			? Partial<NonNullable<Config[K]>>
			: Config[K];
};

export interface ApiKeyCredentialSink {
	storeApiKey(providerId: string, apiKey: string): Promise<void>;
}

export interface ProviderCredentialStore extends ApiKeyCredentialSink {
	readApiKey(providerId: string): Promise<string | undefined>;
}

function isObject(value: unknown): value is Record<string, unknown> {
	return value !== null && typeof value === "object" && !Array.isArray(value);
}

function merge(target: Record<string, unknown>, patch: Record<string, unknown>): Record<string, unknown> {
	const output = { ...target };
	for (const [key, value] of Object.entries(patch)) {
		if (value === undefined) continue;
		output[key] = isObject(value) && isObject(output[key]) ? merge(output[key], value) : value;
	}
	return output;
}

async function readObject(filePath: string): Promise<Record<string, unknown>> {
	try {
		const parsed = JSON.parse(await fs.readFile(filePath, "utf8")) as unknown;
		return isObject(parsed) ? parsed : {};
	} catch (error) {
		if ((error as NodeJS.ErrnoException).code === "ENOENT") return {};
		throw error;
	}
}

/**
 * Atomic configuration writer shared by slash panels and programmatic clients.
 * Project values override user values; writes only touch the selected scope.
 */
export class ConfigService {
	private static readonly updateChains = new Map<string, Promise<void>>();
	readonly cwd: string;

	constructor(cwd = process.cwd()) {
		this.cwd = path.resolve(cwd);
	}

	pathFor(scope: ConfigScope): string {
		return scope === "user"
			? path.join(kagekoHomeDir(), ".kageko", "config.json")
			: path.join(this.cwd, ".kageko", "config.json");
	}

	load(): Promise<Config> {
		return loadConfig(this.cwd);
	}

	/** Effective editable configuration, without requiring a runnable model route. */
	inspect(): Promise<Config> {
		return loadConfigRaw(this.cwd);
	}

	async update(patch: ConfigPatch, scope: ConfigScope = "project"): Promise<Config> {
		const filePath = this.pathFor(scope);
		// `apiKey: null` is the sanctioned clear (see removeNullModelFields);
		// anything else would write a secret into a config file.
		const modelPatch = (patch.model ?? {}) as Record<string, unknown>;
		if (Object.hasOwn(modelPatch, "apiKey") && modelPatch["apiKey"] !== null) {
			throw new Error("API keys cannot be written through ConfigService; store credentials in the credential store.");
		}
		validateMcpPatch(patch);
		return this.withPathLock(filePath, async () => {
			const current = await readObject(filePath);
			const nextRaw = merge(current, patch as Record<string, unknown>);
			removeNullModelFields(nextRaw, patch as Record<string, unknown>);
			removeNullSubagentProfiles(nextRaw, patch as Record<string, unknown>);
			validateConfigDocument(nextRaw, filePath, scope);
			const merged = merge(
				(await loadConfigRaw(this.cwd)) as unknown as Record<string, unknown>,
				patch as Record<string, unknown>,
			);
			removeNullModelFields(merged, patch as Record<string, unknown>);
			removeNullSubagentProfiles(merged, patch as Record<string, unknown>);
			validateConfig(merged as unknown as Config);
			await new ConfigWriter(filePath).write(nextRaw);
			return loadConfig(this.cwd);
		});
	}

	private withPathLock<T>(filePath: string, operation: () => Promise<T>): Promise<T> {
		const key = process.platform === "win32" ? path.resolve(filePath).toLowerCase() : path.resolve(filePath);
		const prior = ConfigService.updateChains.get(key) ?? Promise.resolve();
		const result = prior.then(operation, operation);
		const settled = result.then(
			() => undefined,
			() => undefined,
		);
		ConfigService.updateChains.set(key, settled);
		void settled.finally(() => {
			if (ConfigService.updateChains.get(key) === settled) ConfigService.updateChains.delete(key);
		});
		return result;
	}

	/** Move a legacy user-level model.apiKey into device-private credential storage. */
	async migrateLegacyUserApiKey(sink: ApiKeyCredentialSink): Promise<boolean> {
		const filePath = this.pathFor("user");
		const current = await readObject(filePath);
		validateConfigDocument(current, filePath, "user");
		const model = isObject(current["model"]) ? current["model"] : undefined;
		const apiKey = model?.["apiKey"];
		if (apiKey === undefined) return false;
		if (typeof apiKey !== "string" || apiKey.length === 0) {
			throw new Error(`Legacy API key at ${filePath} is invalid.`);
		}
		const effective = await loadConfigRaw(this.cwd);
		const providerId = effective.model.provider;
		if (!providerId) {
			throw new Error(`Cannot migrate ${filePath} model.apiKey without a configured model.provider.`);
		}
		await sink.storeApiKey(providerId, apiKey);
		const nextModel = { ...model };
		delete nextModel["apiKey"];
		const next = { ...current, model: nextModel };
		validateConfigDocument(next, filePath, "user");
		await new ConfigWriter(filePath).write(next);
		return true;
	}
}

/** Reject unsafe MCP definitions at the persistence boundary, before a reload can make them executable. */
function validateMcpPatch(patch: ConfigPatch): void {
	const servers = (patch.mcp as { servers?: unknown } | undefined)?.servers;
	if (servers === undefined) return;
	if (!isObject(servers)) throw new Error("mcp.servers must be an object");
	for (const [name, config] of Object.entries(servers)) {
		if (config === null) continue; // Explicit tombstone used by `mcp remove`.
		if (!validateMcpServerConfig(config))
			throw new Error(`MCP server ${name} has an unsafe or invalid command configuration`);
	}
}

/** A null model field is an explicit metadata reset, unlike undefined (omit). */
function removeNullModelFields(target: Record<string, unknown>, patch: Record<string, unknown>): void {
	const modelPatch = patch["model"];
	if (!isObject(modelPatch) || !isObject(target["model"])) return;
	for (const key of [
		"contextLength",
		"capabilities",
		"maxContextSize",
		"maxOutputTokens",
		"reasoningConfig",
		"baseUrl",
		"authMode",
		"provenance",
		"metadataSource",
		"apiKey",
	]) {
		if (modelPatch[key] === null) delete target["model"][key];
	}
}

/** `agentGraph.subagents.<id>: null` is the explicit profile deletion operation. */
function removeNullSubagentProfiles(target: Record<string, unknown>, patch: Record<string, unknown>): void {
	const graphPatch = patch["agentGraph"];
	if (!isObject(graphPatch) || !isObject(graphPatch["subagents"])) return;
	const graph = target["agentGraph"];
	if (!isObject(graph) || !isObject(graph["subagents"])) return;
	for (const [id, value] of Object.entries(graphPatch["subagents"])) {
		if (value === null) delete graph["subagents"][id];
	}
}
