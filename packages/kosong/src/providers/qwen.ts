/**
 * Qwen (Alibaba) provider.
 *
 * Uses DashScope for API-key access.
 */
import type { Provider, ProviderChatOptions, ProviderChatResponse } from "../types.js";
import { OpenAICompatibleProvider } from "./openai-compatible.js";
import { resolveAuth } from "./oauth-auth.js";

const QWEN_API_BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1";
const QWEN_PROVIDER_ID = "qwen";

export interface QwenProviderOptions {
	/** Explicit API key; falls back to QWEN_API_KEY. */
	apiKey?: string;
	/** Optional override for the Qwen API base URL. */
	baseUrl?: string;
}

export function createQwenProvider(options?: QwenProviderOptions): QwenProvider {
	return new QwenProvider(options?.apiKey, options?.baseUrl);
}

class QwenProvider implements Provider {
	constructor(private apiKey?: string, private baseUrl?: string) {}

	async chat(options: ProviderChatOptions): Promise<ProviderChatResponse> {
		const auth = await resolveAuth({
			providerId: QWEN_PROVIDER_ID,
			authMode: "api",
			envKeyName: "QWEN_API_KEY",
			apiKey: this.apiKey ?? options.apiKey,
		});
		return new OpenAICompatibleProvider({ providerId: QWEN_PROVIDER_ID }).chat({
			...options,
			apiKey: auth.apiKey,
			baseUrl: options.baseUrl ?? this.baseUrl ?? QWEN_API_BASE_URL,
		});
	}
}
