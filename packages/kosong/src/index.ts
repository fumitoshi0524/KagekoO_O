export { createLLM, KagekoLLM, isRetryableError } from "./llm.js";
export {
	LLMTimeoutError,
	ProviderConnectionError,
	ProviderError,
	ProviderProtocolError,
	ProviderReloginRequiredError,
	parseRetryAfter,
} from "./errors.js";
export { FauxLLM } from "./faux.js";
export type { FauxLLMOptions } from "./faux.js";
// Provider factories are intentionally NOT re-exported here: static value
// re-exports would eagerly load the provider SDKs and defeat the lazy loading
// in ./llm.js. Import them from the provider modules directly instead
// (e.g. ./providers/anthropic.js).
export { OPENAI_COMPATIBLE_REGISTRY } from "./types.js";
export type { OAuthCredentialResolver, OAuthRequestAuth } from "./credentials.js";
export { discoverModels, ModelDiscoveryError } from "./model-discovery.js";
export type { DiscoveredModel } from "./model-discovery.js";
export {
	HERMES_PROVIDER_ALIASES,
	HERMES_PROVIDER_API_KEY_ENV,
	HERMES_PROVIDER_BASE_URL_ENV,
	canonicalHermesProviderId,
	resolveHermesApiKey,
	resolveHermesBaseUrl,
} from "./provider-parity.js";
export type {
	ChatMessage,
	ChatOptions,
	ChatResponse,
	ChatTool,
	ContentPart,
	LLM,
	LLMConfig,
	ModelMetadata,
	ModelMetadataProvenance,
	ModelMetadataOrigin,
	ModelMetadataSource,
	ModelDiscoverySource,
	Provider,
	ProviderChatOptions,
	ProviderChatResponse,
	ProviderRequestOptions,
	ProviderRecoveryContext,
	ToolCall,
} from "./types.js";
export type { AnthropicProviderOptions } from "./providers/anthropic.js";
export type { KimiProviderOptions } from "./providers/kimi.js";
export type { MistralProviderOptions } from "./providers/mistral.js";
export type { MinimaxProviderOptions } from "./providers/minimax.js";
export type { QwenProviderOptions } from "./providers/qwen.js";
export type { XaiProviderOptions } from "./providers/xai.js";
export type { OpenAICompatibleProviderOptions } from "./providers/openai-compatible.js";
export type { BedrockProviderOptions } from "./providers/bedrock.js";
export type { CopilotAcpProviderOptions } from "./providers/copilot-acp.js";

// Backward-compatible aliases for the previous pi-ai-based API.
import { createLLM, KagekoLLM } from "./llm.js";
import type { LLMConfig } from "./types.js";

/**
 * @deprecated Use {@link LLMConfig} instead.
 */
export type PiAiLLMConfig = LLMConfig;

/**
 * @deprecated Use {@link KagekoLLM} instead.
 */
export class PiAiLLM extends KagekoLLM {}

/**
 * @deprecated Use {@link createLLM} instead.
 */
export async function createPiAiLLM(config: PiAiLLMConfig): Promise<PiAiLLM> {
	return createLLM(config) as Promise<PiAiLLM>;
}
