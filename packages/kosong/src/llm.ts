/**
 * Core LLM implementation and factory for the Kageko LLM abstraction layer.
 */
import {
	OPENAI_COMPATIBLE_REGISTRY,
	type ChatOptions,
	type ChatResponse,
	type LLM,
	type LLMConfig,
	type Provider,
	type ProviderRecoveryContext,
} from "./types.js";
import { LLMTimeoutError } from "./errors.js";
import {
	canonicalHermesProviderId,
	providerAuthPolicy,
	resolveHermesApiKey,
	resolveHermesBaseUrl,
} from "./provider-parity.js";
import { configureEnvironmentProxy } from "./live-catalog-fetch.js";

const DEFAULT_LLM_IDLE_TIMEOUT_MS = 300_000;

export class KagekoLLM implements LLM {
	readonly modelName: string;
	readonly model: LLM["model"];

	constructor(
		private provider: Provider,
		private config: LLMConfig,
	) {
		this.modelName = config.modelName;
		this.model = {
			provider: config.provider,
			modelName: config.modelName,
			contextLength: config.contextLength,
			capabilities: config.capabilities,
			reasoningConfig: config.reasoningConfig,
			maxContextSize: config.maxContextSize,
			maxOutputTokens: config.maxOutputTokens,
			authMode: config.authMode,
			...(config.provenance === undefined ? {} : { provenance: config.provenance }),
			...(config.metadataSource === undefined ? {} : { metadataSource: config.metadataSource }),
		};
		const provenance =
			config.provenance ??
			({
				contextLength: config.contextLength === undefined ? "unknown" : "configured",
				capabilities: config.capabilities === undefined ? "unknown" : "configured",
				maxContextSize: config.maxContextSize === undefined ? "unknown" : "configured",
				maxOutputTokens: config.maxOutputTokens === undefined ? "unknown" : "configured",
			} as const);
		for (const [key, value] of Object.entries({
			contextLengthSource: provenance.contextLength,
			capabilitiesSource: provenance.capabilities,
			maxContextSizeSource: provenance.maxContextSize,
			maxOutputTokensSource: provenance.maxOutputTokens,
		})) {
			Object.defineProperty(this.model, key, { value, enumerable: false, writable: false });
		}
	}

	async chat(options: ChatOptions): Promise<ChatResponse> {
		const { signal: externalSignal, ...rest } = options;
		const abortController = new AbortController();
		const idleTimeoutMs = positiveTimeout(this.config.idleTimeoutMs, DEFAULT_LLM_IDLE_TIMEOUT_MS);
		const totalTimeoutMs = positiveTimeout(this.config.totalTimeoutMs);
		let idleTimer: NodeJS.Timeout | undefined;
		let totalTimer: NodeJS.Timeout | undefined;

		if (externalSignal?.aborted) {
			abortController.abort(externalSignal.reason);
		}

		const onExternalAbort = () => abortController.abort(externalSignal?.reason);
		if (externalSignal) {
			externalSignal.addEventListener("abort", onExternalAbort, { once: true });
		}

		const resetIdleTimer = () => {
			if (idleTimeoutMs === undefined) return;
			if (idleTimer) clearTimeout(idleTimer);
			idleTimer = setTimeout(
				() => abortController.abort(new LLMTimeoutError(`LLM stream was idle for ${idleTimeoutMs}ms`)),
				idleTimeoutMs,
			);
		};
		if (rest.onTextDelta || rest.onThinkingDelta || rest.onToolCallDelta) resetIdleTimer();
		if (totalTimeoutMs !== undefined) {
			totalTimer = setTimeout(
				() => abortController.abort(new LLMTimeoutError(`LLM request timed out after ${totalTimeoutMs}ms`)),
				totalTimeoutMs,
			);
		}

		try {
			return await this.provider.chat({
				...rest,
				onTextDelta: rest.onTextDelta
					? (delta) => {
							resetIdleTimer();
							rest.onTextDelta?.(delta);
						}
					: undefined,
				onThinkingDelta: rest.onThinkingDelta
					? (delta) => {
							resetIdleTimer();
							rest.onThinkingDelta?.(delta);
						}
					: undefined,
				onToolCallDelta: rest.onToolCallDelta
					? (delta) => {
							resetIdleTimer();
							rest.onToolCallDelta?.(delta);
						}
					: undefined,
				modelName: this.config.modelName,
				authMode: this.config.authMode,
				temperature: this.config.temperature,
				apiKey: this.config.apiKey,
				baseUrl: this.config.baseUrl,
				maxContextSize: this.config.maxContextSize,
				maxOutputTokens: this.config.maxOutputTokens,
				providerOptions: {
					...this.config.providerOptions,
					...rest.providerOptions,
				},
				signal: abortController.signal,
			});
		} finally {
			if (idleTimer) clearTimeout(idleTimer);
			if (totalTimer) clearTimeout(totalTimer);
			abortController.abort();
			if (externalSignal) {
				externalSignal.removeEventListener("abort", onExternalAbort);
			}
		}
	}

	isRetryableError(error: unknown): boolean {
		return isRetryableError(error);
	}

	async recoverAfterError(error: unknown, context: ProviderRecoveryContext): Promise<boolean> {
		if (context.signal.aborted) throw context.signal.reason ?? new Error("Aborted");
		if (await this.provider.recoverAfterError?.(error, context)) return true;
		const replacement = await createProviderForConfig(this.config);
		if (context.signal.aborted) throw context.signal.reason ?? new Error("Aborted");
		this.provider = replacement;
		return true;
	}
}

export async function createLLM(config: LLMConfig): Promise<KagekoLLM> {
	configureEnvironmentProxy();
	if (!config.provider) {
		throw new Error("LLM config missing `provider`.");
	}
	if (!config.modelName) {
		throw new Error("LLM config missing `modelName`.");
	}

	const normalizedProvider = canonicalProviderId(config.provider);
	const effectiveConfig = {
		...config,
		provider: normalizedProvider,
		...(config.authMode === undefined && providerAuthPolicy(normalizedProvider) === "oauth"
			? { authMode: "oauth" as const }
			: {}),
	};
	const provider = await createProviderForConfig(effectiveConfig);
	return new KagekoLLM(provider, effectiveConfig);
}

async function createProviderForConfig(config: LLMConfig): Promise<Provider> {
	const authMode = config.authMode;
	assertAuthRoute(config.provider, authMode);
	const apiKey = config.apiKey ?? resolveHermesApiKey(config.provider);
	const baseUrl = config.baseUrl ?? resolveHermesBaseUrl(config.provider);
	const commonOptions = {
		apiKey,
		baseUrl,
		modelName: config.modelName,
		authMode,
	};

	switch (config.provider) {
		case "anthropic":
		case "claude": {
			const { createAnthropicProvider } = await import("./providers/anthropic.js");
			return createAnthropicProvider(commonOptions);
		}
		case "mistral": {
			const { createMistralProvider } = await import("./providers/mistral.js");
			return createMistralProvider(commonOptions);
		}
		case "kimi":
		case "kimi-code":
		case "kimi-coding":
		case "kimi-coding-cn": {
			const { createKimiProvider } = await import("./providers/kimi.js");
			return createKimiProvider({
				...commonOptions,
				providerId: config.provider,
				authMode,
				oauthResolver: config.oauthCredentialResolver,
			});
		}
		case "xai": {
			const { createXaiProvider } = await import("./providers/xai.js");
			return createXaiProvider({
				apiKey,
				baseUrl,
			});
		}
		case "minimax": {
			const { createMinimaxProvider } = await import("./providers/minimax.js");
			return createMinimaxProvider({
				apiKey,
				baseUrl,
				providerId: config.provider,
			});
		}
		case "minimax-cn": {
			const { createMinimaxProvider } = await import("./providers/minimax.js");
			return createMinimaxProvider({
				apiKey,
				baseUrl,
				providerId: config.provider,
			});
		}
		case "qwen": {
			const { createQwenProvider } = await import("./providers/qwen.js");
			return createQwenProvider({
				apiKey,
				baseUrl,
			});
		}
		case "openai-codex": {
			const { CodexResponsesProvider } = await import("./providers/codex-responses.js");
			return new CodexResponsesProvider(config.oauthCredentialResolver, {
				providerId: "openai-codex",
				baseUrl,
				preferRouteBaseUrl: Boolean(baseUrl),
			});
		}
		case "openai-api": {
			const { CodexResponsesProvider } = await import("./providers/codex-responses.js");
			return new CodexResponsesProvider(undefined, {
				providerId: "openai-api",
				apiKey,
				baseUrl: baseUrl ?? "https://api.openai.com/v1",
			});
		}
		case "github-copilot": {
			const { CopilotProvider } = await import("./providers/copilot.js");
			return new CopilotProvider(apiKey, baseUrl);
		}
		case "bedrock": {
			const { BedrockProvider } = await import("./providers/bedrock.js");
			return new BedrockProvider({ region: config.providerOptions?.awsRegion });
		}
		case "copilot-acp": {
			const { CopilotAcpProvider } = await import("./providers/copilot-acp.js");
			return new CopilotAcpProvider();
		}
		default: {
			const { createOpenAICompatibleProvider } = await import("./providers/openai-compatible.js");
			const resolvedBaseUrl = baseUrl ?? OPENAI_COMPATIBLE_REGISTRY[config.provider];
			if (!resolvedBaseUrl) {
				throw new Error(`Unknown LLM provider "${config.provider}". Set baseUrl or use a supported provider.`);
			}
			return createOpenAICompatibleProvider(config.provider, {
				apiKey,
				baseUrl: resolvedBaseUrl,
			});
		}
	}
}

function canonicalProviderId(provider: string): string {
	return canonicalHermesProviderId(provider);
}

function assertAuthRoute(provider: string, authMode: LLMConfig["authMode"]): void {
	const normalizedProvider = provider.trim().toLowerCase();
	const policy = providerAuthPolicy(normalizedProvider);
	if (authMode === "oauth" && policy === "api") {
		throw new Error(`Provider "${provider}" does not support OAuth authentication.`);
	}
	if (authMode === "api" && policy === "oauth") {
		throw new Error(`Provider "${provider}" requires OAuth authentication.`);
	}
}

export function isRetryableError(error: unknown): boolean {
	if (hasCancellationCause(error)) return false;
	const seen = new Set<unknown>();
	let current: unknown = error;
	for (let depth = 0; current && depth < 8 && !seen.has(current); depth += 1) {
		seen.add(current);
		if (typeof current === "object") {
			const candidate = current as {
				status?: number;
				code?: string;
				retryable?: boolean;
				cause?: unknown;
				message?: string;
			};
			if (candidate.retryable === true) return true;
			if (candidate.retryable === false) return false;
			if (typeof candidate.status === "number" && [408, 425, 429].includes(candidate.status)) return true;
			if (typeof candidate.status === "number" && candidate.status >= 500) return true;
			if (
				typeof candidate.code === "string" &&
				[
					"ECONNRESET",
					"ETIMEDOUT",
					"ECONNREFUSED",
					"ENOTFOUND",
					"EAI_AGAIN",
					"UND_ERR_CONNECT_TIMEOUT",
					"UND_ERR_BODY_TIMEOUT",
					"UND_ERR_HEADERS_TIMEOUT",
					"UND_ERR_SOCKET",
					"LLM_TIMEOUT",
				].includes(candidate.code)
			)
				return true;
			const message = String(candidate.message ?? "").toLowerCase();
			if (
				message.includes("network error") ||
				message.includes("fetch failed") ||
				message.includes("socket") ||
				message.includes("terminated") ||
				message.includes("other side closed")
			)
				return true;
			current = candidate.cause;
			continue;
		}
		break;
	}
	return false;
}

function hasCancellationCause(error: unknown): boolean {
	const seen = new Set<unknown>();
	let current: unknown = error;
	for (let depth = 0; current && depth < 8 && !seen.has(current); depth += 1) {
		seen.add(current);
		if (current instanceof Error && (current.name === "AbortError" || current.name === "UserCancelled")) return true;
		current = typeof current === "object" ? (current as { cause?: unknown }).cause : undefined;
	}
	return false;
}

function positiveTimeout(value: number | undefined, fallback?: number): number | undefined {
	if (value === undefined) return fallback;
	if (!Number.isFinite(value) || value <= 0) return undefined;
	return Math.min(Math.floor(value), 2 ** 31 - 1);
}
