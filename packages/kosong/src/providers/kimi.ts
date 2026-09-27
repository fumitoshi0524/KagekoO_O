/**
 * Kimi (Moonshot AI) provider.
 *
 * The provider id, not the shape of a secret, selects one of two independent
 * products:
 * - `kimi-code`: Kimi For Coding subscription, OAuth, api.kimi.com/coding/v1
 * - `kimi-coding[-cn]`: Moonshot Open Platform, API key, api.moonshot.*
 *
 * An explicit `/coding` override remains available for the official
 * Anthropic-compatible Kimi Code endpoint, but credentials never implicitly
 * cross the product boundary based on an `sk-*` prefix.
 */
import type { OAuthCredentialResolver } from "../credentials.js";
import type { Provider, ProviderChatOptions, ProviderChatResponse } from "../types.js";
import { OpenAICompatibleProvider } from "./openai-compatible.js";
import { resolveAuth } from "./oauth-auth.js";

const KIMI_BASE_URL = "https://api.moonshot.ai/v1";
const KIMI_CN_BASE_URL = "https://api.moonshot.cn/v1";
const KIMI_CODE_BASE_URL = "https://api.kimi.com/coding/v1";
const KIMI_PROVIDER_ID = "kimi";

export interface KimiProviderOptions {
	/** Provider id used for credential resolution; preserves the kimi-code alias. */
	providerId?: string;
	/** Explicit API key; falls back to KIMI_API_KEY or the OAuth credential resolver. */
	apiKey?: string;
	authMode?: "api" | "oauth";
	/** Optional override for the Kimi API base URL. */
	baseUrl?: string;
	/** Injected OAuth credential resolver used when no API key is available. */
	oauthResolver?: OAuthCredentialResolver;
}

export function createKimiProvider(options?: KimiProviderOptions): KimiProvider {
	return new KimiProvider(
		options?.apiKey,
		options?.baseUrl,
		options?.oauthResolver,
		options?.authMode,
		options?.providerId,
	);
}

class KimiProvider implements Provider {
	constructor(
		private apiKey?: string,
		private baseUrl?: string,
		private oauthResolver?: OAuthCredentialResolver,
		private authMode?: "api" | "oauth",
		private providerId = KIMI_PROVIDER_ID,
	) {}

	async chat(options: ProviderChatOptions): Promise<ProviderChatResponse> {
		const auth = await resolveAuth({
			providerId: this.providerId,
			authMode: this.authMode,
			envKeyName: this.providerId === "kimi-coding-cn" ? "KIMI_CN_API_KEY" : "KIMI_API_KEY",
			apiKey: this.apiKey ?? options.apiKey,
			oauthResolver: this.oauthResolver,
		});
		// auth.baseUrl only exists on the OAuth resolver path; it must win over a
		// hand-edited config/env base URL. API-key mode returns no auth.baseUrl
		// and is unaffected.
		const baseUrl =
			auth.baseUrl ??
			options.baseUrl ??
			this.baseUrl ??
			(this.providerId === "kimi-code"
				? KIMI_CODE_BASE_URL
				: this.providerId === "kimi-coding-cn"
					? KIMI_CN_BASE_URL
					: KIMI_BASE_URL);
		if (isKimiCodingAnthropicEndpoint(baseUrl)) {
			// Hermes treats the official Kimi Code `/coding` route as native
			// Anthropic Messages. Only the `/coding/v1` API-compatible route uses
			// OpenAI chat/completions semantics.
			const { createAnthropicProvider } = await import("./anthropic.js");
			return createAnthropicProvider({
				authToken: auth.apiKey,
				baseUrl,
				defaultHeaders: { "User-Agent": "claude-code/0.1.0" },
			}).chat(options);
		}
		return new OpenAICompatibleProvider({ providerId: this.providerId }).chat({
			...options,
			apiKey: auth.apiKey,
			baseUrl,
		});
	}
}

function isKimiCodingAnthropicEndpoint(baseUrl: string): boolean {
	try {
		const url = new URL(baseUrl);
		return url.hostname.toLowerCase() === "api.kimi.com" && url.pathname.replace(/\/$/, "") === "/coding";
	} catch {
		return false;
	}
}
