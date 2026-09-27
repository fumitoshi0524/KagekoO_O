/**
 * xAI Grok provider.
 *
 * Wraps the OpenAI-compatible endpoint at https://api.x.ai/v1 and resolves
 * authentication from an explicit API key, the XAI_API_KEY environment
 * variable.
 */
import type { Provider, ProviderChatOptions, ProviderChatResponse } from "../types.js";
import { CodexResponsesProvider } from "./codex-responses.js";
import { resolveAuth } from "./oauth-auth.js";

const XAI_BASE_URL = "https://api.x.ai/v1";
const XAI_PROVIDER_ID = "xai";

export interface XaiProviderOptions {
	/** Explicit API key; falls back to XAI_API_KEY. */
	apiKey?: string;
	/** Optional override for the xAI API base URL. */
	baseUrl?: string;
}

export function createXaiProvider(options?: XaiProviderOptions): XaiProvider {
	return new XaiProvider(options?.apiKey, options?.baseUrl);
}

class XaiProvider implements Provider {
	constructor(
		private apiKey?: string,
		private baseUrl?: string,
	) {}

	async chat(options: ProviderChatOptions): Promise<ProviderChatResponse> {
		const auth = await resolveAuth({
			providerId: XAI_PROVIDER_ID,
			authMode: "api",
			envKeyName: "XAI_API_KEY",
			apiKey: this.apiKey ?? options.apiKey,
		});
		return new CodexResponsesProvider(undefined, {
			providerId: XAI_PROVIDER_ID,
			apiKey: auth.apiKey,
			baseUrl: options.baseUrl ?? this.baseUrl ?? XAI_BASE_URL,
			isXai: true,
		}).chat(options);
	}
}
