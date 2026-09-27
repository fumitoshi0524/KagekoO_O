import type { ModelMetadataOrigin, ModelMetadataProvenance, ModelMetadataSource } from "./types.js";

/** Public model registry used by OpenCode and Hermes as a secondary metadata source. */
const MODELS_DEV_URL = "https://models.dev/api.json";
const CACHE_TTL_MS = 15 * 60 * 1000;

export interface CatalogModel {
	readonly id: string;
	readonly name?: string;
	readonly contextLength?: number;
	/** Provider's hard context ceiling, distinct from the currently usable window. */
	readonly contextLimit?: number;
	readonly maxOutputTokens?: number;
	readonly reasoningLevels?: readonly string[];
	readonly capabilities?: string[];
	readonly provenance: ModelMetadataProvenance;
	readonly metadataSource: ModelMetadataOrigin;
}

let cache: { readonly expiresAt: number; readonly value: unknown } | undefined;
let pending: Promise<unknown> | undefined;
let refreshPending: Promise<unknown> | undefined;

/** Clear process-local catalog state. Kept for deterministic discovery tests. */
export function resetPublicCatalogCache(): void {
	cache = undefined;
	pending = undefined;
	refreshPending = undefined;
}

export async function fetchPublicCatalogModels(providerId: string, signal?: AbortSignal): Promise<CatalogModel[]> {
	const provider = providerAlias(providerId);
	let data = await fetchPublicCatalog(signal);
	let models = catalogModels(data, provider);
	// A long-lived process can have a healthy cache that predates a provider
	// being added. Refresh once before treating that provider as unknown.
	if (models.length === 0 && !hasCatalogModels(data, provider)) {
		data = await fetchPublicCatalog(signal, true);
		models = catalogModels(data, provider);
	}
	return models;
}

function catalogModels(data: unknown, provider: string): CatalogModel[] {
	const rawProvider = isRecord(data) ? data[provider] : undefined;
	const rawModels = isRecord(rawProvider) ? rawProvider["models"] : undefined;
	if (!isRecord(rawModels)) return [];

	return Object.entries(rawModels).flatMap(([id, raw]) => {
		if (!isRecord(raw)) return [];
		const contextLength = positiveNumber(readLimit(raw, "context"));
		const maxOutputTokens = positiveNumber(readLimit(raw, "output"));
		const capabilities = capabilitiesFrom(raw);
		const sourceFor = (present: boolean): ModelMetadataSource => (present ? "catalog" : "unknown");
		return [
			{
				id,
				...(typeof raw["name"] === "string" ? { name: raw["name"] } : {}),
				...(contextLength === undefined ? {} : { contextLength }),
				...(maxOutputTokens === undefined ? {} : { maxOutputTokens }),
				...(capabilities === undefined ? {} : { capabilities }),
				provenance: {
					contextLength: sourceFor(contextLength !== undefined),
					capabilities: sourceFor(capabilities !== undefined),
					maxContextSize: "unknown",
					maxOutputTokens: sourceFor(maxOutputTokens !== undefined),
				},
				metadataSource: { kind: "catalog", providerId: provider, source: "public-catalog", authoritative: false },
			} satisfies CatalogModel,
		];
	});
}

function hasCatalogModels(data: unknown, provider: string): boolean {
	const rawProvider = isRecord(data) ? data[provider] : undefined;
	return isRecord(rawProvider) && isRecord(rawProvider["models"]);
}

async function fetchPublicCatalog(signal?: AbortSignal, forceRefresh = false): Promise<unknown> {
	if (!forceRefresh && cache && cache.expiresAt > Date.now()) return cache.value;
	let current = forceRefresh ? refreshPending : pending;
	if (!current) {
		current = fetch(MODELS_DEV_URL)
			.then(async (response) => {
				if (!response.ok) throw new Error(`Public model catalog failed: ${response.status} ${response.statusText}`);
				const value = (await response.json()) as unknown;
				cache = { value, expiresAt: Date.now() + CACHE_TTL_MS };
				return value;
			})
			.finally(() => {
				if (forceRefresh) refreshPending = undefined;
				else pending = undefined;
			});
		if (forceRefresh) refreshPending = current;
		else pending = current;
	}
	return withCallerAbort(current, signal);
}

function withCallerAbort<T>(promise: Promise<T>, signal?: AbortSignal): Promise<T> {
	if (!signal) return promise;
	if (signal.aborted) return Promise.reject(signal.reason ?? new Error("Aborted"));
	return new Promise<T>((resolve, reject) => {
		const onAbort = () => reject(signal.reason ?? new Error("Aborted"));
		signal.addEventListener("abort", onAbort, { once: true });
		promise.then(
			(value) => {
				signal.removeEventListener("abort", onAbort);
				resolve(value);
			},
			(error) => {
				signal.removeEventListener("abort", onAbort);
				reject(error);
			},
		);
	});
}

function providerAlias(providerId: string): string {
	const normalized = providerId.toLowerCase();
	return (
		{
			openai: "openai",
			"openai-api": "openai",
			"openai-codex": "openai",
			anthropic: "anthropic",
			claude: "anthropic",
			kimi: "kimi-for-coding",
			"kimi-code": "kimi-for-coding",
			"kimi-coding": "moonshotai",
			"kimi-coding-cn": "moonshotai",
			moonshot: "moonshotai",
			moonshotai: "moonshotai",
			"moonshotai-cn": "moonshotai",
			"github-copilot": "github-copilot",
			copilot: "github-copilot",
			qwen: "alibaba",
			alibaba: "alibaba",
			"alibaba-coding-plan": "alibaba",
			minimax: "minimax",
			"minimax-cn": "minimax-cn",
			xai: "xai",
			deepseek: "deepseek",
			mistral: "mistral",
			zai: "zai",
			glm: "zhipuai",
			zhipu: "zhipuai",
			stepfun: "stepfun",
			"opencode-zen": "opencode",
			"opencode-go": "opencode-go",
			kilocode: "kilo",
			novita: "novita-ai",
			fireworks: "fireworks-ai",
			"fireworks-ai": "fireworks-ai",
			together: "togetherai",
			togetherai: "togetherai",
			groq: "groq",
			cerebras: "cerebras",
			"ai-gateway": "vercel",
			huggingface: "huggingface",
			arcee: "arcee",
			gmi: "gmi",
			nvidia: "nvidia",
			xiaomi: "xiaomi",
			"ollama-cloud": "ollama-cloud",
			"tencent-tokenhub": "tencent",
			openrouter: "openrouter",
		}[normalized] ?? normalized
	).toLowerCase();
}

function readLimit(model: Record<string, unknown>, key: string): unknown {
	const limit = model["limit"];
	return isRecord(limit) ? limit[key] : undefined;
}

function positiveNumber(value: unknown): number | undefined {
	if (typeof value === "number" && Number.isFinite(value) && value > 0) return Math.round(value);
	return typeof value === "string" && /^\d+(?:\.\d+)?$/.test(value.trim()) && Number(value) > 0
		? Math.round(Number(value))
		: undefined;
}

function capabilitiesFrom(model: Record<string, unknown>): string[] | undefined {
	const result: string[] = [];
	if (model["tool_call"] === true) result.push("tools");
	if (model["reasoning"] === true) result.push("reasoning");
	const modalities = model["modalities"];
	const input = isRecord(modalities) ? modalities["input"] : undefined;
	if (Array.isArray(input) && input.includes("image")) result.push("vision");
	if (model["attachment"] === true && !result.includes("vision")) result.push("vision");
	return result.length ? result : undefined;
}

function isRecord(value: unknown): value is Record<string, unknown> {
	return typeof value === "object" && value !== null && !Array.isArray(value);
}
