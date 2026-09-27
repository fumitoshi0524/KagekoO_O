/**
 * MiniMax provider.
 *
 * Wraps MiniMax's Anthropic Messages endpoint at https://api.minimax.io/anthropic
 * (and the regional CN equivalent), while retaining OpenAI-compatible support
 * for an explicitly supplied non-Anthropic base URL. Authentication uses an
 * explicit API key or the regional MiniMax API-key environment variable.
 */
import type { Provider, ProviderChatOptions, ProviderChatResponse } from "../types.js";
import { OpenAICompatibleProvider } from "./openai-compatible.js";
import { resolveAuth } from "./oauth-auth.js";

const MINIMAX_BASE_URL = "https://api.minimax.io/anthropic";
const MINIMAX_CN_BASE_URL = "https://api.minimaxi.com/anthropic";
const MINIMAX_PROVIDER_ID = "minimax";

export interface MinimaxProviderOptions {
	/** Provider id used for credential/environment resolution. */
	providerId?: string;
	/** Explicit API key; falls back to the regional MiniMax API key environment variable. */
	apiKey?: string;
	/** Optional override for the MiniMax API base URL. */
	baseUrl?: string;
}

export function createMinimaxProvider(options?: MinimaxProviderOptions): MinimaxProvider {
	return new MinimaxProvider(
		options?.apiKey,
		options?.baseUrl,
		options?.providerId,
	);
}

class MinimaxProvider implements Provider {
	private inner = new OpenAICompatibleProvider();

	constructor(
		private apiKey?: string,
		private baseUrl?: string,
		private providerId = MINIMAX_PROVIDER_ID,
	) {}

	async chat(options: ProviderChatOptions): Promise<ProviderChatResponse> {
		const auth = await resolveAuth({
			providerId: this.providerId,
			authMode: "api",
			envKeyName: this.providerId === "minimax-cn" ? "MINIMAX_CN_API_KEY" : "MINIMAX_API_KEY",
			apiKey: this.apiKey ?? options.apiKey,
		});
		const defaultBaseUrl = this.providerId === "minimax-cn" ? MINIMAX_CN_BASE_URL : MINIMAX_BASE_URL;
		const baseUrl = options.baseUrl ?? this.baseUrl ?? defaultBaseUrl;
		if (isAnthropicEndpoint(baseUrl)) {
			const { createAnthropicProvider } = await import("./anthropic.js");
			return createAnthropicProvider({ authToken: auth.apiKey, baseUrl }).chat(options);
		}
		return this.inner.chat({
			...options,
			apiKey: auth.apiKey,
			baseUrl,
		});
	}
}

function isAnthropicEndpoint(baseUrl: string): boolean {
	try {
		return new URL(baseUrl).pathname.replace(/\/$/, "").endsWith("/anthropic");
	} catch {
		return baseUrl.replace(/\/$/, "").endsWith("/anthropic");
	}
}
